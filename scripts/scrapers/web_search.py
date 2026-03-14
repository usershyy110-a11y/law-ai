"""Web search scraper — Tavily API + DDG fallback for family law news."""
import logging
import os
from datetime import datetime, timezone

log = logging.getLogger("web_search")

QUERIES = [
    "דיני משפחה ירושה פסק דין חדש",
    "גירושין מזונות משמורת ילדים פסיקה",
    "חוק ירושה צוואה עדכון חקיקה",
    "בית משפט לענייני משפחה פסק דין site:psakdin.co.il OR site:nevo.co.il OR site:courts.gov.il",
]

# Whitelist — only fetch/return URLs from trusted legal domains
ALLOWED_DOMAINS = {
    "psakdin.co.il",
    "nevo.co.il",
    "courts.gov.il",
    "din.co.il",
    "calcalist.co.il",
    "globes.co.il",
    "maariv.co.il",
    "ynet.co.il",
    "walla.co.il",
    "kan.org.il",
    "haaretz.co.il",
}


def _is_allowed_url(url: str) -> bool:
    """SSRF protection — only allowed domains."""
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)
    except Exception:
        return False


async def _tavily_search(query: str) -> list[dict]:
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        resp = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            days=2,  # last 48h
        )
        items = []
        for r in resp.get("results", []):
            url = r.get("url", "")
            if not _is_allowed_url(url):
                continue
            items.append({
                "title": r.get("title", ""),
                "url": url,
                "source": "חיפוש אינטרנט",
                "date": datetime.now(timezone.utc).isoformat(),
                "summary": r.get("content", "")[:300],
            })
        return items
    except Exception as e:
        log.warning(f"Tavily error for '{query}': {e}")
        return []


async def _ddg_search(query: str) -> list[dict]:
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        items = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=5, timelimit="d"):  # past day
                url = r.get("url", "")
                if not _is_allowed_url(url):
                    continue
                items.append({
                    "title": r.get("title", ""),
                    "url": url,
                    "source": "חיפוש אינטרנט",
                    "date": r.get("date", datetime.now(timezone.utc).isoformat()),
                    "summary": r.get("body", "")[:300],
                })
        return items
    except Exception as e:
        log.warning(f"DDG error for '{query}': {e}")
        return []


async def fetch() -> list[dict]:
    all_items = []
    seen_urls = set()

    for query in QUERIES:
        # Try Tavily first
        results = await _tavily_search(query)
        if not results:
            # DDG fallback
            results = await _ddg_search(query)

        for item in results:
            url = item.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_items.append(item)

    log.info(f"web_search: {len(all_items)} items")
    return all_items[:15]
