"""
ربات تلگرام قیمت ارز و طلا
نیازمندی‌ها: pip install python-telegram-bot requests beautifulsoup4 python-dotenv flask
"""

import logging
import os

from dotenv import load_dotenv
from telegram.ext import Application
from telegram.request import HTTPXRequest

from handlers import register_handlers
from keep_alive import keep_alive

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
    )

    return builder.build()


def main():
    keep_alive()  # سرور Flask سبک برای زنده نگه‌داشتن سرویس روی Render

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
