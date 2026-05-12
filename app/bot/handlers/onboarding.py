"""Онбординг: /start, ввод email, аудит валидации."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
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
    'Добро пожаловать в чат-бот для сотрудников Компании ООО "ФМСМ".\n\n'
    "Внимание! Не передавайте полученный QR-код посторонним лицам.\n\n"
    "Чтобы начать - введи свою почту в поле ввода сообщения:"
)

_EMAIL_ACCEPTED = (
    'Добро пожаловать в "Конкурс в кубе"!\n'
    "Ты можешь вспомнить лучшие моменты яркой трёхлетней истории программы лояльности "
    "Q CLUB и получить шанс выиграть классный приз! Тебя будут ждать три тура: "
    "14.05, 18.05 и 20.05 - мы пришлём напоминания, чтобы ты точно не "
    "пропустил начало. Участвуй в каждом туре и зарабатывай баллы. Желаем тебе удачи!"
)

_WELCOME_BACK = (
    "С возвращением! Ты уже в игре с email <b>{email}</b>.\n\n"
    "Туры «Конкурса в кубе» доступны через /play — следи за датами старта в Q CLUB."
)

_INVITE_REQUIRED = (
    "Бот доступен только по пригласительной ссылке.\n\n"
    "Открой ссылку из письма или сообщения от организаторов (формат: "
    "<code>t.me/...</code> с параметром <code>start</code>). "
    "Если ссылка есть, нажми её ещё раз и затем «Запустить» / Start."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject) -> None:
    settings = get_settings()
    if message.from_user is None:
        return

    start_payload = (command.args or "").strip()

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

        if settings.invite_only and not settings.invite_start_tokens:
            log.error("INVITE_ONLY=true, но INVITE_START_TOKENS пуст — закройте дыру в конфиге.")
            await message.answer(
                "Регистрация через бота временно недоступна. Напиши в поддержку Q CLUB."
            )
            await state.clear()
            return

        if settings.invite_link_enforced():
            if user.invite_gate_passed_at is None:
                if start_payload not in settings.invite_start_token_set:
                    await message.answer(_INVITE_REQUIRED)
                    await state.clear()
                    return
                user.invite_gate_passed_at = datetime.now(UTC).replace(tzinfo=None)

        await state.set_state(OnboardingStates.waiting_email)
        await message.answer(_WELCOME_NEW)


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
                    "Попробуй другой email."
                )
            else:
                await message.answer("Не удалось проверить адрес. Попробуй ещё раз.")
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
    await message.answer(_EMAIL_ACCEPTED)


@router.message(OnboardingStates.waiting_email)
async def need_text_email(message: Message) -> None:
    await message.answer("Пожалуйста, отправь email обычным текстом (без фото и стикеров).")
