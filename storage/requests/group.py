from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from storage.models import DigestGroup, User, initial_digest_times
from storage.requests.channel import get_or_create_channel


async def create_digest_group(
    session: AsyncSession,
    *,
    user: User,
    name: str,
    channel_names: list[str],
    interval_hours: int,
    custom_prompt: str | None = None,
) -> DigestGroup:
    existing = await get_group_by_name(session, user_id=user.id, name=name)
    if existing:
        raise ValueError("Группа с таким названием уже существует")

    channels = [await get_or_create_channel(session, channel_name) for channel_name in channel_names]
    last_digest_at, next_digest_at = initial_digest_times(interval_hours)
    group = DigestGroup(
        user_id=user.id,
        name=name,
        interval_hours=interval_hours,
        last_digest_at=last_digest_at,
        next_digest_at=next_digest_at,
        custom_prompt=custom_prompt,
        is_active=True,
    )
    session.add(group)
    group.channels = channels
    await session.flush()
    return group


async def get_group_by_name(session: AsyncSession, *, user_id: int, name: str) -> DigestGroup | None:
    result = await session.execute(
        select(DigestGroup)
        .where(DigestGroup.user_id == user_id, DigestGroup.name == name)
        .options(selectinload(DigestGroup.channels), selectinload(DigestGroup.user))
    )
    return result.scalar_one_or_none()


async def get_group_for_user(session: AsyncSession, *, group_id: int, tg_id: int) -> DigestGroup | None:
    result = await session.execute(
        select(DigestGroup)
        .join(DigestGroup.user)
        .where(DigestGroup.id == group_id, User.tg_id == tg_id)
        .options(selectinload(DigestGroup.channels), selectinload(DigestGroup.user))
    )
    return result.scalar_one_or_none()


async def get_user_groups(session: AsyncSession, *, tg_id: int) -> list[DigestGroup]:
    result = await session.execute(
        select(DigestGroup)
        .join(DigestGroup.user)
        .where(User.tg_id == tg_id)
        .options(selectinload(DigestGroup.channels))
        .order_by(DigestGroup.name)
    )
    return list(result.scalars().all())


async def get_due_groups(session: AsyncSession, now: datetime) -> list[DigestGroup]:
    result = await session.execute(
        select(DigestGroup)
        .where(
            DigestGroup.is_active.is_(True),
            DigestGroup.next_digest_at.is_not(None),
            DigestGroup.next_digest_at <= now,
        )
        .options(
            selectinload(DigestGroup.channels),
            selectinload(DigestGroup.user),
        )
        .order_by(DigestGroup.next_digest_at.asc())
    )
    return list(result.scalars().all())


async def add_channels_to_group(
    session: AsyncSession,
    *,
    group: DigestGroup,
    channel_names: list[str],
) -> int:
    existing = {channel.name for channel in group.channels}
    added = 0
    for channel_name in channel_names:
        if channel_name in existing:
            continue
        group.channels.append(await get_or_create_channel(session, channel_name))
        existing.add(channel_name)
        added += 1
    await session.flush()
    return added


async def remove_channel_from_group(
    session: AsyncSession,
    *,
    group: DigestGroup,
    channel_id: int,
) -> bool:
    for channel in list(group.channels):
        if channel.id == channel_id:
            group.channels.remove(channel)
            await session.flush()
            return True
    return False


async def delete_group(session: AsyncSession, *, group: DigestGroup) -> None:
    await session.execute(delete(DigestGroup).where(DigestGroup.id == group.id))


def update_group_interval(group: DigestGroup, *, interval_hours: int, now: datetime) -> None:
    group.interval_hours = interval_hours
    group.next_digest_at = now + timedelta(hours=interval_hours)


def update_group_prompt(group: DigestGroup, prompt: str | None) -> None:
    group.custom_prompt = prompt.strip() if prompt and prompt.strip() else None
