"""
Law-AI Daily Digest — main orchestrator.
Runs daily at 08:00 IST via cron.
Collects family law & inheritance updates from multiple sources,
summarizes with GPT-5, and sends to Telegram.
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers import psakdin_scraper, din_scraper, courts_scraper, nevo_scraper, web_search, rabbinical_scraper
from summarizer import summarize
from sender import send_digest

LOG_FILE = Path(__file__).parent.parent / "law_ai.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ],
)
log = logging.getLogger("digest")

CONFIG_FILE = Path(__file__).parent.parent / "config" / "sources.json"
with CONFIG_FILE.open() as f:
    CONFIG = json.load(f)

KEYWORDS = CONFIG["keywords"]


def _is_relevant(item: dict) -> bool:
    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    return any(kw in text for kw in KEYWORDS)


async def main() -> None:
    log.info("=== Law-AI Digest started ===")

    tasks = [
        psakdin_scraper.fetch(),
        din_scraper.fetch(),
        courts_scraper.fetch(),
        nevo_scraper.fetch(),
        rabbinical_scraper.fetch(),
        web_search.fetch(),
    ]
    source_names = ["psakdin", "din", "courts", "nevo", "rabbinical", "web_search"]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    raw_items = []
    for name, result in zip(source_names, results):
        if isinstance(result, Exception):
            log.warning(f"{name} failed: {result}")
        elif isinstance(result, list):
            log.info(f"{name}: {len(result)} items")
            raw_items.extend(result)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique = []
    for item in raw_items:
        url = item.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(item)

    # Filter relevant
    relevant = [i for i in unique if _is_relevant(i)]
    log.info(f"Total: {len(unique)} unique, {len(relevant)} relevant after filtering")

    if not relevant:
        log.info("No relevant items found — sending no-updates message")
        await send_digest(None)
        return

    digest_text = await summarize(relevant)
    await send_digest(digest_text)
    log.info("=== Digest sent successfully ===")


if __name__ == "__main__":
    asyncio.run(main())
