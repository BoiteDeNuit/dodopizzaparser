from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    MenuButtonWebApp,
    BotCommand,
)

from config import settings

log = logging.getLogger(__name__)

router = Router(name="user")


def _menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🍕 Открыть меню", web_app=WebAppInfo(url=settings.WEBAPP_URL)),
    ]])


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "<b>Привет!</b> 👋\n\n"
        "Это бот с актуальным меню <b>Додо Пиццы</b>.\n"
        "Нажми кнопку <b>«Открыть меню»</b> ниже или используй кнопку меню Telegram, "
        "чтобы посмотреть пиццы, закуски, напитки и десерты с фото и ценами.\n\n"
        "Команды:\n"
        "/menu — открыть меню\n"
        "/help — помощь"
    )
    await message.answer(text, reply_markup=_menu_kb())


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer("Открой меню кнопкой ниже 👇", reply_markup=_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Этот бот показывает актуальное меню Додо Пиццы.\n\n"
        "• /start — приветствие\n"
        "• /menu — открыть WebApp\n\n"
        "Данные обновляются автоматически несколько раз в сутки.",
        reply_markup=_menu_kb(),
    )


@router.errors()
async def errors_handler(event) -> bool:
    log.exception("Ошибка в user bot: %s", event.exception)
    return True


async def _set_menu_button(bot: Bot) -> None:
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="Меню", web_app=WebAppInfo(url=settings.WEBAPP_URL))
    )
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск"),
        BotCommand(command="menu", description="Открыть меню"),
        BotCommand(command="help", description="Помощь"),
    ])


async def run_user_bot() -> None:
    if not settings.BOT_TOKEN or settings.BOT_TOKEN.startswith("PUT_"):
        log.error("BOT_TOKEN не задан в .env — пользовательский бот не стартует")
        return
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    try:
        await _set_menu_button(bot)
    except Exception as e:
        log.warning("Не смог установить menu button: %s", e)
    log.info("User bot polling started")
    await dp.start_polling(bot, handle_signals=False)
