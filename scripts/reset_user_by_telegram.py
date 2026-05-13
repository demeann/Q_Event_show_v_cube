"""Сброс регистрации (почта) и игрового прогресса по ``telegram_user_id``.

Пример::

    cd Q_Event_show_v_cube && source .venv/bin/activate
    export PYTHONPATH=.
    python -m scripts.reset_user_by_telegram 201343602

После сброса в Telegram: /start — снова приветствие и ввод почты.
"""

from __future__ import annotations

import argparse
import asyncio
import sys


async def _run(telegram_user_id: int) -> int:
    from app.db.base import dispose_engine, get_session
    from app.services.admin_progress_reset import reset_all_game_progress_for_user
    from app.services.user_service import get_user_by_telegram_id

    uid: int | None = None
    async with get_session() as session:
        u = await get_user_by_telegram_id(session, telegram_user_id)
        if u is None:
            print(f"Пользователь telegram_user_id={telegram_user_id} не найден в БД.", file=sys.stderr)
            return 1
        uid = u.id
        await reset_all_game_progress_for_user(session, u.id)
        u.email = None
        u.email_domain = None
        u.email_verified_at = None
        u.invite_gate_passed_at = None

    assert uid is not None
    print(
        f"Готово: internal user id={uid}, telegram_user_id={telegram_user_id} — "
        "почта сброшена, ответы и прогресс по турам удалены."
    )
    await dispose_engine()
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("telegram_user_id", type=int, help="Telegram user id (число)")
    args = p.parse_args()
    raise SystemExit(asyncio.run(_run(args.telegram_user_id)))


if __name__ == "__main__":
    main()
