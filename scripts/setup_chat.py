"""
One-time setup: get the Telegram chat_id for the law-ai bot.
Steps:
  1. Find the bot on Telegram by its username
  2. Send it any message (e.g. /start)
  3. Run this script to retrieve the chat_id
  4. Save LAW_AI_CHAT_ID to Infisical
"""
import asyncio
import os
import sys

import telegram


async def main() -> None:
    token = os.environ.get("LAW_AI_BOT_TOKEN")
    if not token:
        print("ERROR: LAW_AI_BOT_TOKEN env var not set")
        sys.exit(1)

    bot = telegram.Bot(token=token)

    print("Fetching bot info...")
    me = await bot.get_me()
    print(f"Bot: @{me.username} ({me.first_name})")

    print("\nFetching updates (last messages sent to the bot)...")
    updates = await bot.get_updates()

    if not updates:
        print("\n⚠️  No messages found.")
        print(f"Please open Telegram, search for @{me.username}, and send /start")
        print("Then run this script again.")
        return

    print("\n✅ Found chats:")
    for u in updates:
        if u.message:
            chat = u.message.chat
            user = u.message.from_user
            print(f"  chat_id: {chat.id}  |  type: {chat.type}  |  from: @{user.username} ({user.first_name})")

    chat_id = updates[-1].message.chat.id
    print(f"\n→ Use this chat_id: {chat_id}")
    print(f'\nSave to Infisical:')
    print(f'  infisical secrets set LAW_AI_CHAT_ID="{chat_id}" --env=prod')


if __name__ == "__main__":
    asyncio.run(main())
