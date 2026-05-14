# Q CLUB Telegram Bot

Игровая механика «Шоу в кубе» в Telegram-боте: 3 тура по 3 дня, 9 победителей в каждом туре,
автоматические рассылки и админские выгрузки результатов.

Каноническое ТЗ: [`materials/TZ_NORMALIZED.md`](materials/TZ_NORMALIZED.md).

## Стек

- Python 3.13 (минимум 3.11)
- aiogram 3.x (long polling в MVP, webhook опционально)
- SQLAlchemy 2.x (async) + aiomysql / PyMySQL
- Alembic (миграции)
- APScheduler (расписание туров и рассылок, МСК)
- Pydantic v2 (settings)
- openpyxl (XLSX-выгрузки)
- pytest, pytest-asyncio (тесты)

## Структура проекта

```
app/
  bot/                 # Telegram-слой (handlers, keyboards, middlewares)
  core/                # config, logging, time helpers
  db/                  # модели, репозитории, миграции
  services/            # бизнес-логика (туры, победители, рассылки, отчёты)
content/               # YAML с вопросами и шаблонами рассылок
assets/round3/         # картинки для Тура 3 (q1.jpg … q3.jpg — см. `content/round3.yaml`)
scripts/               # CLI-утилиты (seed, ручной запуск победителей и т.п.)
tests/                 # pytest
materials/             # исходные ТЗ + нормализованная версия
```

## Локальный запуск (development)

### MySQL в Docker (рекомендуется для разработки на Mac)

Чтобы вся логика бота (туры, победители, рассылки, админка) шла против **локальной** БД так же, как потом на сервере, поднимите MySQL из корня репозитория:

```bash
docker compose up -d
docker compose ps   # дождаться состояния healthy для сервиса mysql
```

В `.env` задайте параметры из блока «Локальная БД в Docker» в [`.env.example`](.env.example) (`DB_HOST=127.0.0.1`, `DB_NAME=qclub_dev`, `DB_USER=qclub`, `DB_PASSWORD=qclub_dev`). Данные контейнера живут в volume `qclub_mysql_data`; остановка без удаления: `docker compose stop`. Полный сброс БД: `docker compose down -v` (удалит volume).

Дальше — те же шаги, что ниже: `alembic upgrade head`, `seed_content`, запуск бота.

### Окружение Python и зависимости

