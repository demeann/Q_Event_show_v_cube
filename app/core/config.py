"""Конфигурация приложения через pydantic-settings.

Источник значений: переменные окружения и `.env`-файл в корне проекта.
Все обязательные поля валидируются при создании `Settings`.

Пример использования::

    from app.core.config import get_settings

    settings = get_settings()
    print(settings.bot_token[:8])
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Путь к корню проекта (на 3 уровня выше: app/core/config.py -> ../../..).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Все настройки бота, загружаемые из окружения / .env."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- Telegram ----------
    bot_token: str = Field(min_length=10)

    # ---------- MySQL ----------
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str
    db_user: str
    db_password: str

    # ---------- Game ----------
    # Дата начала Дня 1 Тура 1 в МСК. Расписание остальных туров и рассылок
    # высчитывается от этой даты.
    game_start_date_msk: date
    # NoDecode отключает встроенный JSON-парсер pydantic-settings для list-полей,
    # чтобы наш `field_validator(mode="before")` получил сырую CSV-строку.
    allowed_email_domains: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # ---------- Admin ----------
    admin_ids: Annotated[list[int], NoDecode] = Field(default_factory=list)

    # ---------- Logging ----------
    log_level: str = "INFO"
    log_dir: Path = Path("logs")

    # ---------- Runtime ----------
    run_mode: Literal["polling", "webhook"] = "polling"
    webhook_base_url: str = ""
    webhook_path: str = "/qclub/webhook"
    webhook_listen_host: str = "127.0.0.1"
    webhook_listen_port: int = 8081

    # ---------------- Validators ----------------

    @field_validator("allowed_email_domains", mode="before")
    @classmethod
    def _parse_email_domains(cls, value):
        """Принимаем список или CSV-строку. Нормализуем в lowercase, без `@`."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            parts = [p.strip().lower().lstrip("@") for p in value.split(",")]
            return [p for p in parts if p]
        if isinstance(value, list):
            return [str(p).strip().lower().lstrip("@") for p in value if str(p).strip()]
        return value

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value):
        """Принимаем список int или CSV-строку с числами."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            parts = [p.strip() for p in value.split(",") if p.strip()]
            return [int(p) for p in parts]
        if isinstance(value, list):
            return [int(p) for p in value]
        return value

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(
                f"Invalid LOG_LEVEL: {value!r}. Allowed: {sorted(allowed)}"
            )
        return normalized

    # ---------------- Computed properties ----------------

    @property
    def db_dsn_async(self) -> str:
        """DSN для async-движка SQLAlchemy (используется приложением)."""
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def db_dsn_sync(self) -> str:
        """DSN для sync-движка (используется Alembic-миграциями)."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    def is_admin(self, telegram_user_id: int) -> bool:
        return telegram_user_id in set(self.admin_ids)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Закэшированный singleton настроек.

    В тестах используется `get_settings.cache_clear()` для пересоздания
    с подменёнными `monkeypatch.setenv`.
    """
    return Settings()
