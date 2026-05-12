"""
Точка входа. Запускает параллельно:
1. FastAPI (отдаёт /api/menu и статику WebApp)
2. Пользовательский Telegram-бот
3. Админский Telegram-бот
4. Планировщик парсера (4 раза в сутки по умолчанию)

Запуск: нажмите Run в PyCharm на этом файле.
"""
from __future__ import annotations

import asyncio
import logging

from api.server import run_api
from bot.admin_bot import run_admin_bot
from bot.user_bot import run_user_bot
from config import settings
from database.db import init_db
from parser.scheduler import setup_scheduler
from utils.logger import setup_logging

log = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()
    log.info("=== Dodo Menu Parser Bot — старт ===")
    log.info("City: %s | Parser headless: %s | Runs/day: %s",
             settings.DODO_CITY, settings.PARSER_HEADLESS, settings.PARSER_RUNS_PER_DAY)

    await init_db()

    scheduler = setup_scheduler()
    scheduler.start()
    log.info("Scheduler запущен")

    tasks = [
        asyncio.create_task(run_api(), name="api"),
        asyncio.create_task(run_user_bot(), name="user_bot"),
        asyncio.create_task(run_admin_bot(), name="admin_bot"),
    ]

    try:
        await asyncio.gather(*tasks)
    except (KeyboardInterrupt, SystemExit):
        log.info("Останов по сигналу")
    finally:
        scheduler.shutdown(wait=False)
        for t in tasks:
            t.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
