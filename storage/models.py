from datetime import datetime, timedelta

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from core.settings import settings


DEFAULT_PROMPT = (
    "Сделай краткий дайджест постов. Сгруппируй похожие новости, выдели важное, "
    "оставь ссылки на оригиналы. Посты:\n{posts}"
)


def utcnow() -> datetime:
    return datetime.utcnow()


engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


group_channels = Table(
    "group_channels",
    Base.metadata,
    Column("group_id", ForeignKey("digest_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("channel_id", ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    groups: Mapped[list["DigestGroup"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class DigestGroup(Base):
    __tablename__ = "digest_groups"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_digest_group_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    interval_hours: Mapped[int] = mapped_column(Integer, default=24)
    last_digest_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_digest_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    custom_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="groups")
    channels: Mapped[list["Channel"]] = relationship(
        secondary=group_channels,
        back_populates="groups",
    )


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    url: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    last_parsed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    posts: Mapped[list["Post"]] = relationship(
        back_populates="channel",
        cascade="all, delete-orphan",
    )
    groups: Mapped[list[DigestGroup]] = relationship(
        secondary=group_channels,
        back_populates="channels",
    )


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    url: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    channel: Mapped[Channel] = relationship(back_populates="posts")


class AISettings(Base):
    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), unique=True, default="openrouter")
    model: Mapped[str] = mapped_column(String(255), default="openai/gpt-4o-mini")
    default_prompt: Mapped[str] = mapped_column(Text, default=DEFAULT_PROMPT)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


async def ensure_default_ai_settings(session) -> AISettings:
    from sqlalchemy import select

    result = await session.execute(select(AISettings).where(AISettings.provider == "openrouter"))
    ai_settings = result.scalar_one_or_none()
    if ai_settings:
        return ai_settings

    ai_settings = AISettings(
        provider="openrouter",
        model="openai/gpt-4o-mini",
        default_prompt=DEFAULT_PROMPT,
    )
    session.add(ai_settings)
    await session.flush()
    return ai_settings


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        await ensure_default_ai_settings(session)
        await session.commit()


async def reset_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        await ensure_default_ai_settings(session)
        await session.commit()


def initial_digest_times(interval_hours: int) -> tuple[datetime, datetime]:
    now = utcnow()
    return now, now + timedelta(hours=interval_hours)


start_db = init_db
