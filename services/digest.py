from datetime import datetime
from dataclasses import dataclass

from aiogram import Bot

from bot.helper import save_send
from core.logging import logger
from services.ai import summarize_group_posts
from services.schedule import calculate_next_digest_at
from storage.models import DigestGroup
from storage.requests.post import get_posts_since


@dataclass(frozen=True)
class DigestResult:
    posts_count: int
    sent: bool


async def process_due_group(session, *, bot: Bot, group: DigestGroup, now: datetime) -> DigestResult:
    since = group.last_digest_at or group.created_at
    posts = await get_posts_since(session, channels=group.channels, since=since)
    sent = False

    if posts:
        digest_text = await summarize_group_posts(session, group=group, posts=posts)
        if digest_text.strip():
            await save_send(digest_text, bot, group.user.tg_id)
            sent = True
            logger.info("Digest sent: group_id={}, user_tg_id={}, posts={}", group.id, group.user.tg_id, len(posts))
        else:
            logger.warning("OpenRouter returned empty digest: group_id={}", group.id)
    else:
        logger.info("No new posts for group_id={}", group.id)

    group.last_digest_at = now
    group.next_digest_at = calculate_next_digest_at(now, group.interval_hours)
    return DigestResult(posts_count=len(posts), sent=sent)
