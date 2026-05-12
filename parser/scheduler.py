from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings
from database.db import log_parse_finish, log_parse_start, replace_menu
from parser.dodo_parser import parse_menu

log = logging.getLogger(__name__)

_running = False
_lock = asyncio.Lock()


async def run_parse_once(reason: str = "scheduled") -> tuple[bool, int, str]:
    """Запускает парсер. Браузер блокирующий — крутим в отдельном потоке."""
    global _running
    async with _lock:
        if _running:
            log.warning("Парсинг уже идёт, пропускаю запуск (%s)", reason)
            return False, 0, "already running"
        _running = True
    parse_id = await log_parse_start()
    log.info("=== Старт парсинга (%s) #%d ===", reason, parse_id)
    try:
        items = await asyncio.to_thread(parse_menu)
        if not items:
            await log_parse_finish(parse_id, False, 0, "parser returned 0 items")
            return False, 0, "0 items"
        saved = await replace_menu(items)
        await log_parse_finish(parse_id, True, saved)
        log.info("=== Парсинг #%d ОК, позиций: %d ===", parse_id, saved)
        return True, saved, ""
    except Exception as e:
        log.exception("Парсинг #%d упал: %s", parse_id, e)
        await log_parse_finish(parse_id, False, 0, repr(e))
        return False, 0, repr(e)
    finally:
        _running = False


def setup_scheduler() -> AsyncIOScheduler:
    """Распределяет N запусков в сутки равномерно + случайный джиттер ±20 минут."""
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    runs = max(1, min(6, settings.PARSER_RUNS_PER_DAY))
    step = 24 // runs
    for i in range(runs):
        hour = (i * step + random.randint(0, max(0, step - 1))) % 24
        minute = random.randint(0, 59)
        scheduler.add_job(
            run_parse_once,
            CronTrigger(hour=hour, minute=minute),
            kwargs={"reason": f"cron-{i}"},
            id=f"parse-{i}",
            misfire_grace_time=3600,
        )
        log.info("Парсер запланирован на %02d:%02d MSK (slot %d)", hour, minute, i)
    return scheduler
