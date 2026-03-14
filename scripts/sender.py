"""Telegram sender — sends the daily law digest to the dedicated bot."""
import logging
import os
from datetime import date

import telegram

log = logging.getLogger("sender")

MAX_MSG_LEN = 4000  # Telegram limit is 4096, leave buffer


def _no_updates_msg() -> str:
    today = date.today().strftime("%d/%m/%Y")
    return (
        f"📋 *עדכוני דיני משפחה וירושה — {today}*\n\n"
        "ℹ️ לא נמצאו עדכונים חדשים ב-48 השעות האחרונות."
    )


def _split_message(text: str) -> list[str]:
    if len(text) <= MAX_MSG_LEN:
        return [text]
    chunks = []
    while text:
        chunk = text[:MAX_MSG_LEN]
        # Try to split at newline
        if len(text) > MAX_MSG_LEN:
            split_at = chunk.rfind("\n")
            if split_at > MAX_MSG_LEN // 2:
                chunk = text[:split_at]
        chunks.append(chunk)
        text = text[len(chunk):]
    return chunks


async def send_digest(text: str | None) -> None:
    token = os.environ["LAW_AI_BOT_TOKEN"]
    chat_id = os.environ["LAW_AI_CHAT_ID"]

    bot = telegram.Bot(token=token)
    message = text if text else _no_updates_msg()

    for chunk in _split_message(message):
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        except telegram.error.BadRequest:
            # Fallback without Markdown if parsing fails
            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                disable_web_page_preview=True,
            )
        log.info(f"Sent chunk ({len(chunk)} chars) to {chat_id}")
