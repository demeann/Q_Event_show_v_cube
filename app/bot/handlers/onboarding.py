"""Онбординг: /start, ввод email, аудит валидации."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.states import OnboardingStates
from app.core.config import get_settings
from app.db.base import get_session
from app.db.models import EmailValidationLog
from app.services.email_validation import check_corporate_email
from app.services.user_service import get_or_create_user

log = logging.getLogger(__name__)

router = Router(name="onboarding")

_WELCOME_NEW = (
    "Привет! Это бот Q CLUB — игры «Шоу в кубе».\n\n"
    "Чтобы присоединиться, пришли <b>корпоративный email</b> "
    "на домене <code>@pmru.com</code> или <code>@contracted.pmru.com</code>. "
    "Коды подтверждения не нужны — мы просто проверим домен.\n\n"
    "Напиши адрес одним сообщением. Отмена: /cancel."
)

_WELCOME_BACK = (
    "С возвращением! Ты уже в игре с email <b>{email}</b>.\n\n"
    "Туры и кнопки появятся в следующих обновлениях — следи за объявлениями в Q CLUB."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    settings = get_settings()
    if message.from_user is None:
        return

    if settings.is_admin(message.from_user.id):
        async with get_session() as session:
            user = await get_or_create_user(
                session,
                message.from_user.id,
                message.from_user.username,
            )
            user.is_admin = True
            if user.is_blocked:
                await message.answer(
                    "Доступ для этого аккаунта ограничен. "
                    "Если кажется, что это ошибка — напиши в поддержку Q CLUB."
                )
                await state.clear()
                return
        await state.clear()
        await message.answer(
            "Ты в списке <b>администраторов</b> — доступ без проверки email. "
            "Обычным участникам по-прежнему нужен корпоративный адрес.\n\n"
            "Дальше здесь появятся админка и туры."
        )
        return

    async with get_session() as session:
        user = await get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
        )

        if user.is_blocked:
            await message.answer(
                "Доступ для этого аккаунта ограничен. "
                "Если кажется, что это ошибка — напиши в поддержку Q CLUB."
            )
            await state.clear()
            return

        if user.email_verified_at is not None and user.email:
            await state.clear()
            await message.answer(_WELCOME_BACK.format(email=user.email))
            return

        await state.set_state(OnboardingStates.waiting_email)
        await message.answer(_WELCOME_NEW)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Я бот «Шоу в кубе» (Q CLUB).\n\n"
        "/start — регистрация по корпоративному email\n"
        "/cancel — отменить ввод email\n"
        "/help — эта подсказка"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Ок, остановились. Когда будешь готов — снова /start.")


@router.message(OnboardingStates.waiting_email, F.text)
async def process_email(message: Message, state: FSMContext) -> None:
    settings = get_settings()
    if message.from_user is None:
        return

    raw = message.text or ""
    result = check_corporate_email(raw, settings.allowed_email_domains)

    async with get_session() as session:
        user = await get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
        )
        if settings.is_admin(user.telegram_user_id):
            user.is_admin = True

        masked = (
            result.normalized_email
            if result.normalized_email
            else (raw.strip() if raw.strip() else "(empty)")
        )
        log_row = EmailValidationLog(
            telegram_user_id=message.from_user.id,
            email=masked[:255],
            is_valid=result.ok,
            reason=result.reason[:64],
        )
        session.add(log_row)

        if not result.ok:
            if result.reason == "empty":
                await message.answer("Похоже, адрес пустой. Пришли email текстом.")
            elif result.reason == "invalid_format":
                await message.answer(
                    "Не похоже на email. Проверь опечатки и пришли снова, например: "
                    "<code>ivanov@pmru.com</code>"
                )
            elif result.reason == "domain_not_allowed":
                await message.answer(
                    "Этот домен не подходит. Нужен корпоративный адрес на "
                    "<code>@pmru.com</code> или <code>@contracted.pmru.com</code>.\n"
                    "Попробуй другой email или напиши /cancel."
                )
            else:
                await message.answer("Не удалось проверить адрес. Попробуй ещё раз или /cancel.")
            log.info(
                "email_reject uid=%s reason=%s",
                message.from_user.id,
                result.reason,
            )
            return

        now = datetime.now(UTC).replace(tzinfo=None)
        user.email = result.normalized_email
        user.email_domain = result.domain
        user.email_verified_at = now

    await state.clear()
    await message.answer(
        "Отлично, email принят — добро пожаловать в «Шоу в кубе»!\n\n"
        "Дальше здесь появятся туры и кнопки — пока можешь просто ждать старта."
    )


@router.message(OnboardingStates.waiting_email)
async def need_text_email(message: Message) -> None:
    await message.answer("Пожалуйста, отправь email обычным текстом (без фото и стикеров).")
