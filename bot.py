"""
ربات تلگرام قیمت ارز و طلا
نیازمندی‌ها: pip install python-telegram-bot requests beautifulsoup4 python-dotenv flask
"""

import logging
import os

from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import Application
from telegram.request import HTTPXRequest

from config import ASSETS
from handlers import register_handlers
from keep_alive import keep_alive
from scraper import start_background_scraper

load_dotenv()

# ─── تنظیمات ────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")  # فقط برای اجرای لوکال در ایران لازم است

if not BOT_TOKEN:
    raise ValueError("توکن ربات یافت نشد! فایل .env را بررسی کنید.")
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def setup_commands(app: Application):
    """
    ثبت لیست دستورات ربات در منوی Telegram.
    این باعث می‌شود وقتی کاربر "/" را تایپ می‌کند، لیست دستورات
    (مثل /usd، /eur، /gold، /all) به صورت پیشنهادی نمایش داده شود —
    چه در چت خصوصی و چه داخل گروه‌ها.
    """
    commands = [
        BotCommand(asset.command, asset.description)
        for asset in ASSETS.values()
    ]
    commands.append(BotCommand("all", "نمایش همه قیمت‌ها"))
    commands.append(BotCommand("market", "نمایش همه قیمت‌ها"))
    commands.append(BotCommand("start", "شروع کار با ربات"))

    await app.bot.set_my_commands(commands)
    logger.info("لیست دستورات ربات ثبت شد.")


def build_application() -> Application:
    """
    ساخت Application با تنظیمات timeout بالاتر و قابلیت retry.
    این تنظیمات از قطع شدن polling در شبکه‌های ناپایدار جلوگیری می‌کند.
    """
    request = HTTPXRequest(
        connect_timeout=20.0,
        read_timeout=20.0,
        write_timeout=20.0,
        pool_timeout=20.0,
        proxy=PROXY_URL if PROXY_URL else None,
    )

    builder = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(request)
        .post_init(setup_commands)
    )

    return builder.build()


def main():
    keep_alive()  # سرور Flask سبک برای زنده نگه‌داشتن سرویس روی Render
    start_background_scraper()  # اسکرپ خودکار هر ۳۰ ثانیه + ذخیره در فایل کش

    app = build_application()
    register_handlers(app)

    logger.info("ربات در حال اجرا است...")

    # drop_pending_updates: از پردازش پیام‌های قدیمی بعد از ری‌استارت جلوگیری می‌کند
    # allowed_updates: فقط آپدیت‌های لازم را دریافت می‌کند (کارایی بهتر)
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
        poll_interval=1.0,
        timeout=20,
    )


if __name__ == "__main__":
    main()
