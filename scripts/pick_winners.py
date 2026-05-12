"""CLI: отбор победителей для туров после `ends_at` (или вручную для отладки).

Примеры::

    export PYTHONPATH=.
    python -m scripts.pick_winners

Все подходящие туры (в прошлом, без записи в winner_selections)::

    python -m scripts.pick_winners

Один тур по id строки в ``rounds``::

    python -m scripts.pick_winners --round-id 1

Обойти проверку времени окончания тура (только для локальной отладки)::

    python -m scripts.pick_winners --round-id 1 --ignore-end-time
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import dispose_engine, get_session
from app.db.models import Round
from app.services.winner_selection import ensure_winner_selection, pick_winners_for_due_rounds

log = logging.getLogger(__name__)


async def _amain() -> int:
    parser = argparse.ArgumentParser(description="Отбор победителей тура (считалочка).")
    parser.add_argument(
        "--round-id",
        type=int,
        default=None,
        help="Только этот тур (id из таблицы rounds).",
    )
    parser.add_argument(
        "--ignore-end-time",
        action="store_true",
        help="Не требовать ends_at < now (отладка).",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_dir)

    try:
        if args.round_id is not None:
            async with get_session() as session:
                rnd = await session.get(Round, args.round_id)
                if rnd is None:
                    log.error("Round id=%s not found", args.round_id)
                    return 1
                sel = await ensure_winner_selection(
                    session,
                    rnd,
                    only_after_end=not args.ignore_end_time,
                )
                if sel is None:
                    log.warning(
                        "No selection created (already exists, too early, or no participants)."
                    )
                    return 0
                log.info(
                    "Created winner selection id=%s for round %s (%s)",
                    sel.id,
                    rnd.id,
                    rnd.code,
                )
        else:
            await pick_winners_for_due_rounds()
            log.info("Processed due rounds.")
    finally:
        await dispose_engine()
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
