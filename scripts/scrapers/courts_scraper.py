"""Courts scraper — searches courts.gov.il content via Tavily (direct DNS blocked)."""
import logging
import os
from datetime import datetime, timezone

log = logging.getLogger("courts")

QUERIES = [
    "site:courts.gov.il דיני משפחה ירושה פסק דין",
    "site:courts.gov.il גירושין מזונות משמורת",
]

ALLOWED_DOMAIN = "courts.gov.il"


def _is_courts_url(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        return ALLOWED_DOMAIN in host
    except Exception:
        return False


async def fetch() -> list[dict]:
    items = []
    seen = set()

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

        for query in QUERIES:
            try:
                resp = client.search(query=query, search_depth="basic", max_results=5, days=3)
                for r in resp.get("results", []):
                    url = r.get("url", "")
                    if not _is_courts_url(url):
                        continue
                    if url in seen:
                        continue
                    seen.add(url)
                    items.append({
                        "title": r.get("title", ""),
                        "url": url,
                        "source": "דוברות בתי המשפט",
                        "date": datetime.now(timezone.utc).isoformat(),
                        "summary": r.get("content", "")[:300],
                    })
            except Exception as e:
                log.warning(f"courts Tavily query error: {e}")

    except Exception as e:
        log.warning(f"courts fetch error: {e}")

    log.info(f"courts: {len(items)} items")
    return items[:10]
