from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from core.settings import settings


class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user and user.id in settings.admin_ids:
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer("Нет доступа к админке.")
        elif isinstance(event, CallbackQuery):
            await event.answer("Нет доступа к админке.", show_alert=True)
        return None
