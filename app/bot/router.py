"""Сборка Router для Dispatcher."""

from __future__ import annotations

from aiogram import Router

from app.bot.handlers import main_menu, onboarding, round1


def get_root_router() -> Router:
    root = Router()
    root.include_router(onboarding.router)
    root.include_router(round1.router)
    root.include_router(main_menu.router)
    return root
