from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from storage.models import Channel


async def get_or_create_channel(session: AsyncSession, name: str) -> Channel:
    result = await session.execute(select(Channel).where(Channel.name == name))
    channel = result.scalar_one_or_none()
    if channel:
        return channel

    channel = Channel(name=name, url=f"https://t.me/{name}")
    session.add(channel)
    await session.flush()
    return channel


async def get_channels(session: AsyncSession) -> list[Channel]:
    result = await session.execute(
        select(Channel)
        .join(Channel.groups)
        .options(selectinload(Channel.groups))
        .order_by(Channel.name)
    )
    return list(result.scalars().unique().all())
