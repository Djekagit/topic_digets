from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from storage.models import User


async def get_or_create_user(session: AsyncSession, telegram_user: TelegramUser) -> User:
    result = await session.execute(select(User).where(User.tg_id == telegram_user.id))
    user = result.scalar_one_or_none()

    full_name = telegram_user.full_name
    username = telegram_user.username
    if user:
        user.username = username
        user.full_name = full_name
        return user

    user = User(tg_id=telegram_user.id, username=username, full_name=full_name)
    session.add(user)
    await session.flush()
    return user


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    return result.scalar_one_or_none()
