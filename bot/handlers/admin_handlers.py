from aiogram import F, Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.fsm.admin import AdminSettings
from bot.keyboards.admin import admin_menu_kb
from core.settings import settings
from storage.models import async_session
from storage.requests.ai_settings import get_ai_settings, update_ai_model, update_default_prompt


router = Router()


def _mask_key(value: str) -> str:
    if not value:
        return "не задан"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


@router.message(Command("admin"))
async def admin_settings_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        ai_settings = await get_ai_settings(session)
        await session.commit()

    text = (
        "Админ-панель\n\n"
        "Провайдер: OpenRouter\n"
        f"Модель: {ai_settings.model}\n"
        f"API-ключ: {_mask_key(settings.openrouter_api_key)}\n"
        f"Стандартный промпт: {ai_settings.default_prompt[:500]}"
    )
    await message.answer(text, reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:model")
async def change_model_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminSettings.model)
    await callback.message.answer("Введите модель OpenRouter, например openai/gpt-4o-mini:")
    await callback.answer()


@router.message(AdminSettings.model)
async def change_model_handler(message: Message, state: FSMContext) -> None:
    model = message.text.strip()
    if not model:
        await message.answer("Модель не может быть пустой.")
        return

    async with async_session() as session:
        await update_ai_model(session, model)
        await session.commit()

    await state.clear()
    await message.answer("Модель обновлена.", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:prompt")
async def change_default_prompt_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminSettings.default_prompt)
    await callback.message.answer(
        'Введите новый стандартный промпт. Можно использовать {posts}; если не использовать, я добавлю в конец "Посты:" и список постов.'
    )
    await callback.answer()


@router.message(AdminSettings.default_prompt)
async def change_default_prompt_handler(message: Message, state: FSMContext) -> None:
    prompt = message.text.strip()
    if not prompt:
        await message.answer("Промпт не может быть пустым.")
        return

    async with async_session() as session:
        await update_default_prompt(session, prompt)
        await session.commit()

    await state.clear()
    await message.answer("Стандартный промпт обновлен.", reply_markup=admin_menu_kb())
