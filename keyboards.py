from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ASSETS


def main_keyboard() -> InlineKeyboardMarkup:
    """کیبورد اصلی با همه دارایی‌ها + دکمه همه قیمت‌ها"""
    keyboard = []
    row = []

    for asset in ASSETS.values():
        row.append(
            InlineKeyboardButton(
                text=asset.button,
                callback_data=asset.key,
            )
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(
            text="📊 همه قیمت‌ها",
            callback_data="all",
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def asset_keyboard(current_key: str) -> InlineKeyboardMarkup:
    """کیبورد داخل صفحه یک دارایی: دارایی‌های دیگر + بازگشت به همه"""
    keyboard = []
    row = []

    for key, asset in ASSETS.items():
        if key == current_key:
            continue
        row.append(
            InlineKeyboardButton(
                text=asset.button,
                callback_data=asset.key,
            )
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(
            text="📊 همه قیمت‌ها",
            callback_data="all",
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text="🔙 بازگشت",
            callback_data="back",
        )
    ])

    return InlineKeyboardMarkup(keyboard)


# ─── کیبوردهای پنل مدیریت ─────────────────────────────────────────────────────
def admin_main_keyboard() -> InlineKeyboardMarkup:
    """منوی اصلی پنل مدیریت (فقط برای ادمین)"""
    keyboard = [
        [InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("👨‍👩‍👧‍👦 گروه‌های تایید شده", callback_data="admin_groups")],
        [InlineKeyboardButton("🕒 گروه‌های در انتظار تایید", callback_data="admin_pending")],
        [InlineKeyboardButton("📊 آمار ربات", callback_data="admin_stats")],
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_home")]
    ])


def admin_pending_groups_keyboard(pending_groups: list[dict]) -> InlineKeyboardMarkup:
    """برای هر گروه در انتظار تایید، یک دکمه‌ی تایید می‌سازد."""
    keyboard = []
    for group in pending_groups:
        title = group.get("title") or str(group.get("id"))
        keyboard.append([
            InlineKeyboardButton(
                text=f"✅ تایید «{title}»",
                callback_data=f"admin_approve_{group['id']}",
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_home")])
    return InlineKeyboardMarkup(keyboard)
