"""
ربات تلگرام قیمت ارز و طلا
نیازمندی‌ها: pip install python-telegram-bot requests beautifulsoup4 python-dotenv
"""

import logging
import os
import re
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ASSETS

load_dotenv()

# ─── تنظیمات ────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("توکن ربات یافت نشد! فایل .env را بررسی کنید.")
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── اسکرپر ─────────────────────────────────────────────────────────────────

ASSETS = {
    "usd":  {"keywords": ["دلار آمریکا", "دلار"],   "min": 500_000,  "label": "💵 دلار آمریکا"},
    "eur":  {"keywords": ["یورو"],                   "min": 500_000,  "label": "💶 یورو"},
    "gold": {"keywords": ["طلای ۱۸ عیار", "طلا"],   "min": 5_000_000,"label": "🥇 طلا ۱۸ عیار (هر گرم)"},
}


def fetch_prices() -> dict[str, str]:
    url = f"https://www.tgju.org/?t={int(time.time())}"
    logger.info("در حال دریافت قیمت‌ها...")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("خطا در دریافت صفحه: %s", exc)
        return {key: "❌ خطای اتصال" for key in ASSETS}

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.find_all("tr")
    results: dict[str, str] = {}

    for key, cfg in ASSETS.items():
        found = False
        for row in rows:
            row_text = row.get_text()
            if any(kw in row_text for kw in cfg["keywords"]):
                for cell in row.find_all("td"):
                    cell_text = cell.get_text().strip()
                    match = re.search(r"\d{1,3}(?:,\d{3})+", cell_text)
                    if match:
                        val = int(match.group().replace(",", ""))
                        if val > cfg["min"]:
                            results[key] = match.group()
                            found = True
                            break
            if found:
                break
        if not found:
            results[key] = "⚠️ یافت نشد"

    return results


def format_price_message(key: str, price: str) -> str:
    label = ASSETS[key]["label"]
    if price.startswith(("❌", "⚠️")):
        return f"{label}\n{price}"
    return f"{label}\n`{price}` ریال"


# ─── هندلرهای ربات ──────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👋 سلام! به ربات قیمت ارز خوش اومدی.\n\n"
        "دستورات:\n"
        "/price — قیمت دلار 💵\n"
        "/euro  — قیمت یورو 💶\n"
        "/gold  — قیمت طلا 🥇\n"
        "/all   — همه قیمت‌ها 📊\n"
    )
    await update.message.reply_text(text)


async def cmd_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔄 در حال دریافت قیمت دلار...")
    prices = fetch_prices()
    await update.message.reply_text(format_price_message("usd", prices["usd"]), parse_mode="Markdown")


async def cmd_euro(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔄 در حال دریافت قیمت یورو...")
    prices = fetch_prices()
    await update.message.reply_text(format_price_message("eur", prices["eur"]), parse_mode="Markdown")


async def cmd_gold(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔄 در حال دریافت قیمت طلا...")
    prices = fetch_prices()
    await update.message.reply_text(format_price_message("gold", prices["gold"]), parse_mode="Markdown")


async def cmd_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔄 در حال دریافت همه قیمت‌ها...")
    prices = fetch_prices()
    lines = [
        "📊 *قیمت‌های لحظه‌ای*\n",
        format_price_message("usd",  prices["usd"]),
        format_price_message("eur",  prices["eur"]),
        format_price_message("gold", prices["gold"]),
        f"\n🕒 آخرین بروزرسانی: {time.strftime('%H:%M:%S')}",
    ]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─── اجرا ────────────────────────────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", cmd_price))
    app.add_handler(CommandHandler("euro",  cmd_euro))
    app.add_handler(CommandHandler("gold",  cmd_gold))
    app.add_handler(CommandHandler("all",   cmd_all))
    logger.info("ربات شروع به کار کرد...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
