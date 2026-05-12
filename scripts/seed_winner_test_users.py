"""Локальная проверка отбора победителей: «мертвые души» в БД + прогон pick_winners.

Только для dev: фиктивные ``telegram_user_id`` в диапазоне ``770000000000+``.

Пример::

    export PYTHONPATH=.
    # id тура из SELECT id, code FROM rounds;
    python -m scripts.seed_winner_test_users --round-id 1 --preset four_then_fifty --nuke
    python -m scripts.pick_winners --round-id 1 --ignore-end-time

Проверка в MySQL::

    SELECT * FROM winner_selections WHERE round_id = 1 \\G
    SELECT * FROM winners WHERE winner_selection_id = ... ORDER BY position;

Пресеты:
    nine_flat        — 9 человек с одним максимумом (все победители, без считалочки).
    josephus12       — 12 с одним баллом (считалочка только среди них, 9 мест).
    four_then_fifty  — 4 с баллом 500 + 30 с баллом 100 (4 авто + считалочка на 5 из 30).
    thin             — 5 участников разных уровней (победителей < 9).
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import delete

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.time import now_utc
from app.db.base import dispose_engine, get_session
from app.db.models import Round, RoundProgressStatus, User, UserRoundProgress, WinnerSelection

# Диапазон synthetic Telegram id (не пересекаются с реальными аккаунтами в проде).
TG_ID_BASE = 770_000_000_000


def _email_for(tg: int, tag: str) -> tuple[str, str]:
    settings = get_settings()
    domain = (
        settings.allowed_email_domains[0]
        if settings.allowed_email_domains
        else "pmru.com"
    )
    local = f"dead_{tag}_{tg}"
    return f"{local}@{domain}", domain


async def _nuke(session, round_id: int) -> None:
    await session.execute(
        delete(WinnerSelection).where(WinnerSelection.round_id == round_id)
    )
    await session.execute(
        delete(User).where(
            User.telegram_user_id >= TG_ID_BASE,
            User.telegram_user_id < TG_ID_BASE + 100_000,
        )
    )


def _preset_rows(name: str) -> list[tuple[str, int]]:
    """(tag, total_score) — порядок вставки задаёт порядок user_id внутри уровня."""
    if name == "nine_flat":
        return [(f"a{i}", 100) for i in range(9)]
    if name == "josephus12":
        return [(f"j{i}", 250) for i in range(12)]
    if name == "four_then_fifty":
        top = [(f"t{i}", 500) for i in range(4)]
        rest = [(f"s{i}", 100) for i in range(30)]
        return top + rest
    if name == "thin":
        return [(f"x{i}", 300 - i * 10) for i in range(5)]
    raise SystemExit(f"unknown preset: {name}")


async def _amain() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round-id", type=int, required=True)
    parser.add_argument(
        "--preset",
        choices=("nine_flat", "josephus12", "four_then_fifty", "thin"),
        default="four_then_fifty",
    )
    parser.add_argument(
        "--nuke",
        action="store_true",
        help="Удалить winner_selections для тура и тестовых users (TG_ID_BASE..).",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_dir)

    rows_spec = _preset_rows(args.preset)
    now_naive = now_utc().replace(tzinfo=None)

    try:
        async with get_session() as session:
            rnd = await session.get(Round, args.round_id)
            if rnd is None:
                print(f"Round id={args.round_id} not found")
                return 1
            round_code = rnd.code.value

            if args.nuke:
                await _nuke(session, args.round_id)

            tg_ids: list[int] = []
            for i, (tag, score) in enumerate(rows_spec):
                tg = TG_ID_BASE + i
                tg_ids.append(tg)
                email, domain = _email_for(tg, tag)
                u = User(
                    telegram_user_id=tg,
                    tg_username=f"dead_{tag}",
                    email=email,
                    email_domain=domain,
                    email_verified_at=now_naive,
                    is_admin=False,
                    is_blocked=False,
                )
                session.add(u)
                await session.flush()
                session.add(
                    UserRoundProgress(
                        user_id=u.id,
                        round_id=args.round_id,
                        status=RoundProgressStatus.FINISHED,
                        total_score=score,
                        started_at=now_naive,
                        finished_at=now_naive,
                        last_answer_at=now_naive,
                    )
                )

        print(f"OK: round {args.round_id} ({round_code}), preset={args.preset}")
        print(f"Created {len(tg_ids)} users, telegram_user_id: {tg_ids[0]} … {tg_ids[-1]}")
        print()
        print("Дальше:")
        print(
            "  PYTHONPATH=. python -m scripts.pick_winners --round-id",
            args.round_id,
            "--ignore-end-time",
        )
        print("или дождаться ends_at тура без --ignore-end-time")
        return 0
    finally:
        await dispose_engine()


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
