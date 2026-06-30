from dataclasses import dataclass

CACHE_SECONDS = 30

REQUEST_TIMEOUT = 50

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0 Safari/537.36"
)


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

    "gold": Asset(
        key="gold",
        label="🥇 طلای ۱۸ عیار",
        command="gold",
        description="قیمت طلای ۱۸ عیار",
        button="🥇 طلا",
        keywords=["طلای ۱۸ عیار", "طلا"],
        minimum=5000000
    ),

}