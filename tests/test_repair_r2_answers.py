"""Тест скрипта восстановления ответов R2."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import func, select

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
from scripts.repair_r2_answers_after_seed import repair_r2_answers_after_seed


@pytest.mark.asyncio
async def test_repair_inserts_missing_answers(db_session):
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
    db_session.add(
        UserAnswer(
            user_id=1,
            round_id=20,
            question_id=101,
            selected_option="0",
            is_correct=True,
            points_awarded=1,
            answered_at=datetime(2026, 5, 18, 12, 0, 0),
        )
    )
    await db_session.flush()

    dry = await repair_r2_answers_after_seed(db_session, apply=False)
    assert dry["users_repaired"] == 1
    assert dry["answers_inserted"] == 5

    await repair_r2_answers_after_seed(db_session, apply=True)
    await db_session.flush()

    cnt = await db_session.scalar(
        select(func.count())
        .select_from(UserAnswer)
        .where(UserAnswer.user_id == 1, UserAnswer.round_id == 20)
    )
    assert cnt == 6
