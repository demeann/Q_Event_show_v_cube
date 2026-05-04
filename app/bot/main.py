"""Запуск бота (long polling, MVP)."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import BotCommand

from app.bot.middlewares.access import AccessMiddleware
from app.bot.router import get_root_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import dispose_engine

log = logging.getLogger(__name__)

# По умолчанию в aiogram 60 с — на «медленных» каналах до api.telegram.org этого мало.
_BOT_HTTP_TIMEOUT_SEC = 120.0


async def _run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_dir)

    session = AiohttpSession(timeout=_BOT_HTTP_TIMEOUT_SEC)
    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.update.outer_middleware(AccessMiddleware())
    dp.include_router(get_root_router())

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Регистрация и профиль"),
            BotCommand(command="play", description="Играть в активный тур"),
        ]
    )

    log.info(
        "Bot polling started (parse_mode=HTML, http_timeout=%ss)",
        _BOT_HTTP_TIMEOUT_SEC,
    )
    try:
        await dp.start_polling(bot)
    except TelegramNetworkError as e:
        log.error(
            "Не удаётся достучаться до Telegram API (%s). "
            "Проверь интернет, VPN (если api.telegram.org недоступен), "
            "файрвол и что BOT_TOKEN верный.",
            e,
        )
        raise SystemExit(1) from None
    finally:
        await dispose_engine()
        log.info("Bot stopped")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
