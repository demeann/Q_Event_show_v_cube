"""Интеграционные тесты ранжирования (SQLite)."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.db.models import (
    Round,
    RoundCode,
    RoundQuestion,
    RoundStatus,
    User,
    UserAnswer,
    UserRoundProgress,
)
from app.db.models.progress import RoundProgressStatus
from app.services.admin_export import export_round_csv
from app.services.winner_ranking import fetch_ranked_participants


@pytest.mark.asyncio
async def test_r2_perfect_all_when_total_score_max_despite_missing_answers(db_session):
    """После seed: total_score=6, ответов меньше — всё равно perfect для выгрузки."""
    db_session.add(
        Round(
            id=20,
            code=RoundCode.R2,
            name="R2",
            starts_at=datetime(2026, 6, 4, 0, 0, 0),
            ends_at=datetime(2026, 6, 6, 0, 0, 0),
            status=RoundStatus.ACTIVE,
        )
    )
    db_session.add(
        User(
            id=1,
            telegram_user_id=101,
            email="a@pmru.com",
            email_domain="pmru.com",
            email_verified_at=datetime(2026, 1, 1),
            is_admin=False,
            is_blocked=False,
        )
    )
    for i in range(1, 7):
        db_session.add(
            RoundQuestion(
                id=100 + i,
                round_id=20,
                code=f"R2Q{i}",
                order_index=i,
                points=100,
                payload={"options": ["a", "b"], "correct_index": 0},
            )
        )
    await db_session.flush()
    db_session.add(
        UserRoundProgress(
            user_id=1,
            round_id=20,
            status=RoundProgressStatus.FINISHED,
            total_score=6,
            finished_at=datetime(2026, 5, 18, 12, 0, 0),
        )
    )
    for qid in (101, 102, 103, 104):
        db_session.add(
            UserAnswer(
                user_id=1,
                round_id=20,
                question_id=qid,
                selected_option="0",
                is_correct=True,
                points_awarded=1,
                answered_at=datetime(2026, 5, 18, 12, 0, 0),
            )
        )
    await db_session.flush()

    rnd = await db_session.get(Round, 20)
    ranked = await fetch_ranked_participants(db_session, rnd)
    assert len(ranked) == 1
    assert ranked[0].perfect_all is True

    raw = await export_round_csv(db_session, RoundCode.R2)
    text = raw.decode("utf-8-sig")
    assert "да" in text.splitlines()[1]  # all_answers_correct column


@pytest.mark.asyncio
async def test_r1_does_not_perfect_by_score_alone(db_session):
    db_session.add(
        Round(
            id=10,
            code=RoundCode.R1,
            name="R1",
            starts_at=datetime(2026, 6, 1, 0, 0, 0),
            ends_at=datetime(2026, 6, 3, 0, 0, 0),
            status=RoundStatus.ACTIVE,
        )
    )
    db_session.add(
        User(
            id=1,
            telegram_user_id=101,
            email="a@pmru.com",
            email_domain="pmru.com",
            email_verified_at=datetime(2026, 1, 1),
            is_admin=False,
            is_blocked=False,
        )
    )
    db_session.add(
        RoundQuestion(
            id=11,
            round_id=10,
            code="R1Q1",
            order_index=1,
            points=1,
            payload={"options": ["a"], "correct_index": 0},
        )
    )
    await db_session.flush()
    db_session.add(
        UserRoundProgress(
            user_id=1,
            round_id=10,
            status=RoundProgressStatus.FINISHED,
            total_score=1,
        )
    )
    await db_session.flush()

    rnd = await db_session.get(Round, 10)
    ranked = await fetch_ranked_participants(db_session, rnd)
    assert ranked[0].perfect_all is False
