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
