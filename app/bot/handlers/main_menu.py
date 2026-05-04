"""Заглушка для пользователей с подтверждённым email (туры — шаги 7+)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

router = Router(name="main_menu")


@router.message(F.text)
async def placeheld_tours(message: Message) -> None:
    await message.answer(
        "Пока туры подключаются к боту. Совсем скоро здесь можно будет сыграть "
        "во все три дня «Шоу в кубе». Следи за новостями Q CLUB!"
    )
