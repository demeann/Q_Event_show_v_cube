"""Тур 1 «Кто хочет стать миллионером»: команда /play и ответы по callback."""

from __future__ import annotations

from typing import Any

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from app.core.config import get_settings
from app.db.base import get_session
from app.db.models import RoundCode, RoundQuestion, User, UserRoundProgress
from app.services.round1_play import (
    get_next_round1_question,
    on_question_shown,
    try_answer_round1,
)
from app.services.round_schedule import get_playable_round_now
from app.services.user_service import get_user_by_telegram_id

router = Router(name="round1")


class R1Pick(CallbackData, prefix="r1"):
    qid: int
    idx: int


def _btn_caption(text: str, max_len: int = 64) -> str:
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _options_from_payload(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("options")
    if not isinstance(raw, list) or not raw:
        return []
    return [str(x) for x in raw]


def _question_caption(q: RoundQuestion) -> str:
    body = str(q.payload.get("text", ""))
    return f"<b>Вопрос {q.order_index}.</b>\n\n{body}"


def _r1_keyboard(q: RoundQuestion) -> InlineKeyboardMarkup:
    opts = _options_from_payload(q.payload)
    rows = [
        [
            InlineKeyboardButton(
                text=_btn_caption(label),
                callback_data=R1Pick(qid=q.id, idx=i).pack(),
            )
        ]
        for i, label in enumerate(opts)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _gate_user(session, from_user_id: int) -> tuple[User | None, str | None]:
    settings = get_settings()
    user = await get_user_by_telegram_id(session, from_user_id)
    if user is None:
        return None, "Сначала нажми /start."
    if user.is_blocked:
        return None, "Доступ для этого аккаунта ограничен."
    if user.email_verified_at is None and not settings.is_admin(from_user_id):
        return None, "Сначала подтверди корпоративный email: /start"
    return user, None


@router.message(Command("play"))
async def cmd_play(message: Message) -> None:
    if message.from_user is None:
        return
    async with get_session() as session:
        user, err = await _gate_user(session, message.from_user.id)
        if err:
            await message.answer(err)
            return

        active = await get_playable_round_now(session)
        if active is None:
            await message.answer(
                "Сейчас нет активного тура. Даты игры совпадают с настройкой "
                "внутри Q CLUB — загляни в объявления или к организаторам."
            )
            return
        if active.code != RoundCode.R1:
            await message.answer(
                "Сейчас запущен другой тур «Шоу в кубе». Прохождение этого формата "
                "в боте появится в следующих обновлениях."
            )
            return

        nq = await get_next_round1_question(session, user.id, active)
        if nq is None:
            await message.answer(
                "Ты уже прошёл все вопросы Тура 1. Отличная работа! Жди следующий тур."
            )
            return

        await on_question_shown(session, user.id, active)
        await message.answer(
            _question_caption(nq),
            reply_markup=_r1_keyboard(nq),
        )


@router.callback_query(R1Pick.filter())
async def on_r1_pick(query: CallbackQuery, callback_data: R1Pick) -> None:
    if query.from_user is None or query.message is None:
        return
    msg = query.message
    async with get_session() as session:
        user, err = await _gate_user(session, query.from_user.id)
        if err:
            await query.answer(err, show_alert=True)
            return

        active = await get_playable_round_now(session)
        if active is None or active.code != RoundCode.R1:
            await query.answer("Сейчас нельзя ответить в этом туре.", show_alert=True)
            return

        q_row = await session.get(RoundQuestion, callback_data.qid)
        if (
            q_row is None
            or q_row.round_id != active.id
            or not _options_from_payload(q_row.payload)
        ):
            await query.answer("Вопрос устарел. Нажми /play снова.", show_alert=True)
            return

        ok, awarded, err_msg = await try_answer_round1(
            session,
            user_id=user.id,
            round_row=active,
            question=q_row,
            selected_idx=callback_data.idx,
        )
        if not ok:
            await query.answer(err_msg or "Ошибка", show_alert=True)
            return

        await query.answer()

        if awarded > 0:
            feedback = f"Верно! +{awarded} баллов."
        else:
            feedback = (
                "Увы, не в этот раз.\n\n"
                "Баллы не снимаем — держим удар и идём дальше."
            )
        await msg.answer(feedback)

        nq = await get_next_round1_question(session, user.id, active)
        if nq is None:
            pr = await session.execute(
                select(UserRoundProgress).where(
                    UserRoundProgress.user_id == user.id,
                    UserRoundProgress.round_id == active.id,
                )
            )
            prog = pr.scalar_one_or_none()
            total = prog.total_score if prog else 0
            await msg.answer(
                f"Тур 1 завершён! Сумма баллов: <b>{total}</b>.\n"
                "Спасибо за игру — скоро подключим следующие туры."
            )
            return

        await on_question_shown(session, user.id, active)
        await msg.answer(
            _question_caption(nq),
            reply_markup=_r1_keyboard(nq),
        )
