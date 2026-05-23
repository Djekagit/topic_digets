import math as m

from aiogram import Bot
from aiogram.enums.parse_mode import ParseMode

from core.logging import logger


async def save_send(text: str, bot: Bot, chat_id: int) -> None:
    limit = 4096
    parts_count = m.ceil(len(text) / limit) or 1
    logger.info("Sending message: chat_id={}, length={}, parts={}", chat_id, len(text), parts_count)

    for index in range(parts_count):
        chunk = text[index * limit : (index + 1) * limit]
        await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=ParseMode.HTML)
