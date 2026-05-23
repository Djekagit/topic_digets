from aiogram import Bot, F, Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.fsm.user import GroupEdit, GroupWizard
from bot.keyboards.user import (
    delete_group_kb,
    group_menu_kb,
    group_prompt_kb,
    groups_kb,
    interval_kb,
    main_menu_kb,
    prompt_choice_kb,
    remove_channels_kb,
)
from services.channel_utils import normalize_channel_list, parse_interval_hours
from services.digest import process_due_group
from services.jobs import parse_channels
from services.telegram_parser import channel_exists
from storage.models import async_session, utcnow
from storage.requests.group import (
    add_channels_to_group,
    create_digest_group,
    delete_group,
    get_group_for_user,
    get_user_groups,
    remove_channel_from_group,
    update_group_interval,
    update_group_prompt,
)
from storage.requests.user import get_or_create_user


router = Router()

WELCOME_TEXT = """Привет! Я собираю посты из публичных Telegram-каналов и присылаю тебе короткие дайджесты.

Как это работает:
1. Создай логическую группу, например "AI", "Маркетинг" или "Новости".
2. Добавь публичные каналы.
3. Выбери интервал отправки.
4. Оставь стандартный промпт или задай свой для этой группы.

Если в промпте нет {posts}, я сам добавлю в конец блок "Посты:" со списком постов."""

HELP_TEXT = """Каналы можно добавлять в любом формате:
@channel
https://t.me/channel
t.me/channel

В одной группе может быть несколько каналов. Для каждой группы можно отдельно менять интервал и промпт."""


async def _send_main_menu(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


async def _validate_public_channels(message: Message, channel_names: list[str]) -> bool:
    for channel_name in channel_names:
        try:
            exists = await channel_exists(channel_name)
        except Exception:
            await message.answer(f"Не удалось проверить @{channel_name}. Попробуйте позже.")
            return False
        if not exists:
            await message.answer(f"Канал @{channel_name} не найден или он не публичный.")
            return False
    return True


async def _show_groups(message: Message, tg_id: int) -> None:
    async with async_session() as session:
        groups = await get_user_groups(session, tg_id=tg_id)

    if not groups:
        await message.answer("У тебя пока нет групп.", reply_markup=main_menu_kb())
        return

    await message.answer("Твои группы:", reply_markup=groups_kb(groups))


async def _get_group_or_answer(message: Message, *, group_id: int, tg_id: int):
    async with async_session() as session:
        group = await get_group_for_user(session, group_id=group_id, tg_id=tg_id)
    if not group:
        await message.answer("Группа не найдена.")
    return group


def _group_summary(group) -> str:
    channels = ", ".join(f"@{channel.name}" for channel in group.channels) or "нет каналов"
    prompt_type = "свой" if group.custom_prompt else "стандартный"
    next_digest = group.next_digest_at.strftime("%d.%m %H:%M") if group.next_digest_at else "не задано"
    return (
        f"Группа: {group.name}\n"
        f"Каналы: {channels}\n"
        f"Интервал: каждые {group.interval_hours} ч\n"
        f"Следующий дайджест: {next_digest} UTC\n"
        f"Промпт: {prompt_type}"
    )


async def _finish_group_creation(
    message: Message,
    state: FSMContext,
    telegram_user,
    custom_prompt: str | None,
) -> None:
    data = await state.get_data()
    async with async_session() as session:
        user = await get_or_create_user(session, telegram_user)
        try:
            group = await create_digest_group(
                session,
                user=user,
                name=data["name"],
                channel_names=data["channel_names"],
                interval_hours=data["interval_hours"],
                custom_prompt=custom_prompt,
            )
        except ValueError as exc:
            await message.answer(str(exc), reply_markup=main_menu_kb())
            await state.clear()
            return
        await session.commit()

    await state.clear()
    await message.answer("Группа создана.", reply_markup=group_menu_kb(group))


@router.message(F.text == "Главное меню")
@router.message(Command("start"))
async def command_start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        await get_or_create_user(session, message.from_user)
        await session.commit()
    await _send_main_menu(message)


@router.callback_query(F.data == "main:home")
async def main_home_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "main:help")
async def help_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(HELP_TEXT, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "main:groups")
async def groups_callback(callback: CallbackQuery) -> None:
    await _show_groups(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "main:create_group")
