import json
import logging
import re
import threading
import time

import requests
from bs4 import BeautifulSoup

from config import (
    ASSETS,
    CACHE_FILE,
    REQUEST_TIMEOUT,
    SCRAPE_INTERVAL,
    USER_AGENT,
)

logger = logging.getLogger(__name__)

# قفل برای جلوگیری از تداخل خواندن/نوشتن هم‌زمان فایل کش
_file_lock = threading.Lock()


def _scrape_from_web() -> dict:
    """
    یک‌بار صفحه‌ی tgju.org را می‌گیرد و قیمت‌های تعریف‌شده در ASSETS را
    استخراج می‌کند. این تابع فقط توسط ترد پس‌زمینه صدا زده می‌شود، نه به‌صورت
    مستقیم توسط هندلرهای تلگرام.
    """
    url = f"https://www.tgju.org/?t={int(time.time())}"

    headers = {
        "User-Agent": USER_AGENT,
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.find_all("tr")

    result = {}

    for key, asset in ASSETS.items():

        found = False

        for row in rows:

            text = row.get_text()

            if any(keyword in text for keyword in asset.keywords):

                for td in row.find_all("td"):

                    cell = td.get_text(strip=True)

                    match = re.search(r"\d{1,3}(?:,\d{3})+", cell)

                    if not match:
                        continue

                    value = int(match.group().replace(",", ""))

                    if value > asset.minimum:

                        result[key] = match.group()

                        found = True

                        break

            if found:
                break

        if not found:
            result[key] = "⚠️ یافت نشد"

    return result


def _write_cache(prices: dict) -> None:
    payload = {
        "updated_at": time.time(),
        "prices": prices,
    }
    with _file_lock:
        tmp_path = CACHE_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        # جایگزینی اتمیک تا در صورت ری‌استارت وسط نوشتن، فایل خراب نشود
        import os
        os.replace(tmp_path, CACHE_FILE)


def _read_cache() -> dict | None:
    with _file_lock:
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None


def _scrape_and_store_once() -> None:
    try:
        prices = _scrape_from_web()
        _write_cache(prices)
        logger.info("قیمت‌ها به‌روزرسانی و در فایل ذخیره شدند.")
    except requests.RequestException as e:
        logger.error("خطا در دریافت صفحه: %s", e)
    except Exception as e:  # noqa: BLE001 - نمی‌خواهیم ترد پس‌زمینه به‌خاطر خطای غیرمنتظره بمیرد
        logger.exception("خطای غیرمنتظره در اسکرپ: %s", e)


def _scrape_loop() -> None:
    # همان لحظه‌ی استارت، یک‌بار فوری اسکرپ کن تا فایل کش خالی نماند
    _scrape_and_store_once()

    while True:
        time.sleep(SCRAPE_INTERVAL)
        _scrape_and_store_once()


def start_background_scraper() -> None:
    """
    اجرای اسکرپر در یک ترد پس‌زمینه‌ی daemon. باید فقط یک‌بار، هنگام
    بالا آمدن ربات (در bot.py) صدا زده شود.
    """
    thread = threading.Thread(target=_scrape_loop, daemon=True)
    thread.start()
    logger.info(
        "اسکرپر پس‌زمینه شروع شد (هر %s ثانیه یک‌بار قیمت‌ها به‌روزرسانی می‌شوند).",
        SCRAPE_INTERVAL,
    )


def get_prices() -> dict:
    """
    این تابعی است که هندلرهای تلگرام باید صدا بزنند. هرگز مستقیماً به
    tgju.org درخواست نمی‌زند؛ فقط آخرین مقادیر ذخیره‌شده در فایل کش را
    برمی‌گرداند. اگر فایل هنوز ساخته نشده باشد (مثلاً چند لحظه‌ی اول
    راه‌اندازی ربات)، به‌صورت اضطراری یک بار مستقیم اسکرپ می‌کند.
    """
    cached = _read_cache()

    if cached and cached.get("prices"):
        return cached["prices"]

    logger.warning("فایل کش هنوز آماده نیست؛ یک اسکرپ اضطراری انجام می‌شود.")

    try:
        prices = _scrape_from_web()
        _write_cache(prices)
        return prices
    except requests.RequestException as e:
        logger.error("خطا در اسکرپ اضطراری: %s", e)
        return {key: "❌ خطای اتصال" for key in ASSETS}


def get_last_update_timestamp() -> float | None:
    cached = _read_cache()
    if cached:
        return cached.get("updated_at")
    return None
