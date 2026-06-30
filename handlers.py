from config import ASSETS
from scraper import fetch_prices
from telegram import Update
from keyboards import main_keyboard, asset_keyboard
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)


# ─── فرمت قیمت ───────────────────────────────────────────────────────────────
def format_price(asset, value: str) -> str:
    if value.startswith(("❌", "⚠️")):
        return f"*{asset.label}*\n{value}"
    return f"*{asset.label}*\n💰 {value} ریال"


def format_all(prices: dict) -> str:
    lines = ["📊 *قیمت‌های لحظه‌ای*\n"]
    for key, asset in ASSETS.items():
        value = prices.get(key, "⚠️ یافت نشد")
        lines.append(format_price(asset, value))
    return "\n\n".join(lines)


# ─── هندلرها ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *سلام\\!*\n\n"
        "به ربات قیمت ارز و طلا خوش آمدید\\.\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    await update.message.reply_text(
        text,
        parse_mode="MarkdownV2",
        reply_markup=main_keyboard(),
    )


def create_asset_handler(key: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        prices = fetch_prices()
        asset = ASSETS[key]
        value = prices.get(key, "⚠️ یافت نشد")
        text = format_price(asset, value)
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=asset_keyboard(key),
        )
    return handler


async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prices = fetch_prices()
    text = format_all(prices)
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


# ─── هندلر تشخیص کلیدواژه در متن پیام ────────────────────────────────────────
def find_asset_by_text(text: str):
    """
    متن پیام را با کلیدواژه‌های هر دارایی مقایسه می‌کند.
    اگر کلیدواژه‌ای پیدا شود، آن asset را برمی‌گرداند، در غیر این صورت None.
    کلیدواژه‌های طولانی‌تر اول چک می‌شوند (مثلاً "دلار آمریکا" قبل از "دلار")
    تا تطبیق دقیق‌تر اولویت داشته باشد.
    """
    text = text.strip()

    for asset in ASSETS.values():
        sorted_keywords = sorted(asset.keywords, key=len, reverse=True)
        for keyword in sorted_keywords:
            if keyword in text:
                return asset
    return None


async def keyword_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    asset = find_asset_by_text(update.message.text)
    if not asset:
        return

    prices = fetch_prices()
    value = prices.get(asset.key, "⚠️ یافت نشد")
    text = format_price(asset, value)

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=asset_keyboard(asset.key),
    )


# ─── هندلر دکمه‌های شیشه‌ای ──────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    prices = fetch_prices()

    if data == "all":
        text = format_all(prices)
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    elif data == "back":
        text = (
            "👋 *سلام!*\n\n"
            "به ربات قیمت ارز و طلا خوش آمدید.\n\n"
            "یکی از گزینه‌های زیر را انتخاب کنید:"
        )
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    elif data in ASSETS:
        asset = ASSETS[data]
        value = prices.get(data, "⚠️ یافت نشد")
        text = format_price(asset, value)
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=asset_keyboard(data),
        )
    else:
        await query.answer("دستور ناشناخته")


# ─── ثبت هندلرها ─────────────────────────────────────────────────────────────
def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("all", send_all))
    app.add_handler(CommandHandler("market", send_all))

    for asset in ASSETS.values():
        app.add_handler(
            CommandHandler(
                asset.command,
                create_asset_handler(asset.key),
            )
        )

    app.add_handler(CallbackQueryHandler(button_handler))

    # هندلر کلیدواژه: باید آخر از همه ثبت شود تا با دستورات تداخل نکند
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            keyword_handler,
        )
    )
