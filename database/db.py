from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, delete

from config import settings
from database.models import Base, MenuItem, ParseLog

log = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database initialized: %s", settings.DATABASE_URL)


async def replace_menu(items: Iterable[dict]) -> int:
    """Полностью переписать содержимое menu_items одной транзакцией."""
    items = list(items)
    async with SessionLocal() as s:
        await s.execute(delete(MenuItem))
        now = datetime.utcnow()
        for it in items:
            s.add(MenuItem(
                category=it["category"],
                name=it["name"],
                price=float(it.get("price", 0) or 0),
                in_stock=bool(it.get("in_stock", True)),
                image_url=it.get("image_url", "") or "",
                description=it.get("description", "") or "",
                last_updated=now,
            ))
        await s.commit()
    return len(items)


async def get_all_items() -> list[MenuItem]:
    async with SessionLocal() as s:
        rows = (await s.execute(select(MenuItem).order_by(MenuItem.category, MenuItem.name))).scalars().all()
        return list(rows)


async def get_last_update() -> datetime | None:
    async with SessionLocal() as s:
        row = (await s.execute(select(MenuItem.last_updated).order_by(MenuItem.last_updated.desc()).limit(1))).scalar()
        return row


async def log_parse_start() -> int:
    async with SessionLocal() as s:
        entry = ParseLog(started_at=datetime.utcnow())
        s.add(entry)
        await s.commit()
        return entry.id


async def log_parse_finish(parse_id: int, success: bool, items_count: int, error: str = "") -> None:
    async with SessionLocal() as s:
        entry = await s.get(ParseLog, parse_id)
        if entry is None:
            return
        entry.finished_at = datetime.utcnow()
        entry.success = success
        entry.items_count = items_count
        entry.error = error[:2000]
        await s.commit()


async def get_recent_logs(limit: int = 5) -> list[ParseLog]:
    async with SessionLocal() as s:
        rows = (await s.execute(select(ParseLog).order_by(ParseLog.started_at.desc()).limit(limit))).scalars().all()
        return list(rows)
