from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from storage.models import Channel, Post


async def save_post_if_new(
    session: AsyncSession,
    *,
    channel: Channel,
    text: str,
    date: datetime,
    url: str,
) -> bool:
    result = await session.execute(select(Post.id).where(Post.url == url))
    if result.scalar_one_or_none() is not None:
        return False

    session.add(Post(channel=channel, text=text, date=date, url=url))
    return True


async def get_posts_since(
    session: AsyncSession,
    *,
    channels: list[Channel],
    since: datetime,
) -> list[Post]:
    if not channels:
        return []

    channel_ids = [channel.id for channel in channels]
    result = await session.execute(
        select(Post)
        .where(Post.channel_id.in_(channel_ids), Post.date > since)
        .order_by(Post.date.asc())
    )
    return list(result.scalars().all())
