"""Сборка Router для Dispatcher."""

from __future__ import annotations

from aiogram import Router

from app.bot.handlers import main_menu, onboarding


def get_root_router() -> Router:
    root = Router()
    root.include_router(onboarding.router)
    root.include_router(main_menu.router)
    return root
