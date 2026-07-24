import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import storage
from config import ASSETS, is_admin
from keyboards import (
    admin_back_keyboard,
    admin_main_keyboard,
    admin_pending_groups_keyboard,
    asset_keyboard,
    main_keyboard,
)
from scraper import get_last_update_timestamp, get_prices

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "👋 *سلام!*\n\n"
    "به ربات قیمت ارز و طلا خوش آمدید.\n\n"
    "یکی از گزینه‌های زیر را انتخاب کنید:"
)

PENDING_GROUP_TEXT = (
    "⏳ این گروه هنوز توسط مدیر ربات تایید نشده است.\n"
    "لطفاً با ادمین ربات هماهنگ کنید تا استفاده از ربات در این گروه فعال شود."
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


# ─── ردیابی کاربر/گروه + دروازه‌ی تایید گروه ─────────────────────────────────
def _track_and_check_allowed(update: Update) -> bool:
    """
    این تابع را باید ابتدای هر هندلری که به کاربر پاسخ می‌دهد صدا زد.
    - اگر پیام از یک چت خصوصی باشد: کاربر را ثبت می‌کند و همیشه True برمی‌گرداند.
    - اگر پیام از یک گروه باشد: گروه را ثبت می‌کند و فقط اگر قبلاً توسط ادمین
      تایید شده باشد True برمی‌گرداند.
    """
    chat = update.effective_chat
    user = update.effective_user

    if chat is None:
        return True

    if chat.type == "private":
        if user is not None:
            storage.track_user(user.id, user.username, user.full_name)
        return True

    if chat.type in ("group", "supergroup"):
        storage.track_group(chat.id, chat.title)
        return storage.is_group_approved(chat.id)

    return True


async def _reply_pending_notice(update: Update) -> None:
    if update.message:
        await update.message.reply_text(PENDING_GROUP_TEXT)


# ─── هندلرها ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _track_and_check_allowed(update):
        await _reply_pending_notice(update)
        return

    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


def create_asset_handler(key: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _track_and_check_allowed(update):
            await _reply_pending_notice(update)
            return

        prices = get_prices()
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
    if not _track_and_check_allowed(update):
        await _reply_pending_notice(update)
        return

    prices = get_prices()
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

    if not _track_and_check_allowed(update):
        await _reply_pending_notice(update)
        return

    prices = get_prices()
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
    data = query.data

    # کال‌بک‌های پنل مدیریت جدا مدیریت می‌شوند
    if data.startswith("admin_"):
        await admin_callback_handler(update, context)
        return

    await query.answer()

    if not _track_and_check_allowed(update):
        await query.answer("این گروه هنوز تایید نشده است.", show_alert=True)
        return

    prices = get_prices()

    if data == "all":
        text = format_all(prices)
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    elif data == "back":
        await query.message.edit_text(
            WELCOME_TEXT,
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


# ─── پنل مدیریت (فقط برای ادمین) ──────────────────────────────────────────────
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None or not is_admin(user.id):
        return  # حتی به کاربر عادی اعلام نمی‌کنیم که چنین پنلی وجود دارد

    await update.message.reply_text(
        "🛠 *پنل مدیریت ربات*",
        parse_mode="Markdown",
        reply_markup=admin_main_keyboard(),
    )

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None or not is_admin(user.id):
        return

    if not context.args:
        await update.message.reply_text(
            "استفاده: /approve <chat_id>\n"
            "مثال: /approve -1001234567890"
        )
        return

    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("chat_id باید یک عدد باشد.")
        return

    storage.approve_group(chat_id)
    await update.message.reply_text(f"✅ گروه با آیدی {chat_id} تایید شد.")

def _format_users_list(users: list[dict]) -> str:
    if not users:
        return "👥 *کاربران*\n\nهنوز هیچ کاربری ثبت نشده."

    lines = [f"👥 *کاربران* (مجموع: {len(users)})\n"]
    # آخرین ۳۰ کاربر بر اساس آخرین بازدید
    recent = sorted(users, key=lambda u: u.get("last_seen", 0), reverse=True)[:30]
    for u in recent:
        name = u.get("full_name") or "بدون نام"
        username = f"@{u['username']}" if u.get("username") else "بدون یوزرنیم"
        lines.append(f"• {name} ({username}) — `{u['id']}`")

    if len(users) > 30:
        lines.append(f"\n… و {len(users) - 30} کاربر دیگر")

    return "\n".join(lines)


def _format_groups_list(groups: list[dict], title: str) -> str:
    if not groups:
        return f"{title}\n\nموردی یافت نشد."

    lines = [f"{title} (مجموع: {len(groups)})\n"]
    for g in groups:
        name = g.get("title") or "بدون عنوان"
        lines.append(f"• {name} — `{g['id']}`")
    return "\n".join(lines)


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if user is None or not is_admin(user.id):
        await query.answer("⛔️ دسترسی ندارید.", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == "admin_home":
        await query.message.edit_text(
            "🛠 *پنل مدیریت ربات*",
            parse_mode="Markdown",
            reply_markup=admin_main_keyboard(),
        )

    elif data == "admin_users":
        users = storage.get_all_users()
        await query.message.edit_text(
            _format_users_list(users),
            parse_mode="Markdown",
            reply_markup=admin_back_keyboard(),
        )

    elif data == "admin_groups":
        groups = storage.get_approved_groups()
        await query.message.edit_text(
            _format_groups_list(groups, "✅ *گروه‌های تایید شده*"),
            parse_mode="Markdown",
            reply_markup=admin_back_keyboard(),
        )

    elif data == "admin_pending":
        pending = storage.get_pending_groups()
        if not pending:
            await query.message.edit_text(
                "🕒 *گروه‌های در انتظار تایید*\n\nموردی یافت نشد.",
                parse_mode="Markdown",
                reply_markup=admin_back_keyboard(),
            )
        else:
            await query.message.edit_text(
                "🕒 *گروه‌های در انتظار تایید*\n\nروی نام هر گروه بزن تا تایید شود:",
                parse_mode="Markdown",
                reply_markup=admin_pending_groups_keyboard(pending),
            )

    elif data == "admin_stats":
        users_count = len(storage.get_all_users())
        approved_count = len(storage.get_approved_groups())
        pending_count = len(storage.get_pending_groups())
        last_update = get_last_update_timestamp()

        if last_update:
            import time
            seconds_ago = int(time.time() - last_update)
            freshness = f"{seconds_ago} ثانیه پیش"
        else:
            freshness = "هنوز اسکرپ نشده"

        text = (
            "📊 *آمار ربات*\n\n"
            f"👥 تعداد کاربران: {users_count}\n"
            f"✅ گروه‌های تایید شده: {approved_count}\n"
            f"🕒 گروه‌های در انتظار: {pending_count}\n"
            f"💹 آخرین به‌روزرسانی قیمت‌ها: {freshness}"
        )
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=admin_back_keyboard(),
        )

    elif data.startswith("admin_approve_"):
        chat_id = int(data.replace("admin_approve_", ""))
        storage.approve_group(chat_id)

        pending = storage.get_pending_groups()
        if pending:
            await query.message.edit_text(
                "✅ تایید شد.\n\n🕒 *گروه‌های در انتظار تایید*",
                parse_mode="Markdown",
                reply_markup=admin_pending_groups_keyboard(pending),
            )
        else:
            await query.message.edit_text(
                "✅ تایید شد. دیگر گروهی در انتظار تایید نیست.",
                parse_mode="Markdown",
                reply_markup=admin_back_keyboard(),
            )


# ─── ثبت هندلرها ─────────────────────────────────────────────────────────────
def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("all", send_all))
    app.add_handler(CommandHandler("market", send_all))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("approve", approve_command))

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
