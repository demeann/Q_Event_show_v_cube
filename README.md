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
assets/round3/         # картинки для Тура 3 (q1.jpg … q5.jpg — см. `content/round3.yaml`)
scripts/               # CLI-утилиты (seed, ручной запуск победителей и т.п.)
tests/                 # pytest
deploy/                # инструкции и скрипты деплоя
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

## Тесты

```bash
pytest
```

## Деплой

См. [`deploy/README.md`](deploy/README.md) (появится на Шаге 12).

## Прогресс реализации

- [x] Шаг 1. Каркас проекта
- [x] Шаг 2. Конфиг, логирование, МСК-хелперы
- [x] Шаг 3. БД, async engine, alembic init
- [x] Шаг 4. Полная схема данных
- [x] Шаг 5. Контент туров и сидинг
- [x] Шаг 6. Онбординг и валидация email
- [ ] Шаг 7. Тур 1 «Миллионер»
- [ ] Шаг 8. Тур 2 «Своя игра»
- [ ] Шаг 9. Тур 3 «Где логика»
- [ ] Шаг 10. Алгоритм победителей + автозапуск
- [ ] Шаг 11. Рассылки + админка + выгрузки
- [ ] Шаг 12. Деплой-чеклист
