"""Scraper for psakdin.co.il — Israeli court decisions database."""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

log = logging.getLogger("psakdin")

BASE_URL = "https://www.psakdin.co.il/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LawDigestBot/1.0; +info@law-digest.il)"}
MAX_AGE_HOURS = 24

KEYWORDS = [
    "משפחה", "ירושה", "גירושין", "מזונות", "משמורת",
    "עיזבון", "צוואה", "אפוטרופסות", "הסכם ממון",
    "פירוק שיתוף", "כתובה", "נישואין", "אימוץ",
]


def _parse_date(text: str) -> Optional[datetime]:
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if not m:
        return None
    try:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), tzinfo=timezone.utc)
    except ValueError:
        return None


def _is_recent(dt: Optional[datetime]) -> bool:
    if not dt:
        return False  # exclude if date unknown
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    return dt >= cutoff


def _is_relevant(title: str) -> bool:
    return any(kw in title for kw in KEYWORDS)


async def fetch() -> list[dict]:
    items = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(BASE_URL, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                html = await resp.text(encoding="utf-8", errors="replace")
    except Exception as e:
        log.warning(f"psakdin fetch error: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")

    for li in soup.find_all("li"):
        link = li.find("a", href=lambda x: x and "/Document/" in x)
        if not link:
            continue

        title = link.get_text(strip=True)
        if not _is_relevant(title):
            continue

        url = link["href"]
        if not url.startswith("http"):
            url = "https://www.psakdin.co.il" + url

        dt = _parse_date(li.get_text())
        if not _is_recent(dt):
            continue

        items.append({
            "title": title,
            "url": url,
            "source": "פסקדין",
            "date": dt.isoformat() if dt else None,
            "summary": "",
        })

    log.info(f"psakdin: {len(items)} relevant items")
    return items[:10]
