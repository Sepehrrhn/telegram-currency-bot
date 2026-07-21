import os
from dataclasses import dataclass

from dotenv import load_dotenv

# این فایل ممکن است قبل از فراخوانی load_dotenv() در bot.py ایمپورت شود،
# پس برای اطمینان از خواندن صحیح متغیرهای محیطی (مثل ADMIN_IDS) این‌جا هم
# load_dotenv را صدا می‌زنیم. صدا زدن چندباره‌ی آن مشکلی ایجاد نمی‌کند.
load_dotenv()

# ─── تنظیمات اسکرپینگ ───────────────────────────────────────────────────────
# به‌جای اسکرپ در لحظه‌ی هر درخواست کاربر، هر SCRAPE_INTERVAL_SECONDS ثانیه
# یک‌بار در پس‌زمینه اسکرپ انجام و نتیجه در فایل data/prices.json ذخیره می‌شود.
# هندلرهای ربات فقط همین فایل را می‌خوانند.
SCRAPE_INTERVAL_SECONDS = 30

REQUEST_TIMEOUT = 50

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0 Safari/537.36"
)

# پوشه‌ی داده‌ها روی سرور (قیمت‌ها، کاربران، گروه‌های مجاز)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _parse_admin_ids(raw: str):
    """
    ADMIN_IDS در فایل .env می‌تواند یک یا چند آیدی عددی، جدا شده با کاما باشد:
    ADMIN_IDS=123456789,987654321
    """
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


# آیدی عددی تلگرام شما. برای گرفتن آیدی عددی‌تان کافیست به ربات دستور
# /myid را بزنید. سپس آن عدد را در فایل .env داخل ADMIN_IDS قرار دهید.
ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))


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
        label="₿ بیت‌کوین",
        command="btc",
        description="قیمت بیت‌کوین",
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
        label="🔗 تتر",
        command="usdt",
        description="قیمت تتر",
        button="🔗 تتر",
        keywords=["تتر"],
        minimum=500000
    ),

}
