"""Полный сброс **игровой** активности для **всех** пользователей.

Удаляет ответы, прогресс по турам и темам, запланированные/завершённые рассылки
и результаты отбора победителей.

**Не трогает:** `users` (регистрация, почта), `rounds`, `round_questions`,
`broadcast_templates`, логи валидации email.

Пример::

    cd Q_Event_show_v_cube && source .venv/bin/activate
    export PYTHONPATH=.
    python -m scripts.reset_all_game_state --yes

Без флага ``--yes`` скрипт только выведет текущие счётчики и выйдет с кодом 1.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import delete, func, select


async def _run(*, do_delete: bool) -> int:
    from app.db.base import dispose_engine, get_session
    from app.db.models import (
        Broadcast,
        BroadcastRecipient,
        UserAnswer,
        UserRoundProgress,
        UserTopicProgress,
        Winner,
        WinnerSelection,
    )

    models_order: list = [
        UserAnswer,
        UserTopicProgress,
        UserRoundProgress,
        BroadcastRecipient,
        Broadcast,
        Winner,
        WinnerSelection,
    ]

    try:
        async with get_session() as session:
            before: dict[str, int] = {}
            for m in models_order:
                key = m.__tablename__
                c = await session.scalar(select(func.count()).select_from(m))
                before[key] = int(c or 0)

            print("Текущее количество строк:")
            for k, v in before.items():
                print(f"  {k}: {v}")
            total = sum(before.values())
            print(f"  — всего: {total}")

            if not do_delete:
                print(
                    "\nУдаление не выполнялось. Для реального сброса запусти с флагом --yes.",
                    file=sys.stderr,
                )
                return 1

            if total == 0:
                print("\nУже пусто, удалять нечего.")
                return 0

            await session.execute(delete(BroadcastRecipient))
            await session.execute(delete(Broadcast))
            await session.execute(delete(WinnerSelection))
            await session.execute(delete(UserAnswer))
            await session.execute(delete(UserTopicProgress))
            await session.execute(delete(UserRoundProgress))
            await session.commit()

            print("\nГотово: игровые данные всех пользователей очищены.")
            return 0
    finally:
        await dispose_engine()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--yes",
        action="store_true",
        help="Подтвердить массовое удаление (обязательно)",
    )
    args = p.parse_args()
    raise SystemExit(asyncio.run(_run(do_delete=args.yes)))


if __name__ == "__main__":
    main()
