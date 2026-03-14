"""Scraper for din.co.il — Israeli legal news site."""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

log = logging.getLogger("din")

BASE_URL = "https://www.din.co.il/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LawDigestBot/1.0; +info@law-digest.il)"}
MAX_AGE_HOURS = 48

KEYWORDS = [
    "משפחה", "ירושה", "גירושין", "מזונות", "משמורת",
    "עיזבון", "צוואה", "אפוטרופסות", "הסכם ממון",
    "פירוק שיתוף", "כתובה", "נישואין", "אימוץ",
]


def _parse_date(text: str) -> Optional[datetime]:
    # Format: DD/M/YYYY or D/M/YYYY
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if not m:
        return None
    try:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), tzinfo=timezone.utc)
    except ValueError:
        return None


def _is_recent(dt: Optional[datetime]) -> bool:
    if not dt:
        return True
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
        log.warning(f"din fetch error: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")

    seen_urls = set()
    for a in soup.find_all("a", href=lambda x: x and "/articles/" in x):
        title = a.get_text(strip=True)
        if not title or not _is_relevant(title):
            continue

        url = a["href"]
        if not url.startswith("http"):
            url = "https://www.din.co.il" + url

        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Try to find date in parent element
        parent_text = a.parent.get_text() if a.parent else ""
        dt = _parse_date(parent_text)
        if not _is_recent(dt):
            continue

        items.append({
            "title": title,
            "url": url,
            "source": "דין",
            "date": dt.isoformat() if dt else None,
            "summary": "",
        })

    log.info(f"din: {len(items)} relevant items")
    return items[:10]
