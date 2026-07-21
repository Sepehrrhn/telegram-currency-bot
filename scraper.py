"""
ماژول اسکرپ قیمت‌ها از tgju.org

تغییر مهم نسبت به قبل:
به‌جای اسکرپ در همان لحظه‌ای که کاربر درخواست می‌دهد، یک ترد پس‌زمینه
(start_scraper_loop) هر SCRAPE_INTERVAL_SECONDS ثانیه یک‌بار صفحه را اسکرپ
کرده و نتیجه را در فایل data/prices.json ذخیره می‌کند. هندلرهای ربات فقط
از طریق get_prices() همین فایل را می‌خوانند و دیگر مستقیماً درخواست HTTP
به tgju.org نمی‌زنند. این هم باعث سریع‌تر شدن پاسخ‌گویی ربات می‌شود و هم
فشار کمتری روی سایت مبدا وارد می‌کند.
"""
import json
import logging
import os
import re
import threading
import time

import requests
from bs4 import BeautifulSoup

from config import ASSETS, DATA_DIR, REQUEST_TIMEOUT, SCRAPE_INTERVAL_SECONDS, USER_AGENT

logger = logging.getLogger(__name__)

PRICES_FILE = os.path.join(DATA_DIR, "prices.json")

_file_lock = threading.Lock()


def _scrape_once() -> dict:
    """یک‌بار صفحه‌ی tgju.org را می‌خواند و دیکشنری قیمت‌ها را برمی‌گرداند."""
    url = f"https://www.tgju.org/?t={int(time.time())}"

    headers = {
        "User-Agent": USER_AGENT,
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
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


def _write_to_file(prices: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    payload = {
        "updated_at": time.time(),
        "prices": prices,
    }
    tmp_path = PRICES_FILE + ".tmp"

    with _file_lock:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp_path, PRICES_FILE)  # نوشتن اتمیک، جلوگیری از فایل نصفه‌نیمه


def _read_from_file():
    with _file_lock:
        if not os.path.exists(PRICES_FILE):
            return None
        try:
            with open(PRICES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("خطا در خواندن فایل قیمت‌ها: %s", e)
            return None


def scrape_and_store():
    """
    یک‌بار اسکرپ می‌کند و در فایل ذخیره می‌کند.
    اگر اسکرپ با خطا مواجه شود، فایل قبلی (کش قبلی) دست‌نخورده باقی می‌ماند
    تا کاربران قیمت‌های نسبتاً تازه را همچنان ببینند.
    """
    try:
        prices = _scrape_once()
        _write_to_file(prices)
        logger.info("قیمت‌ها با موفقیت به‌روزرسانی و در فایل ذخیره شدند.")
    except requests.RequestException as e:
        logger.error("خطا در اسکرپ قیمت‌ها (کش قبلی حفظ شد): %s", e)


def get_prices() -> dict:
    """
    هندلرهای ربات فقط باید از این تابع استفاده کنند.
    قیمت‌ها را از فایل ذخیره‌شده روی سرور می‌خواند، نه با اسکرپ مستقیم.
    """
    data = _read_from_file()

    if data and "prices" in data:
        return data["prices"]

    # اگر ربات همین الان بالا آمده و ترد پس‌زمینه هنوز اولین بار را اسکرپ نکرده،
    # یک‌بار به‌صورت فوری اسکرپ می‌کنیم تا کاربر اول با خطا مواجه نشود.
    logger.warning("فایل قیمت‌ها هنوز آماده نیست؛ تلاش برای اسکرپ فوری...")
    try:
        prices = _scrape_once()
        _write_to_file(prices)
        return prices
    except requests.RequestException as e:
        logger.error("اسکرپ فوری هم ناموفق بود: %s", e)
        return {key: "❌ خطای اتصال" for key in ASSETS}


def _background_loop():
    while True:
        scrape_and_store()
        time.sleep(SCRAPE_INTERVAL_SECONDS)


def start_scraper_loop():
    """
    این تابع باید یک‌بار در ابتدای اجرای ربات (در bot.py) فراخوانی شود.
    یک ترد daemon پس‌زمینه راه می‌اندازد که هر SCRAPE_INTERVAL_SECONDS ثانیه
    قیمت‌ها را اسکرپ و در فایل ذخیره می‌کند.
    """
    t = threading.Thread(target=_background_loop, daemon=True)
    t.start()
    logger.info(
        "حلقه پس‌زمینه‌ی اسکرپ قیمت‌ها آغاز شد (هر %s ثانیه یک‌بار).",
        SCRAPE_INTERVAL_SECONDS,
    )
