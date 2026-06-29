import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from config import ASSETS, CACHE_SECONDS, REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

_cache = None
_last_update = 0


def fetch_prices():
    global _cache, _last_update

    # اگر کش معتبر است، همان را برگردان
    if _cache and time.time() - _last_update < CACHE_SECONDS:
        return _cache

    url = f"https://www.tgju.org/?t={int(time.time())}"

    headers = {
        "User-Agent": USER_AGENT,
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except requests.RequestException as e:
        logger.error("خطا در دریافت صفحه: %s", e)

        if _cache:
            logger.info("استفاده از کش")

            return _cache

        return {
            key: "❌ خطای اتصال"
            for key in ASSETS
        }

    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.find_all("tr")

    result = {}

    for key, asset in ASSETS.items():

        found = False

        for row in rows:

            text = row.get_text()

            if any(keyword in text for keyword in asset.keywords):

                for td in row.find_all("td"):

                    cell = td.get_text(strip=True)

                    match = re.search(r"\d{1,3}(?:,\d{3})+", cell)

                    if not match:
                        continue

                    value = int(match.group().replace(",", ""))

                    if value > asset.minimum:

                        result[key] = match.group()

                        found = True

                        break

            if found:
                break

        if not found:
            result[key] = "⚠️ یافت نشد"

    _cache = result
    _last_update = time.time()

    return result