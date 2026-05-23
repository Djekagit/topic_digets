import asyncio
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.handlers.admin_handlers import router as admin_router
from bot.handlers.user_handlers import router as user_router
from bot.middlewares.admin import AdminMiddleware
from core.logging import logger, setup_logging
from core.settings import settings
from services.jobs import parse_all_channels, send_due_digests
from storage.models import init_db


async def main() -> None:
    setup_logging()
    if not settings.tg_token:
        raise RuntimeError("TG_TOKEN is not configured")

    await init_db()

    bot = Bot(
        settings.tg_token,
        default=DefaultBotProperties(
            link_preview_is_disabled=True,
            parse_mode=ParseMode.HTML,
        ),
    )
    dp = Dispatcher()

    admin_router.message.middleware(AdminMiddleware())
    admin_router.callback_query.middleware(AdminMiddleware())
    dp.include_router(admin_router)
    dp.include_router(user_router)

    scheduler = AsyncIOScheduler(timezone=ZoneInfo("UTC"))
    scheduler.add_job(
        parse_all_channels,
        "interval",
        minutes=10,
        id="parse_all_channels",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        send_due_digests,
        "interval",
        minutes=1,
        kwargs={"bot": bot},
        id="send_due_digests",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    logger.info("Topic digests bot started")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
