"""
پنل مدیریتی ربات.

فقط کاربرانی که آیدی عددی‌شان در ADMIN_IDS (داخل فایل .env) باشد به این پنل
دسترسی دارند. برای گرفتن آیدی عددی خودتان کافیست به ربات دستور /myid را
بزنید و عدد نمایش داده‌شده را داخل .env قرار دهید:

    ADMIN_IDS=123456789

سپس با دستور /admin در چت خصوصی با ربات، پنل مدیریتی باز می‌شود.
"""
import storage
from config import ADMIN_IDS
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

PAGE_SIZE = 15


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ─── منوها ────────────────────────────────────────────────────────────────
def _admin_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("👥 لیست کاربران", callback_data="admin:users:0")],
        [InlineKeyboardButton("✅ گروه‌های مجاز", callback_data="admin:groups:allowed:0")],
        [InlineKeyboardButton("⏳ گروه‌های در انتظار تایید", callback_data="admin:groups:pending:0")],
        [InlineKeyboardButton("📊 آمار کلی", callback_data="admin:stats")],
    ]
    return InlineKeyboardMarkup(keyboard)


def _back_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:home")]])


def _format_users_page(page: int):
    users = storage.list_users()
    total = len(users)
    start = page * PAGE_SIZE
    chunk = users[start:start + PAGE_SIZE]

    if not chunk:
        return "👥 *لیست کاربران*\n\nهنوز هیچ کاربری ثبت نشده است.", _back_markup()

    lines = [f"👥 *لیست کاربران* (مجموع: {total})\n"]
    for u in chunk:
        username = u.get("username")
        display = f"@{username}" if username else (u.get("first_name") or "بدون‌نام")
        lines.append(f"• `{u['id']}` — {display}")

    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:users:{page - 1}"))
    if start + PAGE_SIZE < total:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:users:{page + 1}"))
    nav.append(InlineKeyboardButton("🔙 بازگشت", callback_data="admin:home"))

    return "\n".join(lines), InlineKeyboardMarkup([nav])


def _format_groups_page(page: int, allowed: bool):
    scope = "allowed" if allowed else "pending"
    groups = [g for g in storage.list_groups() if bool(g.get("allowed")) == allowed]
    total = len(groups)
    start = page * PAGE_SIZE
    chunk = groups[start:start + PAGE_SIZE]

    title = "✅ گروه‌های مجاز" if allowed else "⏳ گروه‌های در انتظار تایید"

    if not chunk:
        return f"{title}\n\nموردی یافت نشد.", _back_markup()

    lines = [f"{title} (مجموع: {total})\n"]
    buttons = []
    for g in chunk:
        gname = g.get("title") or str(g["id"])
        lines.append(f"• {gname} — `{g['id']}`")
        short_name = gname[:24]
        if allowed:
            buttons.append([
                InlineKeyboardButton(
                    f"❌ لغو مجوز: {short_name}",
                    callback_data=f"admin:disallow:{g['id']}:{page}",
                )
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    f"✅ تایید: {short_name}",
                    callback_data=f"admin:allow:{g['id']}:{page}",
                )
            ])

    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:groups:{scope}:{page - 1}"))
    if start + PAGE_SIZE < total:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:groups:{scope}:{page + 1}"))
    nav.append(InlineKeyboardButton("🔙 بازگشت", callback_data="admin:home"))
    buttons.append(nav)

    return "\n".join(lines), InlineKeyboardMarkup(buttons)


def _format_stats():
    users_total = storage.users_count()
    groups = storage.list_groups()
    allowed_count = sum(1 for g in groups if g.get("allowed"))
    pending_count = len(groups) - allowed_count

    text = (
        "📊 *آمار کلی*\n\n"
        f"👥 تعداد کاربران: {users_total}\n"
        f"✅ گروه‌های مجاز: {allowed_count}\n"
        f"⏳ گروه‌های در انتظار تایید: {pending_count}"
    )
    return text, _back_markup()


# ─── هندلرها ─────────────────────────────────────────────────────────────
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not is_admin(user.id):
        return  # عمداً پاسخی داده نمی‌شود تا وجود پنل ادمین به بقیه لو نرود

    await update.message.reply_text(
        "🛠 *پنل مدیریت ربات*\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=_admin_menu(),
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if not user or not is_admin(user.id):
        await query.answer("دسترسی ندارید.", show_alert=True)
        return

    await query.answer()
    data = query.data
    parts = data.split(":")

    if data == "admin:home":
        await query.message.edit_text(
            "🛠 *پنل مدیریت ربات*\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
            parse_mode="Markdown",
            reply_markup=_admin_menu(),
        )
        return

    if data == "admin:stats":
        text, markup = _format_stats()
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
        return

    if parts[1] == "users":
        page = int(parts[2])
        text, markup = _format_users_page(page)
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
        return

    if parts[1] == "groups":
        scope, page = parts[2], int(parts[3])
        text, markup = _format_groups_page(page, allowed=(scope == "allowed"))
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
        return

    if parts[1] in ("allow", "disallow"):
        chat_id, page = int(parts[2]), int(parts[3])
        storage.set_group_allowed(chat_id, allowed=(parts[1] == "allow"))
        # بعد از تغییر، همان صفحه از لیست مقابل (که آیتم به آن منتقل شده) نمایش داده می‌شود
        text, markup = _format_groups_page(0, allowed=(parts[1] == "allow"))
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
        return


def register_admin_handlers(app):
    """
    نکته: این تابع باید قبل از register_handlers (در bot.py) فراخوانی شود
    تا CallbackQueryHandler مخصوص ادمین زودتر از هندلر عمومی دکمه‌ها بررسی شود.
    """
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^admin:"))
