"""
Парсер меню dodopizza.ru через undetected-chromedriver.

Сайт Додо — фактически SPA: всё меню живёт на одной странице города
(https://dodopizza.ru/moscow), категории — секции с заголовками <h2> внутри.
Парсер скроллит страницу до конца, чтобы дотянуться до всех ленивых блоков,
и собирает карточки, привязывая их к ближайшей секции.

ВНИМАНИЕ: headful-режим обязателен для обхода Cloudflare.
Селекторы вынесены в SELECTORS — если сайт сменит вёрстку, правьте только их.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException

from config import settings

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG_DIR = BASE_DIR / "debug"

# Эвристика: пробуем несколько селекторов подряд — какие-то сработают,
# даже если Додо переименует классы.
SELECTORS = {
    # Карточка товара на dodopizza.ru — <article data-testid="menu__meta-product_...">
    "product_card": "article[data-testid^='menu__meta-product_']",
    "card_title": "h3",
    "card_price": "span.money__value",
    "card_image": "img",
    "card_description": "p",
    "city_confirm": ",".join([
        "button[data-testid='locality-confirmation-confirm']",
        "button[class*='confirm']",
    ]),
}

# Маппинг внутреннего слага категории (data-menu-product-kind) на читабельный заголовок.
CATEGORY_MAP = {
    "pizza": "Пиццы",
    "combo": "Комбо",
    "snack": "Закуски",
    "snacks": "Закуски",
    "dessert": "Десерты",
    "desserts": "Десерты",
    "drink": "Напитки",
    "drinks": "Напитки",
    "sauce": "Соусы",
    "sauces": "Соусы",
    "breakfast": "Завтраки",
    "other": "Другое",
    "kids": "Детям",
}


@dataclass
class MenuItemDTO:
    category: str
    name: str
    price: float
    in_stock: bool
    image_url: str
    description: str = ""


def _human_sleep(a: float = 3.0, b: float = 7.0) -> None:
    time.sleep(random.uniform(a, b))


def _smooth_scroll_to_bottom(driver, max_steps: int = 40) -> None:
    """Постепенно скроллит до конца страницы, чтобы триггернуть lazy-load."""
    last_h = 0
    for i in range(max_steps):
        driver.execute_script("window.scrollBy(0, arguments[0]);", random.randint(500, 1100))
        time.sleep(random.uniform(0.4, 1.0))
        h = driver.execute_script("return document.body.scrollHeight")
        if h == last_h and i > 5:
            # уже на дне
            break
        last_h = h


def _mouse_jitter(driver) -> None:
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        actions = ActionChains(driver)
        for _ in range(random.randint(2, 5)):
            actions.move_to_element_with_offset(body, random.randint(10, 400), random.randint(10, 400))
            actions.pause(random.uniform(0.1, 0.4))
        actions.perform()
    except WebDriverException:
        pass


def _parse_price(text: str) -> float:
    digits = "".join(ch for ch in text if ch.isdigit() or ch == ",")
    digits = digits.replace(",", ".")
    try:
        return float(digits) if digits else 0.0
    except ValueError:
        return 0.0


def _build_driver() -> uc.Chrome:
    options = uc.ChromeOptions()
    if settings.PARSER_HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=ru-RU,ru")
    if settings.PROXY:
        options.add_argument(f"--proxy-server={settings.PROXY}")
    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.set_page_load_timeout(60)
    return driver


def _try_dismiss_city_popup(driver) -> None:
    """Если выскочил поп-ап подтверждения города — нажимаем."""
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, SELECTORS["city_confirm"])
        for b in btns:
            try:
                if b.is_displayed():
                    b.click()
                    log.info("Закрыл поп-ап подтверждения города")
                    time.sleep(1)
                    return
            except WebDriverException:
                continue
    except WebDriverException:
        pass


def _category_for_card(card) -> str:
    """Категорию берём прямо из атрибута data-menu-product-kind карточки."""
    try:
        kind = (card.get_attribute("data-menu-product-kind") or "").lower().strip()
    except WebDriverException:
        kind = ""
    return CATEGORY_MAP.get(kind, kind.capitalize() if kind else "Меню")


def _collect_all_cards(driver) -> list[MenuItemDTO]:
    items: list[MenuItemDTO] = []
    cards = driver.find_elements(By.CSS_SELECTOR, SELECTORS["product_card"])
    log.info("Найдено карточек на странице: %d", len(cards))
    seen = set()
    for card in cards:
        try:
            name = ""
            name_el = card.find_elements(By.CSS_SELECTOR, SELECTORS["card_title"])
            if name_el:
                name = name_el[0].text.strip()
            if not name:
                # fallback на aria-label у <article>
                name = (card.get_attribute("aria-label") or "").strip()
            if not name or len(name) < 2:
                continue

            price = 0.0
            price_el = card.find_elements(By.CSS_SELECTOR, SELECTORS["card_price"])
            if price_el:
                price = _parse_price(price_el[0].text)

            img_url = ""
            img_el = card.find_elements(By.CSS_SELECTOR, SELECTORS["card_image"])
            if img_el:
                img_url = (
                    img_el[0].get_attribute("src")
                    or img_el[0].get_attribute("data-src")
                    or img_el[0].get_attribute("srcset")
                    or ""
                )
                if "," in img_url:  # srcset вида "url1 1x, url2 2x"
                    img_url = img_url.split(",")[0].strip().split(" ")[0]

            description = ""
            desc_el = card.find_elements(By.CSS_SELECTOR, SELECTORS["card_description"])
            if desc_el:
                description = desc_el[0].text.strip()[:500]

            category = _category_for_card(card)

            key = (category, name)
            if key in seen:
                continue
            seen.add(key)

            items.append(MenuItemDTO(
                category=category,
                name=name,
                price=price,
                in_stock=price > 0,
                image_url=img_url,
                description=description,
            ))
        except WebDriverException as e:
            log.warning("Не смог распарсить карточку: %s", e)
    return items


def _save_debug(driver, tag: str) -> None:
    """Сохраняет скриншот и HTML для разбора, если карточки не найдены."""
    try:
        DEBUG_DIR.mkdir(exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        png = DEBUG_DIR / f"{tag}-{ts}.png"
        html = DEBUG_DIR / f"{tag}-{ts}.html"
        driver.save_screenshot(str(png))
        html.write_text(driver.page_source, encoding="utf-8")
        log.warning("Сохранил отладку: %s, %s", png, html)
    except Exception as e:
        log.warning("Не смог сохранить отладку: %s", e)


def parse_menu() -> list[dict]:
    """Главная точка входа. Возвращает список dict для записи в БД."""
    url = f"https://dodopizza.ru/{settings.DODO_CITY}"
    driver = _build_driver()
    try:
        log.info("Открываю: %s", url)
        driver.get(url)
        _human_sleep(5, 9)

        _try_dismiss_city_popup(driver)
        _mouse_jitter(driver)

        # ждём появления хотя бы одной карточки
        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS["product_card"]))
            )
        except TimeoutException:
            log.warning("Карточки не появились — Cloudflare/капча или сменилась вёрстка")
            _save_debug(driver, "no-cards-initial")
            return []

        # докручиваем страницу, чтобы прогрузить ленивые блоки
        _smooth_scroll_to_bottom(driver, max_steps=50)
        _human_sleep(2, 4)
        _mouse_jitter(driver)

        items = _collect_all_cards(driver)
        if not items:
            _save_debug(driver, "no-cards-after-scroll")
        log.info("Всего собрано позиций: %d", len(items))
        return [asdict(x) for x in items]
    finally:
        try:
            driver.quit()
        except Exception:
            pass
