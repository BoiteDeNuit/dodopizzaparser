from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BotCommand

from config import settings
from database.db import get_last_update, get_recent_logs, get_all_items
from parser.scheduler import run_parse_once

log = logging.getLogger(__name__)

router = Router(name="admin")


def _is_admin(message: Message) -> bool:
    user = message.from_user
    if user is None:
        return False
    return settings.is_admin(user.id, user.username)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("⛔ Доступ только для администраторов.")
        return
    await message.answer(
        "<b>Админ-панель Dodo Menu Bot</b>\n\n"
        "/update — принудительно перепарсить меню\n"
        "/status — состояние БД и последние запуски\n"
        "/count — количество позиций в меню\n"
        "/help — справка"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if not _is_admin(message):
        return
    await message.answer(
        "Команды:\n"
        "/update — запустить парсер прямо сейчас (≈1–3 минуты)\n"
        "/status — последний апдейт и история запусков\n"
        "/count — сколько позиций сейчас в БД"
    )


@router.message(Command("update"))
async def cmd_update(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("⛔ Только для админов.")
        return
    await message.answer("🚀 Запускаю парсер... Это займёт 1–3 минуты, браузер откроется на сервере.")
    ok, count, err = await run_parse_once(reason=f"admin:{message.from_user.id}")
    if ok:
        await message.answer(f"✅ Готово. Сохранено позиций: <b>{count}</b>")
    else:
        await message.answer(f"❌ Парсинг не удался.\n<code>{err or 'нет данных'}</code>")


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if not _is_admin(message):
        return
    last = await get_last_update()
    logs = await get_recent_logs(5)
    lines = ["<b>Статус</b>"]
    if last:
        delta = datetime.utcnow() - last
        hours = delta.total_seconds() / 3600
        lines.append(f"Последнее обновление: <b>{last:%Y-%m-%d %H:%M UTC}</b> ({hours:.1f}ч назад)")
    else:
        lines.append("БД пуста — запусти /update")
    lines.append("\n<b>История парсинга (последние 5):</b>")
    if not logs:
        lines.append("— пусто —")
    for lg in logs:
        mark = "✅" if lg.success else "❌"
        when = lg.started_at.strftime("%m-%d %H:%M")
        info = f"{lg.items_count} поз." if lg.success else (lg.error[:60] or "ошибка")
        lines.append(f"{mark} {when} — {info}")
    await message.answer("\n".join(lines))


@router.message(Command("count"))
async def cmd_count(message: Message) -> None:
    if not _is_admin(message):
        return
    items = await get_all_items()
    by_cat: dict[str, int] = {}
    for i in items:
        by_cat[i.category] = by_cat.get(i.category, 0) + 1
    if not by_cat:
        await message.answer("БД пуста.")
        return
    lines = [f"<b>Всего:</b> {len(items)}"]
    for cat, n in sorted(by_cat.items()):
        lines.append(f"• {cat}: {n}")
    await message.answer("\n".join(lines))


@router.errors()
async def errors_handler(event) -> bool:
    log.exception("Ошибка в admin bot: %s", event.exception)
    return True


async def run_admin_bot() -> None:
    if not settings.ADMIN_BOT_TOKEN or settings.ADMIN_BOT_TOKEN.startswith("PUT_"):
        log.warning("ADMIN_BOT_TOKEN не задан — админский бот не стартует")
        return
    bot = Bot(token=settings.ADMIN_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="update", description="Перепарсить меню"),
        BotCommand(command="status", description="Состояние"),
        BotCommand(command="count", description="Количество позиций"),
        BotCommand(command="help", description="Помощь"),
    ])
    log.info("Admin bot polling started")
    await dp.start_polling(bot, handle_signals=False)
