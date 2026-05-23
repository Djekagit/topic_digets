import aiohttp
from aiogram import Bot

from core.logging import logger
from storage.models import async_session, utcnow
from storage.requests.channel import get_channels
from storage.requests.group import get_due_groups
from storage.requests.post import save_post_if_new
from services.digest import process_due_group
from services.telegram_parser import fetch_channel_posts


async def parse_channels(session, channels) -> int:
    if not channels:
        return 0

    total_saved = 0
    async with aiohttp.ClientSession() as http_session:
        for channel in channels:
            try:
                parsed_posts = await fetch_channel_posts(http_session, channel)
                saved_count = 0
                for post in parsed_posts:
                    saved = await save_post_if_new(
                        session,
                        channel=channel,
                        text=post.text,
                        date=post.date,
                        url=post.url,
                    )
                    saved_count += int(saved)
                total_saved += saved_count
                channel.last_parsed_at = utcnow()
                logger.info("Channel parsed: name={}, saved_posts={}", channel.name, saved_count)
            except Exception as exc:
                logger.exception("Failed to parse channel {}: {}", channel.name, exc)
    return total_saved


async def parse_all_channels() -> None:
    async with async_session() as session:
        channels = await get_channels(session)
        if not channels:
            return

        await parse_channels(session, channels)
        await session.commit()


async def send_due_digests(bot: Bot) -> None:
    now = utcnow()
    async with async_session() as session:
        groups = await get_due_groups(session, now)
        for group in groups:
            try:
                await process_due_group(session, bot=bot, group=group, now=now)
            except Exception as exc:
                logger.exception("Failed to process digest group {}: {}", group.id, exc)
        await session.commit()
