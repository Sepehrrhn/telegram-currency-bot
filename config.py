import os
from dataclasses import dataclass

# ─── تنظیمات کش/اسکرپ ────────────────────────────────────────────────────────
# به جای اسکرپ در لحظه‌ی هر درخواست، یک ترد پس‌زمینه هر SCRAPE_INTERVAL ثانیه
# یک‌بار قیمت‌ها را می‌گیرد و در CACHE_FILE ذخیره می‌کند. هندلرها فقط همین فایل
# را می‌خوانند و هرگز مستقیماً به tgju.org درخواست نمی‌زنند.
SCRAPE_INTERVAL = 30  # ثانیه

REQUEST_TIMEOUT = 50

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0 Safari/537.36"
)

# پوشه‌ی داده روی سرور؛ فایل‌های کش قیمت و اطلاعات کاربران/گروه‌ها اینجا نگه‌داری می‌شوند.
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

CACHE_FILE = os.path.join(DATA_DIR, "prices_cache.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")  # فقط fallback محلی، پایین را ببین
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")  # فقط fallback محلی، پایین را ببین

# ─── ذخیره‌سازی پایدار (Upstash Redis) ───────────────────────────────────────
# روی پلن رایگان Render دیسک موقتی است و با هر ری‌استارت پاک می‌شود. برای این‌که
# لیست کاربران/گروه‌ها و وضعیت تاییدشان از بین نرود، این مقادیر را از پنل
# Upstash (بخش REST API دیتابیس Redis رایگانت) در .env قرار بده:
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")


# ─── تنظیمات پنل مدیریت ──────────────────────────────────────────────────────
# آیدی عددی خودت را (نه یوزرنیم!) داخل .env در متغیر ADMIN_IDS قرار بده.
# می‌توانی چند آیدی را با ویرگول جدا کنی، مثلا: ADMIN_IDS=111111111,222222222
# آیدی عددی را می‌توانی از بات‌هایی مثل @userinfobot بگیری.
def _parse_admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", "")
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


ADMIN_IDS = _parse_admin_ids()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@dataclass(frozen=True)
class Asset:
    key: str
    label: str
    command: str
    description: str
    button: str
    keywords: list[str]
    minimum: int


ASSETS = {

    "usd": Asset(
        key="usd",
        label="💵 دلار آمریکا",
        command="usd",
        description="قیمت دلار آمریکا",
        button="💵 دلار",
        keywords=["دلار آمریکا", "دلار"],
        minimum=500000
    ),

    "eur": Asset(
        key="eur",
        label="💶 یورو",
        command="eur",
        description="قیمت یورو",
        button="💶 یورو",
        keywords=["یورو"],
        minimum=500000
    ),

    "gbp": Asset(
        key="gbp",
        label="💷 پوند انگلیس",
        command="gbp",
        description="قیمت پوند انگلیس",
        button="💷 پوند",
        keywords=["پوند انگلیس", "پوند"],
        minimum=500000
    ),

    "gold": Asset(
        key="gold",
        label="🥇 طلای ۱۸ عیار",
        command="gold",
        description="قیمت طلای ۱۸ عیار",
        button="🥇 طلا",
        keywords=["طلای ۱۸ عیار", "طلا"],
        minimum=5000000
    ),

    "btc": Asset(
        key="btc",
        label="₿ بیت کوین",
        command="btc",
        description="قیمت بیت کوین",
        button="₿ بیت‌کوین",
        keywords=["بیت کوین", "بیت‌کوین"],
        minimum=1000000000
    ),

    "eth": Asset(
        key="eth",
        label="Ξ اتریوم",
        command="eth",
        description="قیمت اتریوم",
        button="Ξ اتریوم",
        keywords=["اتریوم"],
        minimum=100000000
    ),

    "usdt": Asset(
        key="usdt",
        label="₮ تتر",
        command="usdt",
        description="قیمت تتر",
        button="₮ تتر",
        keywords=["تتر"],
        minimum=100000
    ),

}
