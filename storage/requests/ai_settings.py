from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from storage.models import AISettings, ensure_default_ai_settings, utcnow


async def get_ai_settings(session: AsyncSession) -> AISettings:
    result = await session.execute(select(AISettings).where(AISettings.provider == "openrouter"))
    ai_settings = result.scalar_one_or_none()
    if ai_settings:
        return ai_settings
    return await ensure_default_ai_settings(session)


async def update_ai_model(session: AsyncSession, model: str) -> AISettings:
    ai_settings = await get_ai_settings(session)
    ai_settings.model = model.strip()
    ai_settings.updated_at = utcnow()
    await session.flush()
    return ai_settings


async def update_default_prompt(session: AsyncSession, prompt: str) -> AISettings:
    ai_settings = await get_ai_settings(session)
    ai_settings.default_prompt = prompt.strip()
    ai_settings.updated_at = utcnow()
    await session.flush()
    return ai_settings
