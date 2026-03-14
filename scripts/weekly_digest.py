"""
Law-AI Weekly Digest — runs every Thursday at 08:00 IST.
Selects 4 significant family law & inheritance court decisions
published in the last 18 months and sends a detailed summary to Telegram.
"""
import asyncio
import logging
import os
import sys
from datetime import date, datetime, timezone

import telegram
from openai import AzureOpenAI

LOG_FILE = __file__.replace("weekly_digest.py", "../law_ai.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ],
)
log = logging.getLogger("weekly")

ALLOWED_DOMAINS = {
    "psakdin.co.il", "nevo.co.il", "courts.gov.il",
    "din.co.il", "gov.il", "calcalist.co.il",
    "globes.co.il", "haaretz.co.il", "ynet.co.il",
}

SEARCH_QUERIES = [
    "פסק דין משפחה ירושה מזונות גירושין 2024 2025",
    "פסק דין תקדימי בית משפט לענייני משפחה 2024 2025",
    "פסק דין ירושה צוואה עיזבון 2024 2025",
    "פסיקה חשובה גירושין משמורת ילדים 2024 2025",
    "site:psakdin.co.il משפחה ירושה גירושין",
]

SYSTEM_PROMPT = """אתה משפטן ישראלי המתמחה בדיני משפחה וירושה.
קיבלת רשימת פסקי דין מהשנה וחצי האחרונות.
בחר את 4 פסקי הדין המשמעותיים ביותר מהרשימה וצור סקירה שבועית מפורטת.

פורמט הפלט:
⚖️ *סקירה שבועית — פסקי דין בדיני משפחה וירושה*
_[תאריך] | [טווח: 18 חודשים אחרונים]_

לכל פסק דין:
*[מספר]. [כותרת פסק הדין]*
📋 תיק: [מספר תיק — חובה אם מופיע]
📝 סיכום: [3-5 משפטים המסבירים את המחלוקת, ההחלטה וההשלכות המעשיות]
⚡ חשיבות: [משפט אחד — למה פסק הדין הזה חשוב לפרקטיקה]
🔗 [קישור]

---

הנחיות:
- בחר פסקי דין בעלי השלכות מעשיות — לא מקרים טכניים
- העדף תקדימים, פסיקות מחזקות מגמה, או החלטות מפתיעות
- ציין **תמיד** מספר תיק אם מופיע בטקסט
- אם לא ניתן לזהות 4 פסקי דין נפרדים — ציין פחות
- בסוף: _מקורות: [רשימת מקורות]_"""


def _is_allowed(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)
    except Exception:
        return False


def _search_tavily(queries: list[str]) -> list[dict]:
    from tavily import TavilyClient
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    items = []
    seen = set()

    for query in queries:
        try:
            # 18 months ≈ 548 days — Tavily max is 365, so use without days filter
            # and rely on query terms (2024/2025) for recency
            resp = client.search(
                query=query,
                search_depth="advanced",
                max_results=5,
            )
            for r in resp.get("results", []):
                url = r.get("url", "")
                if not _is_allowed(url) or url in seen:
                    continue
                seen.add(url)
                items.append({
                    "title": r.get("title", "")[:200],
                    "url": url,
                    "summary": r.get("content", "")[:500],
                    "source": "חיפוש",
                })
        except Exception as e:
            log.warning(f"Tavily error for '{query}': {e}")

    log.info(f"Collected {len(items)} candidate decisions")
    return items


def _build_prompt(items: list[dict]) -> str:
    today = date.today().strftime("%d/%m/%Y")
    lines = [f"תאריך היום: {today}\n", "פסקי דין שנמצאו:\n"]
    for i, item in enumerate(items[:20], 1):
        lines.append(
            f"[{i}] כותרת: {item['title']}\n"
            f"    מקור: {item['source']}\n"
            f"    תוכן: {item['summary']}\n"
            f"    קישור: {item['url']}\n"
        )
    return "\n".join(lines)


def _summarize(items: list[dict]) -> str:
    client = AzureOpenAI(
        api_key=os.environ.get("AZURE_OPENAI_API_KEY") or os.environ["AZURE_OPENAI_KEY"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    )
    deployment = (
        os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        or os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
        or "gpt-5-chat"
    )
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_prompt(items)},
        ],
        max_tokens=3000,
        temperature=0.4,
    )
    return response.choices[0].message.content


async def _send(text: str) -> None:
    token = os.environ["LAW_AI_BOT_TOKEN"]
    chat_id = os.environ["LAW_AI_CHAT_ID"]
    bot = telegram.Bot(token=token)
    MAX = 4000
    chunks = []
    while text:
        chunk = text[:MAX]
        if len(text) > MAX:
            split_at = chunk.rfind("\n")
            if split_at > MAX // 2:
                chunk = text[:split_at]
        chunks.append(chunk)
        text = text[len(chunk):]

    for chunk in chunks:
        try:
            await bot.send_message(
                chat_id=chat_id, text=chunk,
                parse_mode="Markdown", disable_web_page_preview=True,
            )
        except telegram.error.BadRequest:
            await bot.send_message(chat_id=chat_id, text=chunk, disable_web_page_preview=True)
        log.info(f"Sent chunk ({len(chunk)} chars)")


async def main() -> None:
    log.info("=== Law-AI Weekly Digest started ===")
    items = await asyncio.get_event_loop().run_in_executor(None, _search_tavily, SEARCH_QUERIES)

    if not items:
        log.warning("No items found — skipping weekly digest")
        return

    digest = await asyncio.get_event_loop().run_in_executor(None, _summarize, items)
    await _send(digest)
    log.info("=== Weekly Digest sent ===")


if __name__ == "__main__":
    asyncio.run(main())
