import os
from dataclasses import dataclass
from typing import Self

from dotenv import load_dotenv


def _split_admin_ids(value: str | None) -> list[int]:
    if not value:
        return []

    admin_ids: list[int] = []
    for raw_id in value.replace(";", ",").split(","):
        raw_id = raw_id.strip()
        if not raw_id:
            continue
        try:
            admin_ids.append(int(raw_id))
        except ValueError as exc:
            raise ValueError(f"ADMIN_IDS contains a non-integer value: {raw_id}") from exc
    return admin_ids


def _normalize_database_url(value: str) -> str:
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+asyncpg://", 1)
    return value


@dataclass(frozen=True)
class Settings:
    tg_token: str
    database_url: str
    admin_ids: list[int]
    openrouter_api_key: str
    proxy: str | None = None

    @classmethod
    def from_env(cls, *, load_dotenv_file: bool = True) -> Self:
        if load_dotenv_file:
            load_dotenv()

        database_url = os.getenv("DATABASE_URL")
        if database_url:
            database_url = _normalize_database_url(database_url)
        else:
            user_db = os.getenv("USER_DB", "")
            password_db = os.getenv("PASSWORD_DB", "")
            db_name = os.getenv("DB_NAME", "")
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT")
            host_part = f"{host}:{port}" if port else host
            database_url = f"postgresql+asyncpg://{user_db}:{password_db}@{host_part}/{db_name}"

        return cls(
            tg_token=os.getenv("TG_TOKEN") or os.getenv("TgToken", ""),
            database_url=database_url,
            admin_ids=_split_admin_ids(os.getenv("ADMIN_IDS")),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            proxy=os.getenv("PROXY") or None,
        )


settings = Settings.from_env()
