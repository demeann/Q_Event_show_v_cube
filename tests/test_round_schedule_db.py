"""Активный тур по окнам starts_at / ends_at."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.db.models import Round, RoundCode, RoundStatus
from app.services.round_schedule import get_playable_round_now


@pytest.mark.asyncio
async def test_no_round_in_gap_between_r2_end_and_r3_start(db_session, monkeypatch):
    """20.05: R2 до 09:45 МСК, R3 с 10:00 МСК — между ними туров нет."""
    db_session.add(
        Round(
            id=2,
            code=RoundCode.R2,
            name="R2",
            starts_at=datetime(2026, 5, 18, 7, 0, 0),
            ends_at=datetime(2026, 5, 20, 6, 45, 0),
            status=RoundStatus.ACTIVE,
        )
    )
    db_session.add(
        Round(
            id=3,
            code=RoundCode.R3,
            name="R3",
            starts_at=datetime(2026, 5, 20, 7, 0, 0),
            ends_at=datetime(2026, 5, 22, 20, 59, 59),
            status=RoundStatus.ACTIVE,
        )
    )
    await db_session.flush()

    monkeypatch.setattr(
        "app.services.round_schedule.now_utc",
        lambda: datetime(2026, 5, 20, 6, 50, 0),
    )
    assert await get_playable_round_now(db_session) is None

    monkeypatch.setattr(
        "app.services.round_schedule.now_utc",
        lambda: datetime(2026, 5, 20, 7, 0, 0),
    )
    active = await get_playable_round_now(db_session)
    assert active is not None
    assert active.code == RoundCode.R3
