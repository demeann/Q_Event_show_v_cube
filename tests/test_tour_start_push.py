"""Пуши старта тура: не дублировать через /play; не слать после ends_at."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.db.models import Round, User, UserRoundProgress
from app.db.models.progress import RoundProgressStatus
from app.db.models.round import RoundCode, RoundStatus
from app.services.tour_start_push import (
    send_r1_intro_immediately_after_email_verified,
    try_send_tour_push_for_user,
)


@pytest.mark.asyncio
async def test_try_send_skips_when_user_has_round_progress(db_session, monkeypatch):
    async def boom(*_a, **_kw):
        raise AssertionError("_send_one_push must not be called")

    monkeypatch.setattr("app.services.tour_start_push._send_one_push", boom)

    u = User(
        telegram_user_id=424242,
        email_verified_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    db_session.add(u)
    rnd = Round(
        code=RoundCode.R1,
        name="Тур 1",
        starts_at=datetime(2026, 1, 1, 0, 0, 0),
        ends_at=datetime(2030, 1, 1, 0, 0, 0),
        status=RoundStatus.ACTIVE,
    )
    db_session.add(rnd)
    await db_session.flush()

    db_session.add(
        UserRoundProgress(
            user_id=u.id,
            round_id=rnd.id,
            status=RoundProgressStatus.NOT_STARTED,
            total_score=0,
        )
    )
    await db_session.flush()

    bot = AsyncMock()
    await try_send_tour_push_for_user(db_session, bot, user_id=u.id, round_row=rnd)
    assert u.tour_push_r1_sent_at is None


@pytest.mark.asyncio
async def test_try_send_when_no_progress(db_session, monkeypatch):
    calls: list[int] = []

    async def fake_send(*_a, **_kw):
        calls.append(1)
        return True

    monkeypatch.setattr("app.services.tour_start_push._send_one_push", fake_send)

    u = User(
        telegram_user_id=424243,
        email_verified_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    db_session.add(u)
    rnd = Round(
        code=RoundCode.R1,
        name="Тур 1",
        starts_at=datetime(2026, 1, 1, 0, 0, 0),
        ends_at=datetime(2030, 1, 1, 0, 0, 0),
        status=RoundStatus.ACTIVE,
    )
    db_session.add(rnd)
    await db_session.flush()

    bot = AsyncMock()
    await try_send_tour_push_for_user(db_session, bot, user_id=u.id, round_row=rnd)
    assert len(calls) == 1
    assert u.tour_push_r1_sent_at is not None


@pytest.mark.asyncio
async def test_try_send_skips_when_round_window_ended(db_session, monkeypatch):
    async def boom(*_a, **_kw):
        raise AssertionError("_send_one_push must not be called")

    monkeypatch.setattr("app.services.tour_start_push._send_one_push", boom)
    monkeypatch.setattr(
        "app.services.tour_start_push.now_utc",
        lambda: datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
    )

    u = User(
        telegram_user_id=424244,
        email_verified_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    db_session.add(u)
    rnd = Round(
        code=RoundCode.R1,
        name="Тур 1",
        starts_at=datetime(2026, 1, 1, 0, 0, 0),
        ends_at=datetime(2026, 1, 10, 0, 0, 0),
        status=RoundStatus.ACTIVE,
    )
    db_session.add(rnd)
    await db_session.flush()

    bot = AsyncMock()
    await try_send_tour_push_for_user(db_session, bot, user_id=u.id, round_row=rnd)
    assert u.tour_push_r1_sent_at is None


@pytest.mark.asyncio
async def test_send_r1_intro_after_email_sends_when_before_r1_end_even_if_before_start(
    db_session, monkeypatch
):
    calls: list[int] = []

    async def fake_send(*_a, **_kw):
        calls.append(1)
        return True

    monkeypatch.setattr("app.services.tour_start_push._send_one_push", fake_send)
    monkeypatch.setattr(
        "app.services.tour_start_push.now_utc",
        lambda: datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc),
    )

    @asynccontextmanager
    async def fake_get_session():
        yield db_session

    monkeypatch.setattr(
        "app.services.tour_start_push.get_session",
        fake_get_session,
    )

    u = User(
        telegram_user_id=424245,
        email_verified_at=datetime(2026, 5, 10, 11, 0, 0),
    )
    db_session.add(u)
    db_session.add(
        Round(
            code=RoundCode.R1,
            name="Тур 1",
            starts_at=datetime(2026, 5, 14, 0, 0, 0),
            ends_at=datetime(2026, 5, 20, 23, 59, 59),
            status=RoundStatus.ACTIVE,
        )
    )
    await db_session.flush()
    bot = AsyncMock()

    await send_r1_intro_immediately_after_email_verified(
        bot, telegram_user_id=424245
    )
    assert len(calls) == 1
    assert u.tour_push_r1_sent_at is not None


@pytest.mark.asyncio
async def test_send_r1_intro_after_email_skips_when_r1_ended(db_session, monkeypatch):
    async def boom(*_a, **_kw):
        raise AssertionError("_send_one_push must not be called")

    monkeypatch.setattr("app.services.tour_start_push._send_one_push", boom)
    monkeypatch.setattr(
        "app.services.tour_start_push.now_utc",
        lambda: datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
    )

    @asynccontextmanager
    async def fake_get_session():
        yield db_session

    monkeypatch.setattr(
        "app.services.tour_start_push.get_session",
        fake_get_session,
    )

    u = User(
        telegram_user_id=424247,
        email_verified_at=datetime(2026, 5, 18, 11, 0, 0),
    )
    db_session.add(u)
    db_session.add(
        Round(
            code=RoundCode.R1,
            name="Тур 1",
            starts_at=datetime(2026, 5, 14, 7, 0, 0),
            ends_at=datetime(2026, 5, 17, 21, 0, 0),
            status=RoundStatus.ACTIVE,
        )
    )
    await db_session.flush()
    bot = AsyncMock()

    await send_r1_intro_immediately_after_email_verified(
        bot, telegram_user_id=424247
    )
    assert u.tour_push_r1_sent_at is None


@pytest.mark.asyncio
async def test_send_r1_intro_after_email_sends_even_with_round_progress(
    db_session, monkeypatch
):
    calls: list[int] = []

    async def fake_send(*_a, **_kw):
        calls.append(1)
        return True

    monkeypatch.setattr("app.services.tour_start_push._send_one_push", fake_send)

    @asynccontextmanager
    async def fake_get_session():
        yield db_session

    monkeypatch.setattr(
        "app.services.tour_start_push.get_session",
        fake_get_session,
    )

    u = User(
        telegram_user_id=424246,
        email_verified_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    db_session.add(u)
    rnd = Round(
        code=RoundCode.R1,
        name="Тур 1",
        starts_at=datetime(2026, 1, 1, 0, 0, 0),
        ends_at=datetime(2030, 1, 1, 0, 0, 0),
        status=RoundStatus.ACTIVE,
    )
    db_session.add(rnd)
    await db_session.flush()
    db_session.add(
        UserRoundProgress(
            user_id=u.id,
            round_id=rnd.id,
            status=RoundProgressStatus.NOT_STARTED,
            total_score=0,
        )
    )
    await db_session.flush()
    bot = AsyncMock()

    await send_r1_intro_immediately_after_email_verified(
        bot, telegram_user_id=424246
    )
    assert len(calls) == 1
