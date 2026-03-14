"""Rabbinical Courts scraper — fetches verdicts from gov.il via Tavily.
Direct access is blocked by Cloudflare; Tavily bypasses this.
Source: https://www.gov.il/he/Departments/DynamicCollectors/verdict_the_rabbinical_courts
"""
import logging
import os
from datetime import datetime, timezone

log = logging.getLogger("rabbinical")

SOURCE_URL = "https://www.gov.il/he/Departments/DynamicCollectors/verdict_the_rabbinical_courts"

QUERIES = [
    "site:gov.il בתי הדין הרבניים פסק דין גירושין ירושה",
    "site:gov.il verdict_the_rabbinical_courts",
]

ALLOWED_DOMAIN = "gov.il"


def _is_allowed_url(url: str) -> bool:
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
                resp = client.search(
                    query=query,
                    search_depth="basic",
                    max_results=5,
                    days=3,
                )
                for r in resp.get("results", []):
                    url = r.get("url", "")
                    if not _is_allowed_url(url):
                        continue
                    if url in seen:
                        continue
                    seen.add(url)
                    items.append({
                        "title": r.get("title", ""),
                        "url": url,
                        "source": "בתי הדין הרבניים",
                        "date": datetime.now(timezone.utc).isoformat(),
                        "summary": r.get("content", "")[:300],
                    })
            except Exception as e:
                log.warning(f"rabbinical Tavily query '{query}' error: {e}")

    except Exception as e:
        log.warning(f"rabbinical fetch error: {e}")

    log.info(f"rabbinical: {len(items)} items")
    return items[:10]
