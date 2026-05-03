# Q CLUB Telegram Bot

Игровая механика «Шоу в кубе» в Telegram-боте: 3 тура по 3 дня, 9 победителей в каждом туре,
автоматические рассылки и админские выгрузки результатов.

Каноническое ТЗ: [`materials/TZ_NORMALIZED.md`](materials/TZ_NORMALIZED.md).

## Стек

- Python 3.11
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
assets/round3/         # картинки для Тура 3
scripts/               # CLI-утилиты (seed, ручной запуск победителей и т.п.)
tests/                 # pytest
deploy/                # инструкции и скрипты деплоя
materials/             # исходные ТЗ + нормализованная версия
```

## Локальный запуск (development)

1. Создать виртуальное окружение и установить зависимости:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements-dev.txt
   ```

2. Скопировать и заполнить `.env`:
   ```bash
   cp .env.example .env
   # отредактировать BOT_TOKEN, DB_*, ADMIN_IDS, GAME_START_DATE_MSK
   ```

3. Применить миграции (после Шага 3):
   ```bash
   alembic upgrade head
   ```

4. Засеять контент туров (после Шага 5):
   ```bash
   python -m scripts.seed_content
   ```

5. Запустить бота (после Шага 6):
   ```bash
   python -m app.bot.main
   ```

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
- [ ] Шаг 4. Полная схема данных
- [ ] Шаг 5. Контент туров и сидинг
- [ ] Шаг 6. Онбординг и валидация email
- [ ] Шаг 7. Тур 1 «Миллионер»
- [ ] Шаг 8. Тур 2 «Своя игра»
- [ ] Шаг 9. Тур 3 «Где логика»
- [ ] Шаг 10. Алгоритм победителей + автозапуск
- [ ] Шаг 11. Рассылки + админка + выгрузки
- [ ] Шаг 12. Деплой-чеклист
# Q_Event_show_v_cube
