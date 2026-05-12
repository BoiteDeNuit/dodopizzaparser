# Dodo Menu Parser Bot

Telegram-бот с WebApp, который показывает актуальное меню **dodopizza.ru**.
Парсер на `undetected-chromedriver` имитирует поведение человека, чтобы обходить Cloudflare.

## Что внутри

- **Пользовательский бот** — `/start`, `/menu`, кнопка меню Telegram → WebApp.
- **Админский бот** (отдельный токен) — `/update`, `/status`, `/count`.
- **FastAPI** — отдаёт `/api/menu` и статику WebApp (`webapp/`).
- **Парсер** — `undetected-chromedriver`, headful, рандомные паузы 3–7 сек, скроллинг, движения мыши.
- **APScheduler** — 4 запуска в сутки (настраивается).
- **SQLite** — таблицы `menu_items` и `parse_logs`.

---

## Первый запуск — пошагово

### 1. Создать двух ботов в @BotFather

В Telegram найди [@BotFather](https://t.me/BotFather) и сделай две команды `/newbot`:

1. **Основной бот** (для пользователей). Получишь токен `123456:AA...` — это `BOT_TOKEN`.
2. **Админский бот** (для тебя). Второй токен — это `ADMIN_BOT_TOKEN`.

### 2. Поднять WebApp на HTTPS

Telegram открывает WebApp **только по HTTPS**. Локально проще всего через `ngrok`:

```powershell
# В отдельном окне PowerShell, после запуска main.py:
ngrok http 8000
```

Скопируй HTTPS-URL вида `https://abcd-1234.ngrok-free.app` — это `WEBAPP_URL`.

Альтернативы:
- VPS с nginx + Let's Encrypt
- Cloudflare Tunnel (`cloudflared tunnel --url http://localhost:8000`)
- Деплой статики (`webapp/`) на Vercel/Netlify, а API — где удобно

### 3. Зарегистрировать WebApp у BotFather

У основного бота:
```
/setdomain  → укажи домен из WEBAPP_URL без https://
/setmenubutton → название "Меню", URL — WEBAPP_URL
```
Бот сам выставит кнопку меню при первом запуске, но `/setdomain` всё равно нужен.

### 4. Заполнить `.env`

Открой `.env` и впиши:

```env
BOT_TOKEN=123456:AAA...           # от @BotFather, основной бот
ADMIN_BOT_TOKEN=789012:BBB...     # от @BotFather, админский бот
ADMIN_USERNAMES=golden_wreath     # твой username без @
WEBAPP_URL=https://abcd.ngrok-free.app   # HTTPS URL из шага 2
DODO_CITY=moscow                  # slug города
PARSER_HEADLESS=false             # обязательно false для обхода Cloudflare
```

### 5. Установить зависимости

В корне проекта (`F:\BOTS\dodo_menu_parser_bot\`):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> **Важно про Chrome:** `undetected-chromedriver` использует установленный Google Chrome.
> Убедись, что он установлен. Драйвер скачивается автоматически при первом запуске.

### 6. Запустить

В PyCharm нажми **Run** на `main.py`.
Или из терминала:

```powershell
python main.py
```

Что должно произойти:
- FastAPI поднимется на `http://127.0.0.1:8000`
- Оба бота начнут polling
- Планировщик запланирует 4 запуска парсинга на сутки

### 7. Первое наполнение БД

БД пустая при первом запуске. Напиши **админскому боту** команду `/update` — он откроет браузер и спарсит меню (1–3 минуты). После этого WebApp начнёт отдавать данные.

---

## Структура проекта

```
dodo_menu_parser_bot/
├── main.py              # точка входа
├── config.py            # настройки из .env
├── .env / .env.example
├── requirements.txt
├── bot/
│   ├── user_bot.py      # /start, /menu, кнопка WebApp
│   └── admin_bot.py     # /update, /status, /count
├── api/
│   └── server.py        # FastAPI: /api/menu + статика webapp/
├── parser/
│   ├── dodo_parser.py   # undetected-chromedriver, селекторы
│   └── scheduler.py     # APScheduler + блокировка одновременных запусков
├── database/
│   ├── models.py        # MenuItem, ParseLog
│   └── db.py
├── webapp/
│   ├── index.html       # WebApp UI
│   ├── style.css
│   └── app.js
└── utils/logger.py
```

## Настройка прокси

В `.env` раскомментируй:
```
PROXY=socks5://user:pass@host:port
```
Прокси передастся как в браузер парсера, так и в aiogram-сессии (через расширение, если надо).

## Если парсер не находит товары

Сайт Додо периодически меняет вёрстку. CSS-селекторы лежат в `parser/dodo_parser.py` в словаре `SELECTORS` — правь их, не переписывая остальной код. Можно проверить руками: открыть DevTools на `https://dodopizza.ru/moscow/pizza`, найти стабильные классы карточек.

## Проверка приёмки

- ✅ Бот отвечает на `/start`, `/menu`, открывает WebApp
- ✅ WebApp показывает фото, цены, названия (20+ позиций)
- ✅ Парсер обновляет БД ≥ 4 раза в сутки
- ✅ Этот README покрывает установку и переменные окружения

## Известные ограничения

- `undetected-chromedriver` в headful режиме требует видимый рабочий стол (Windows локально — ок, на Linux-сервере нужен `Xvfb`).
- Если Cloudflare всё-таки покажет капчу — парсер залогирует ошибку и попробует на следующем cron-слоте. Для гарантии можно подключить 2Captcha.
- Cайт может выложить меню через `globalapi.dodopizza.com` — если найдёшь стабильный публичный JSON-endpoint, переключение туда сильно надёжнее браузера.
