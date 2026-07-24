"""
ذخیره‌سازی کاربران و گروه‌ها.

روی پلن رایگان Render دیسک سرویس موقتی (ephemeral) است؛ یعنی با هر
ری‌استارت/دیپلوی، فایل‌های ذخیره‌شده روی دیسک پاک می‌شوند. برای همین این ماژول
داده‌ها را در یک دیتابیس Upstash Redis (رایگان و ابری) نگه می‌دارد که با
ری‌استارت شدن سرویس از بین نمی‌رود.

راه‌اندازی:
1) یک اکانت رایگان در https://upstash.com بساز و یک دیتابیس Redis بساز.
2) از تب "REST API" همان دیتابیس، مقادیر UPSTASH_REDIS_REST_URL و
   UPSTASH_REDIS_REST_TOKEN را کپی کن و در فایل .env قرار بده.

اگر این دو متغیر تنظیم نشده باشند (مثلاً موقع تست روی سیستم خودت)، این ماژول
به‌صورت خودکار روی یک فایل JSON محلی fallback می‌کند تا برنامه crash نکند؛
ولی برای دیپلوی روی Render حتماً باید Upstash تنظیم شود، وگرنه لیست
کاربران/گروه‌ها با هر ری‌استارت پاک می‌شود.
"""

import json
import logging
import threading
import time

import requests

from config import (
    GROUPS_FILE,
    UPSTASH_REDIS_REST_TOKEN,
    UPSTASH_REDIS_REST_URL,
    USERS_FILE,
)

logger = logging.getLogger(__name__)

_lock = threading.Lock()

USERS_KEY = "currency_bot:users"
GROUPS_KEY = "currency_bot:groups"


def _redis_configured() -> bool:
    return bool(UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN)


def _redis_command(*parts):
    """
    یک دستور Redis را از طریق REST API آپستاش اجرا می‌کند.
    مثال: _redis_command("HSET", "groups", "123", '{"approved": true}')
    """
    response = requests.post(
        UPSTASH_REDIS_REST_URL,
        headers={"Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}"},
        json=list(parts),
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("result")


def _redis_hset(hash_key: str, field: str, value: dict) -> None:
    _redis_command("HSET", hash_key, field, json.dumps(value, ensure_ascii=False))


def _redis_hget(hash_key: str, field: str) -> dict | None:
    raw = _redis_command("HGET", hash_key, field)
    if raw is None:
        return None
    return json.loads(raw)


def _redis_hgetall(hash_key: str) -> dict:
    """Upstash نتیجه‌ی HGETALL را به‌صورت لیست تخت [field1, val1, field2, val2, ...] برمی‌گرداند."""
    flat = _redis_command("HGETALL", hash_key) or []
    result = {}
    for i in range(0, len(flat), 2):
        field = flat[i]
        value = flat[i + 1]
        try:
            result[field] = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            continue
    return result


# ─── fallback محلی (فقط برای زمانی که Upstash تنظیم نشده) ────────────────────
def _load_local(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_local(path: str, data: dict) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    import os
    os.replace(tmp_path, path)


if not _redis_configured():
    logger.warning(
        "UPSTASH_REDIS_REST_URL/TOKEN تنظیم نشده‌اند؛ لیست کاربران و گروه‌ها "
        "روی فایل محلی ذخیره می‌شود و با هر ری‌استارت روی Render پاک خواهد شد."
    )


# ─── کاربران (چت‌های خصوصی) ───────────────────────────────────────────────────
def track_user(user_id: int, username: str | None, full_name: str | None) -> None:
    entry = {
        "id": user_id,
        "username": username,
        "full_name": full_name,
        "last_seen": time.time(),
    }
    with _lock:
        if _redis_configured():
            _redis_hset(USERS_KEY, str(user_id), entry)
        else:
            users = _load_local(USERS_FILE)
            users[str(user_id)] = entry
            _save_local(USERS_FILE, users)


def get_all_users() -> list[dict]:
    with _lock:
        if _redis_configured():
            return list(_redis_hgetall(USERS_KEY).values())
        return list(_load_local(USERS_FILE).values())


# ─── گروه‌ها ──────────────────────────────────────────────────────────────────
def track_group(chat_id: int, title: str | None) -> dict:
    """
    گروه را (در صورت جدید بودن) با وضعیت 'در انتظار تایید' ثبت می‌کند و
    اطلاعات فعلی آن را برمی‌گرداند.
    """
    key = str(chat_id)
    with _lock:
        if _redis_configured():
            existing = _redis_hget(GROUPS_KEY, key)
            if existing is None:
                existing = {
                    "id": chat_id,
                    "title": title,
                    "approved": False,
                    "added_at": time.time(),
                }
            else:
                existing["title"] = title or existing.get("title")
            _redis_hset(GROUPS_KEY, key, existing)
            return existing

        groups = _load_local(GROUPS_FILE)
        if key not in groups:
            groups[key] = {
                "id": chat_id,
                "title": title,
                "approved": False,
                "added_at": time.time(),
            }
        else:
            groups[key]["title"] = title or groups[key].get("title")
        _save_local(GROUPS_FILE, groups)
        return groups[key]


def is_group_approved(chat_id: int) -> bool:
    key = str(chat_id)
    with _lock:
        if _redis_configured():
            entry = _redis_hget(GROUPS_KEY, key)
        else:
            entry = _load_local(GROUPS_FILE).get(key)
        return bool(entry and entry.get("approved"))


def approve_group(chat_id: int, title: str | None = None) -> bool:
    """
    گروه را تایید می‌کند. اگر قبلاً ثبت نشده باشد (مثلاً هنوز کسی توی گروه
    پیامی نفرستاده)، همین‌جا با وضعیت تایید‌شده ساخته می‌شود.
    """
    key = str(chat_id)
    with _lock:
        if _redis_configured():
            entry = _redis_hget(GROUPS_KEY, key)
            if entry is None:
                entry = {
                    "id": chat_id,
                    "title": title,
                    "approved": True,
                    "added_at": time.time(),
                }
            else:
                entry["approved"] = True
            _redis_hset(GROUPS_KEY, key, entry)
            return True

        groups = _load_local(GROUPS_FILE)
        if key not in groups:
            groups[key] = {
                "id": chat_id,
                "title": title,
                "approved": True,
                "added_at": time.time(),
            }
        else:
            groups[key]["approved"] = True
        _save_local(GROUPS_FILE, groups)
        return True


def revoke_group(chat_id: int) -> bool:
    key = str(chat_id)
    with _lock:
        if _redis_configured():
            entry = _redis_hget(GROUPS_KEY, key)
            if entry is None:
                return False
            entry["approved"] = False
            _redis_hset(GROUPS_KEY, key, entry)
            return True

        groups = _load_local(GROUPS_FILE)
        if key not in groups:
            return False
        groups[key]["approved"] = False
        _save_local(GROUPS_FILE, groups)
        return True


def get_all_groups() -> list[dict]:
    with _lock:
        if _redis_configured():
            return list(_redis_hgetall(GROUPS_KEY).values())
        return list(_load_local(GROUPS_FILE).values())


def get_pending_groups() -> list[dict]:
    return [g for g in get_all_groups() if not g.get("approved")]


def get_approved_groups() -> list[dict]:
    return [g for g in get_all_groups() if g.get("approved")]