1. Создать виртуальное окружение и установить зависимости:
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements-dev.txt
   ```
   **Не используйте Python 3.14** для этого проекта: зафиксированные версии `pydantic` / `pydantic-core` пока не ставятся под 3.14 (сборка колеса падает). Нужен интерпретатор **3.11–3.13** (`python3.13`, `python3.12` или `python3.11`).

2. Скопировать и заполнить `.env`:
   ```bash
   cp .env.example .env
   # отредактировать BOT_TOKEN, DB_*, ADMIN_IDS, GAME_START_DATE_MSK
   ```

3. Применить миграции:
   ```bash
   alembic upgrade head
   ```
   Для миграций достаточно в `.env` указать **только переменные `DB_*`** (и при необходимости `DB_HOST`). Поля `BOT_TOKEN` и `GAME_START_DATE_MSK` для Alembic **не обязательны** — URL БД подставляется из `DB_*` или из `ALEMBIC_DATABASE_URL`.

   **Важно (Beget / shared-хостинг):** в панели часто указано `Host: localhost` — это значит «MySQL слушает на сервере хостинга», а **не на твоём Mac**. Команда `alembic upgrade head` с ноутбука с `DB_HOST=localhost` даёт `Connection refused`, потому что к порту 3306 на локальной машине никто не подключён. Варианты:
   - **Запускать миграции по SSH на сервере** (там же, где лежит проект и venv).
   - **SSH-туннель** (пример):  
     `ssh -N -L 3307:127.0.0.1:3306 ЛОГИН@СЕРВЕР`  
     затем в `.env` для локального прогона: `DB_HOST=127.0.0.1`, `DB_PORT=3307` (оставляя имя базы и пользователя как в панели).
   - Если хостер выдаёт **отдельный внешний хост MySQL** (не всегда) — уточни в поддержке и подставь его в `DB_HOST`.

   **Docker на Mac и ошибка `(1045) Access denied for user 'u…_default'@'192.168.65.1'`:** подключение до MySQL доходит (Docker Desktop часто показывает клиента как `192.168.65.1`), но в `.env` остались логин/пароль **с хостинга** (`u3412349_…`). Локальный контейнер знает только пользователя из `docker-compose.yml` (`qclub` / `qclub_dev`). Поставь в `.env` для разработки: `DB_HOST=127.0.0.1`, `DB_NAME=qclub_dev`, `DB_USER=qclub`, `DB_PASSWORD=qclub_dev`. На сервер Beget перед деплоем вернёшь боевые `DB_*`.

4. Засеять контент туров (после Шага 5):
   ```bash
   export PYTHONPATH=.
   python -m scripts.seed_content
   ```

5. Запустить бота:
   ```bash
   python -m app.bot.main
   ```

   Если в логе **Request timeout** / **TelegramNetworkError** при старте — до `api.telegram.org` нет стабильного доступа (часто нужен VPN или другая сеть). Таймаут HTTP в коде увеличен до 120 с; при блокировке это всё равно не поможет без обхода.

   Пока бот запущен, **раз в 5 минут** выполняется отбор победителей по завершённым турам; **раз в час** планируются массовые рассылки из [`content/broadcasts.yaml`](content/broadcasts.yaml) (слоты привязаны к окнам туров в БД); **раз в минуту** отправляется одна готовая рассылка (`PLANNED`, время `scheduled_at` уже прошло). Подробности — `app/services/broadcast_plan.py`, `app/services/broadcast_dispatch.py`.

   Вручную отбор победителей:  
   `PYTHONPATH=. python -m scripts.pick_winners` (опции `--round-id`, `--ignore-end-time` — см. файл скрипта). Для проверки на фиктивных участниках:  
   `PYTHONPATH=. python -m scripts.seed_winner_test_users --round-id … --preset four_then_fifty --nuke` (см. docstring скрипта), затем `pick_winners`.

   **Админка в боте** (Telegram `user_id` из `ADMIN_IDS` в `.env`): `/admin_help`, `/admin_stats`, `/export_csv R1`, `/export_xlsx R1` (R1/R2/R3).

   Команда **`/play`** запускает **активный тур** по окну строки в таблице `rounds` в БД (дни 1–4 → Тур 1, 5–7 → Тур 2, 8–10 → Тур 3; см. `GAME_START_DATE_MSK` и `seed_content`). Вне окна бот сообщит, что тура нет. Тур 3 показывает **фото** из `assets/round3/` (пути в `content/round3.yaml`); если файла нет, вопрос уходит текстом с пометкой. На проде **`RUN_MODE=webhook`** и Nginx — см. `.env.example` и раздел «Деплой» ниже.

## Тесты

```bash
pytest
```

## Деплой

Кратко: на VPS поднимаются **MySQL**, процесс **`python -m app.bot.main`**, **Nginx** с **HTTPS** и прокси **POST** на путь из **`WEBHOOK_PATH`** → **`WEBHOOK_LISTEN_HOST:WEBHOOK_LISTEN_PORT`**. В **`.env`**: **`RUN_MODE=webhook`**, **`WEBHOOK_BASE_URL=https://…`** (без пути), **`WEBHOOK_SECRET`** (рекомендуется), плюс **`DB_*`**, **`BOT_TOKEN`**. После выкладки на **чистую** базу: **`alembic upgrade head`**, **`python -m scripts.seed_content`**, перезапуск сервиса. Если база уже была «засвечена» тестами — см. **`python -m scripts.prelaunch_clean`** и раздел в [`sql.md`](sql.md).

## Прогресс реализации

- [x] Шаг 1. Каркас проекта
- [x] Шаг 2. Конфиг, логирование, МСК-хелперы
- [x] Шаг 3. БД, async engine, alembic init
- [x] Шаг 4. Полная схема данных
- [x] Шаг 5. Контент туров и сидинг
- [x] Шаг 6. Онбординг и валидация email
- [x] Шаг 7. Тур 1 «Миллионер»
- [x] Шаг 8. Тур 2 «Своя игра»
- [x] Шаг 9. Тур 3 «Где логика»
- [x] Шаг 10. Алгоритм победителей + автозапуск (планировщик в `app/bot/main.py`)
- [x] Шаг 11. Рассылки + админка + выгрузки
- [x] Шаг 12. Деплой: webhook в коде, переменные в `.env.example`, см. раздел «Деплой» выше
