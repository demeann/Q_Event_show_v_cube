"""Окна туров в seed_content (календарь МСК → UTC в БД)."""

from __future__ import annotations

from datetime import date, datetime

from app.db.models.round import RoundCode
from scripts.seed_content import _round_utc_bounds, _round_windows


def test_r3_first_day_is_game_start_plus_6() -> None:
    game_start = date(2026, 5, 14)
    _name, r3_first, r3_last = _round_windows(game_start)[RoundCode.R3]
    assert r3_first == date(2026, 5, 20)
    assert r3_last == date(2026, 5, 22)


def test_r3_starts_at_07_00_utc_naive() -> None:
    """10:00 МСК в мае = 07:00 UTC (naive в БД)."""
    game_start = date(2026, 5, 14)
    _name, r3_first, r3_last = _round_windows(game_start)[RoundCode.R3]
    starts_at, _ends_at = _round_utc_bounds(RoundCode.R3, r3_first, r3_last)
    assert starts_at == datetime(2026, 5, 20, 7, 0, 0)


def test_r2_last_day_ends_at_09_45_msk() -> None:
    """09:45 МСК последнего дня R2 = 06:45 UTC (май, UTC+3)."""
    game_start = date(2026, 5, 14)
    _name, r2_first, r2_last = _round_windows(game_start)[RoundCode.R2]
    assert r2_last == date(2026, 5, 20)
    _start, ends_at = _round_utc_bounds(RoundCode.R2, r2_first, r2_last)
    assert ends_at == datetime(2026, 5, 20, 6, 45, 0)
