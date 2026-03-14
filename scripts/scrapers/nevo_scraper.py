"""Scraper for nevo.co.il — Israeli legislation and case law database."""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

log = logging.getLogger("nevo")

SEARCH_URLS = [
    "https://www.nevo.co.il/lawGov/SearchResults?q=%D7%93%D7%99%D7%A0%D7%99+%D7%9E%D7%A9%D7%A4%D7%97%D7%94",  # דיני משפחה
    "https://www.nevo.co.il/lawGov/SearchResults?q=%D7%99%D7%A8%D7%95%D7%A9%D7%94",  # ירושה
]
BASE_URL = "https://www.nevo.co.il"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LawDigestBot/1.0; +info@law-digest.il)"}
MAX_AGE_HOURS = 72  # Nevo updates less frequently

KEYWORDS = [
    "משפחה", "ירושה", "גירושין", "מזונות", "משמורת",
    "עיזבון", "צוואה", "אפוטרופסות", "הסכם ממון",
]


def _parse_date(text: str) -> Optional[datetime]:
    m = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", text)
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


def _is_relevant(text: str) -> bool:
    return any(kw in text for kw in KEYWORDS)


async def _fetch_url(session: aiohttp.ClientSession, url: str) -> list[dict]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status != 200:
                return []
            html = await resp.text(encoding="utf-8", errors="replace")
    except Exception as e:
        log.warning(f"nevo {url} error: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    items = []

    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        if not title or len(title) < 5:
            continue
        if not _is_relevant(title):
            continue

        href = a["href"]
        if not href.startswith("http"):
            href = BASE_URL + href

        parent_text = a.parent.get_text() if a.parent else ""
        dt = _parse_date(parent_text)
        if not _is_recent(dt):
            continue

        items.append({
            "title": title,
            "url": href,
            "source": "נבו",
            "date": dt.isoformat() if dt else None,
            "summary": "",
        })

    return items


async def fetch() -> list[dict]:
    all_items = []
    seen = set()

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for url in SEARCH_URLS:
            results = await _fetch_url(session, url)
            for item in results:
                if item["url"] not in seen:
                    seen.add(item["url"])
                    all_items.append(item)

    log.info(f"nevo: {len(all_items)} relevant items")
    return all_items[:10]