async def create_group_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(GroupWizard.name)
    await callback.message.answer("Введите название группы:")
    await callback.answer()


@router.message(GroupWizard.name)
async def group_name_handler(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name or len(name) > 120:
        await message.answer("Название должно быть от 1 до 120 символов.")
        return

    await state.update_data(name=name)
    await state.set_state(GroupWizard.channels)
    await message.answer("Отправьте список публичных Telegram-каналов:")


@router.message(GroupWizard.channels)
async def group_channels_handler(message: Message, state: FSMContext) -> None:
    try:
        channel_names = normalize_channel_list(message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    if not channel_names:
        await message.answer("Добавьте хотя бы один канал.")
        return
    if not await _validate_public_channels(message, channel_names):
        return

    await state.update_data(channel_names=channel_names)
    await state.set_state(GroupWizard.interval)
    await message.answer("Выберите интервал дайджеста:", reply_markup=interval_kb("create_interval"))


@router.callback_query(GroupWizard.interval, F.data.startswith("create_interval:"))
async def create_interval_callback(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.rsplit(":", 1)[-1]
    if value == "custom":
        await state.set_state(GroupWizard.interval_custom)
        await callback.message.answer("Введите интервал в часах:")
        await callback.answer()
        return

    await state.update_data(interval_hours=int(value))
    await state.set_state(GroupWizard.prompt_choice)
    await callback.message.answer("Какой промпт использовать?", reply_markup=prompt_choice_kb("create_prompt"))
    await callback.answer()


@router.message(GroupWizard.interval_custom)
async def create_interval_custom_handler(message: Message, state: FSMContext) -> None:
    try:
        interval_hours = parse_interval_hours(message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await state.update_data(interval_hours=interval_hours)
    await state.set_state(GroupWizard.prompt_choice)
    await message.answer("Какой промпт использовать?", reply_markup=prompt_choice_kb("create_prompt"))


@router.callback_query(GroupWizard.prompt_choice, F.data == "create_prompt:default")
async def create_default_prompt_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await _finish_group_creation(callback.message, state, callback.from_user, custom_prompt=None)
    await callback.answer()


@router.callback_query(GroupWizard.prompt_choice, F.data == "create_prompt:custom")
async def create_custom_prompt_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(GroupWizard.custom_prompt)
    await callback.message.answer(
        'Введите промпт. Можно использовать {posts}; если не использовать, я добавлю в конец "Посты:" и список постов.'
    )
    await callback.answer()


@router.message(GroupWizard.custom_prompt)
async def create_custom_prompt_handler(message: Message, state: FSMContext) -> None:
    await _finish_group_creation(message, state, message.from_user, custom_prompt=message.text)


@router.callback_query(F.data.startswith("group:open:"))
async def open_group_callback(callback: CallbackQuery) -> None:
    group_id = int(callback.data.rsplit(":", 1)[-1])
    group = await _get_group_or_answer(callback.message, group_id=group_id, tg_id=callback.from_user.id)
    if group:
        await callback.message.answer(_group_summary(group), reply_markup=group_menu_kb(group))
    await callback.answer()


@router.callback_query(F.data.startswith("group:channels:"))
async def group_channels_callback(callback: CallbackQuery) -> None:
    group_id = int(callback.data.rsplit(":", 1)[-1])
    group = await _get_group_or_answer(callback.message, group_id=group_id, tg_id=callback.from_user.id)
    if group:
        channels = "\n".join(f"https://t.me/{channel.name}" for channel in group.channels) or "Каналов пока нет."
        await callback.message.answer(channels, reply_markup=group_menu_kb(group))
    await callback.answer()


@router.callback_query(F.data.startswith("group:add_channels:"))
async def group_add_channels_callback(callback: CallbackQuery, state: FSMContext) -> None:
    group_id = int(callback.data.rsplit(":", 1)[-1])
    await state.set_state(GroupEdit.add_channels)
    await state.update_data(group_id=group_id)
    await callback.message.answer("Отправьте каналы, которые нужно добавить:")
    await callback.answer()


@router.message(GroupEdit.add_channels)
async def group_add_channels_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    try:
        channel_names = normalize_channel_list(message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    if not await _validate_public_channels(message, channel_names):
        return

    async with async_session() as session:
        group = await get_group_for_user(session, group_id=data["group_id"], tg_id=message.from_user.id)
        if not group:
            await message.answer("Группа не найдена.")
            await state.clear()
            return
        added = await add_channels_to_group(session, group=group, channel_names=channel_names)
        await session.commit()

    await state.clear()
    await message.answer(f"Добавлено каналов: {added}.", reply_markup=group_menu_kb(group))


@router.callback_query(F.data.startswith("group:remove_menu:"))
async def group_remove_menu_callback(callback: CallbackQuery) -> None:
    group_id = int(callback.data.rsplit(":", 1)[-1])
    group = await _get_group_or_answer(callback.message, group_id=group_id, tg_id=callback.from_user.id)
    if group:
        await callback.message.answer("Выберите канал для удаления:", reply_markup=remove_channels_kb(group.id, group.channels))
    await callback.answer()


@router.callback_query(F.data.startswith("group:remove_channel:"))
async def group_remove_channel_callback(callback: CallbackQuery) -> None:
    _, _, group_id_raw, channel_id_raw = callback.data.split(":")
    async with async_session() as session:
        group = await get_group_for_user(session, group_id=int(group_id_raw), tg_id=callback.from_user.id)
        if not group:
            await callback.message.answer("Группа не найдена.")
            await callback.answer()
            return
        removed = await remove_channel_from_group(session, group=group, channel_id=int(channel_id_raw))
        await session.commit()

    await callback.message.answer("Канал удален." if removed else "Канал не найден.", reply_markup=group_menu_kb(group))
    await callback.answer()


@router.callback_query(F.data.startswith("group:interval:"))
async def group_interval_callback(callback: CallbackQuery) -> None:
    group_id = int(callback.data.rsplit(":", 1)[-1])
    await callback.message.answer("Выберите новый интервал:", reply_markup=interval_kb(f"edit_interval:{group_id}"))
    await callback.answer()


@router.callback_query(F.data.startswith("edit_interval:"))
async def edit_interval_callback(callback: CallbackQuery, state: FSMContext) -> None:
    _, group_id_raw, value = callback.data.split(":")
    group_id = int(group_id_raw)
    if value == "custom":
        await state.set_state(GroupEdit.interval_custom)
        await state.update_data(group_id=group_id)
        await callback.message.answer("Введите интервал в часах:")
        await callback.answer()
        return

    async with async_session() as session:
        group = await get_group_for_user(session, group_id=group_id, tg_id=callback.from_user.id)
        if not group:
            await callback.message.answer("Группа не найдена.")
            await callback.answer()
            return
        update_group_interval(group, interval_hours=int(value), now=utcnow())
        await session.commit()

    await callback.message.answer(f"Интервал обновлен: каждые {value} ч.", reply_markup=group_menu_kb(group))
    await callback.answer()


@router.message(GroupEdit.interval_custom)
async def edit_interval_custom_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    try:
        interval_hours = parse_interval_hours(message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    async with async_session() as session:
        group = await get_group_for_user(session, group_id=data["group_id"], tg_id=message.from_user.id)
        if not group:
            await message.answer("Группа не найдена.")
            await state.clear()
            return
        update_group_interval(group, interval_hours=interval_hours, now=utcnow())
        await session.commit()

    await state.clear()
    await message.answer(f"Интервал обновлен: каждые {interval_hours} ч.", reply_markup=group_menu_kb(group))


@router.callback_query(F.data.startswith("group:prompt:"))
async def group_prompt_callback(callback: CallbackQuery) -> None:
    group_id = int(callback.data.rsplit(":", 1)[-1])
    group = await _get_group_or_answer(callback.message, group_id=group_id, tg_id=callback.from_user.id)
    if group:
        current = "свой" if group.custom_prompt else "стандартный"
        await callback.message.answer(f"Текущий промпт: {current}.", reply_markup=group_prompt_kb(group.id))
    await callback.answer()


@router.callback_query(F.data.startswith("group:prompt_custom:"))
async def group_prompt_custom_callback(callback: CallbackQuery, state: FSMContext) -> None:
    group_id = int(callback.data.rsplit(":", 1)[-1])
    await state.set_state(GroupEdit.custom_prompt)
    await state.update_data(group_id=group_id)
    await callback.message.answer(
        'Введите новый промпт для группы. Можно использовать {posts}; если не использовать, я добавлю в конец "Посты:" и список постов.'
    )
    await callback.answer()


@router.message(GroupEdit.custom_prompt)
async def group_prompt_custom_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    async with async_session() as session:
        group = await get_group_for_user(session, group_id=data["group_id"], tg_id=message.from_user.id)
        if not group:
            await message.answer("Группа не найдена.")
            await state.clear()
            return
        update_group_prompt(group, message.text)
        await session.commit()

    await state.clear()
    await message.answer("Промпт обновлен.", reply_markup=group_menu_kb(group))


@router.callback_query(F.data.startswith("group:digest_now:"))
async def group_digest_now_callback(callback: CallbackQuery, bot: Bot) -> None:
    group_id = int(callback.data.rsplit(":", 1)[-1])
    await callback.answer("Формирую дайджест...")

    async with async_session() as session:
        group = await get_group_for_user(session, group_id=group_id, tg_id=callback.from_user.id)
        if not group:
            await callback.message.answer("Группа не найдена.")
            return
        if not group.channels:
            await callback.message.answer("В группе пока нет каналов.", reply_markup=group_menu_kb(group))
            return

        await callback.message.answer("Собираю свежие посты и формирую дайджест...")
        await parse_channels(session, group.channels)
        result = await process_due_group(session, bot=bot, group=group, now=utcnow())
        await session.commit()

    if result.sent:
        await callback.message.answer("Дайджест сформирован и отправлен.", reply_markup=group_menu_kb(group))
    elif result.posts_count == 0:
        await callback.message.answer("Свежих постов для дайджеста пока нет.", reply_markup=group_menu_kb(group))
    else:
        await callback.message.answer("Посты нашлись, но AI вернул пустой ответ.", reply_markup=group_menu_kb(group))


@router.callback_query(F.data.startswith("group:prompt_reset:"))
async def group_prompt_reset_callback(callback: CallbackQuery) -> None:
    group_id = int(callback.data.rsplit(":", 1)[-1])
    async with async_session() as session:
        group = await get_group_for_user(session, group_id=group_id, tg_id=callback.from_user.id)
        if not group:
            await callback.message.answer("Группа не найдена.")
            await callback.answer()
            return
        update_group_prompt(group, None)
        await session.commit()

    await callback.message.answer("Промпт сброшен на стандартный.", reply_markup=group_menu_kb(group))
    await callback.answer()


@router.callback_query(F.data.startswith("group:delete_confirm:"))
async def group_delete_confirm_callback(callback: CallbackQuery) -> None:
    group_id = int(callback.data.rsplit(":", 1)[-1])
    await callback.message.answer("Удалить группу и ее настройки?", reply_markup=delete_group_kb(group_id))
    await callback.answer()


@router.callback_query(F.data.startswith("group:delete:"))
async def group_delete_callback(callback: CallbackQuery) -> None:
    group_id = int(callback.data.rsplit(":", 1)[-1])
    async with async_session() as session:
        group = await get_group_for_user(session, group_id=group_id, tg_id=callback.from_user.id)
        if not group:
            await callback.message.answer("Группа не найдена.")
            await callback.answer()
            return
        await delete_group(session, group=group)
        await session.commit()

    await callback.message.answer("Группа удалена.", reply_markup=main_menu_kb())
    await callback.answer()
