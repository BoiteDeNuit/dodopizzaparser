from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_BOT_TOKEN: str = os.getenv("ADMIN_BOT_TOKEN", "")

    ADMIN_USERNAMES: list[str] = _split_csv(os.getenv("ADMIN_USERNAMES", ""))
    ADMIN_IDS: list[int] = [int(x) for x in _split_csv(os.getenv("ADMIN_IDS", "")) if x.isdigit()]

    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "https://example.com")

    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    DODO_CITY: str = os.getenv("DODO_CITY", "moscow")
    PARSER_RUNS_PER_DAY: int = int(os.getenv("PARSER_RUNS_PER_DAY", "4"))
    PARSER_HEADLESS: bool = os.getenv("PARSER_HEADLESS", "false").lower() == "true"

    PROXY: Optional[str] = os.getenv("PROXY")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dodo_menu.db")

    DATA_STALE_HOURS: int = 6

    def is_admin(self, user_id: int, username: Optional[str]) -> bool:
        if user_id in self.ADMIN_IDS:
            return True
        if username and username.lstrip("@").lower() in {u.lower() for u in self.ADMIN_USERNAMES}:
            return True
        return False


settings = Settings()
