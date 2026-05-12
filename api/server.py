from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database.db import get_all_items, get_last_update

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
WEBAPP_DIR = BASE_DIR / "webapp"


def create_app() -> FastAPI:
    app = FastAPI(title="Dodo Menu API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/api/menu")
    async def menu():
        items = await get_all_items()
        last = await get_last_update()
        stale = False
        if last is None:
            stale = True
        else:
            stale = (datetime.utcnow() - last) > timedelta(hours=settings.DATA_STALE_HOURS)
        return {
            "last_updated": last.isoformat() if last else None,
            "stale": stale,
            "stale_hours": settings.DATA_STALE_HOURS,
            "count": len(items),
            "items": [
                {
                    "id": i.id,
                    "category": i.category,
                    "name": i.name,
                    "price": i.price,
                    "in_stock": i.in_stock,
                    "image_url": i.image_url,
                    "description": i.description,
                }
                for i in items
            ],
        }

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    if WEBAPP_DIR.exists():
        app.mount("/", StaticFiles(directory=str(WEBAPP_DIR), html=True), name="webapp")
    return app


async def run_api() -> None:
    config = uvicorn.Config(
        create_app(),
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    log.info("FastAPI запущен на http://%s:%s", settings.API_HOST, settings.API_PORT)
    await server.serve()
