"""
ماژول ذخیره‌سازی ساده روی فایل (JSON) برای:
- لیست کاربرانی که با ربات تعامل داشته‌اند
- لیست گروه‌هایی که ربات در آن‌ها عضو است و وضعیت مجاز/غیرمجاز بودن‌شان

این داده‌ها روی دیسک سرور نگه‌داری می‌شوند. توجه: اگر روی Render از پلن رایگان
(بدون Persistent Disk) استفاده می‌کنید، این فایل‌ها بعد از هر دیپلوی/ری‌استارت
سرویس ریست می‌شوند. برای نگه‌داری دائمی، از یک Persistent Disk در Render
استفاده کنید و مسیر پوشه‌ی data را روی آن دیسک قرار دهید.
"""
import json
import logging
import os
import threading
import time
from typing import Optional

from config import DATA_DIR

logger = logging.getLogger(__name__)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")

_lock = threading.Lock()


def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("خطا در خواندن فایل %s: %s", path, e)
        return {}


def _save(path: str, data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


# ─── کاربران ──────────────────────────────────────────────────────────────

def register_user(user_id: int, username: Optional[str], first_name: Optional[str]):
    """هر بار کاربری با ربات تعامل داشته باشد، این تابع اطلاعاتش را ثبت/به‌روزرسانی می‌کند."""
    with _lock:
        users = _load(USERS_FILE)
        key = str(user_id)
        now = time.time()

        if key in users:
            users[key]["username"] = username
            users[key]["first_name"] = first_name
            users[key]["last_seen"] = now
        else:
            users[key] = {
                "username": username,
                "first_name": first_name,
                "first_seen": now,
                "last_seen": now,
            }

        _save(USERS_FILE, users)


def list_users() -> list:
    with _lock:
        users = _load(USERS_FILE)

    result = [{"id": int(uid), **info} for uid, info in users.items()]
    result.sort(key=lambda u: u.get("last_seen", 0), reverse=True)
    return result


def users_count() -> int:
    with _lock:
        return len(_load(USERS_FILE))


# ─── گروه‌ها ──────────────────────────────────────────────────────────────

def register_group(chat_id: int, title: Optional[str]):
    """
    وقتی گروهی برای اولین بار با ربات تعامل کند، به‌صورت پیش‌فرض با وضعیت
    غیرمجاز (allowed=False) ثبت می‌شود تا در پنل ادمین در لیست «در انتظار
    تایید» ظاهر شود و شما بتوانید آن را تایید کنید.
    """
    with _lock:
        groups = _load(GROUPS_FILE)
        key = str(chat_id)

        if key not in groups:
            groups[key] = {
                "title": title,
                "allowed": False,
                "added_at": time.time(),
            }
            _save(GROUPS_FILE, groups)
        elif title and groups[key].get("title") != title:
            groups[key]["title"] = title
            _save(GROUPS_FILE, groups)


def is_group_allowed(chat_id: int) -> bool:
    with _lock:
        groups = _load(GROUPS_FILE)
    return bool(groups.get(str(chat_id), {}).get("allowed", False))


def set_group_allowed(chat_id: int, allowed: bool):
    with _lock:
        groups = _load(GROUPS_FILE)
        key = str(chat_id)
        if key in groups:
            groups[key]["allowed"] = allowed
            _save(GROUPS_FILE, groups)


def list_groups() -> list:
    with _lock:
        groups = _load(GROUPS_FILE)

    result = [{"id": int(gid), **info} for gid, info in groups.items()]
    result.sort(key=lambda g: g.get("added_at", 0), reverse=True)
    return result
