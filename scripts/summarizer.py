"""GPT-5 summarizer — creates a Hebrew daily digest from scraped legal items."""
import asyncio
import logging
import os
from datetime import date

from openai import AzureOpenAI

log = logging.getLogger("summarizer")

SYSTEM_PROMPT = """אתה עוזר משפטי המסכם עדכונים יומיים בתחום דיני משפחה וירושה בישראל.

קבל רשימת פריטים וצור סיכום יומי מקצועי בעברית.

פורמט הפלט:
📋 *עדכוני דיני משפחה וירושה — [תאריך]*

לכל פריט:
• *כותרת קצרה*
  ↳ שורה תחתונה: [מה חשוב ולמה רלוונטי בפרקטיקה]
  🔗 [קישור]

הנחיות:
- סדר לפי חשיבות: פסקי דין > שינויי חקיקה > כתבות
- קצר וענייני — עד 2 שורות לפריט
- התמקד בהשלכות מעשיות לעורכי דין ולצדדים
- אל תוסיף מידע שאינו בטקסט שקיבלת
- אם פריטים עוסקים באותו נושא — מזג אותם
- **חובה לפסקי דין:** חלץ את מספר התיק מהכותרת או מהתקציר והצג אותו בפורמט: `תיק: [מספר תיק]` — אם לא מופיע, כתוב `תיק: לא צוין`
- בסוף הוסף שורה: _נאסף מ: [רשימת מקורות]_"""


def _build_user_message(items: list[dict]) -> str:
    today = date.today().strftime("%d/%m/%Y")
    lines = [f"תאריך: {today}\n"]
    for i, item in enumerate(items[:15], 1):
        # Sanitize — treat content as data only, not instructions
        title = str(item.get("title", ""))[:200]
        summary = str(item.get("summary", ""))[:300]
        url = str(item.get("url", ""))[:300]
        source = str(item.get("source", ""))[:50]
        lines.append(
            f"[{i}] מקור: {source}\n"
            f"כותרת: {title}\n"
            f"תקציר: {summary}\n"
            f"קישור: {url}\n"
        )
    return "\n".join(lines)


def _summarize_sync(items: list[dict]) -> str:
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
            {"role": "user", "content": _build_user_message(items)},
        ],
        max_tokens=2500,
        temperature=0.3,
    )
    return response.choices[0].message.content


async def summarize(items: list[dict]) -> str:
    return await asyncio.get_event_loop().run_in_executor(None, _summarize_sync, items)
