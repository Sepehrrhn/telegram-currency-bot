"""
ربات تلگرام قیمت ارز و طلا
نیازمندی‌ها: pip install python-telegram-bot requests beautifulsoup4 python-dotenv
"""

import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application
from handlers import register_handlers

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


# ─── اجرا ────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    register_handlers(app)
    logger.info("ربات در حال اجرا است...")
    app.run_polling()


if __name__ == "__main__":
    main()
