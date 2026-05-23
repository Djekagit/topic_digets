from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Сменить модель", callback_data="admin:model")
    builder.button(text="Сменить стандартный промпт", callback_data="admin:prompt")
    builder.adjust(1)
    return builder.as_markup()
