from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from storage.models import Channel, DigestGroup


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Создать группу", callback_data="main:create_group")
    builder.button(text="Мои группы", callback_data="main:groups")
    builder.button(text="Помощь", callback_data="main:help")
    builder.adjust(1)
    return builder.as_markup()


def groups_kb(groups: list[DigestGroup]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for group in groups:
        builder.button(text=group.name, callback_data=f"group:open:{group.id}")
    builder.button(text="Создать группу", callback_data="main:create_group")
    builder.button(text="Главное меню", callback_data="main:home")
    builder.adjust(1)
    return builder.as_markup()


def group_menu_kb(group: DigestGroup) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Каналы", callback_data=f"group:channels:{group.id}"),
                InlineKeyboardButton(text="Добавить", callback_data=f"group:add_channels:{group.id}"),
            ],
            [
                InlineKeyboardButton(text="Удалить канал", callback_data=f"group:remove_menu:{group.id}"),
                InlineKeyboardButton(text="Интервал", callback_data=f"group:interval:{group.id}"),
            ],
            [
                InlineKeyboardButton(text="Промпт", callback_data=f"group:prompt:{group.id}"),
                InlineKeyboardButton(text="Удалить группу", callback_data=f"group:delete_confirm:{group.id}"),
            ],
            [InlineKeyboardButton(text="Сформировать дайджест сейчас", callback_data=f"group:digest_now:{group.id}")],
            [InlineKeyboardButton(text="Мои группы", callback_data="main:groups")],
        ]
    )


def interval_kb(prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for hours in (1, 3, 6, 12, 24):
        builder.button(text=f"{hours} ч", callback_data=f"{prefix}:{hours}")
    builder.button(text="Свое значение", callback_data=f"{prefix}:custom")
    builder.adjust(3, 2, 1)
    return builder.as_markup()


def prompt_choice_kb(prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Стандартный", callback_data=f"{prefix}:default")
    builder.button(text="Свой промпт", callback_data=f"{prefix}:custom")
    builder.adjust(1)
    return builder.as_markup()


def group_prompt_kb(group_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Задать свой", callback_data=f"group:prompt_custom:{group_id}")
    builder.button(text="Сбросить на стандартный", callback_data=f"group:prompt_reset:{group_id}")
    builder.button(text="Назад", callback_data=f"group:open:{group_id}")
    builder.adjust(1)
    return builder.as_markup()


def remove_channels_kb(group_id: int, channels: list[Channel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.button(text=f"@{channel.name}", callback_data=f"group:remove_channel:{group_id}:{channel.id}")
    builder.button(text="Назад", callback_data=f"group:open:{group_id}")
    builder.adjust(1)
    return builder.as_markup()


def delete_group_kb(group_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Да, удалить", callback_data=f"group:delete:{group_id}")
    builder.button(text="Назад", callback_data=f"group:open:{group_id}")
    builder.adjust(1)
    return builder.as_markup()
