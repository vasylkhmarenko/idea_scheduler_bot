"""Daily reminder script for PythonAnywhere scheduled task."""

import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

import db

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


async def send_reminders():
    """Send reminders for all pending events."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    events_by_user = db.get_all_pending_events_by_user()

    total_sent = 0
    for user_id, events in events_by_user.items():
        for event in events[:5]:  # Max 5 reminders per user
            keyboard = [[
                InlineKeyboardButton("Done", callback_data=f"complete_{event['id']}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=f"Reminder: {event['idea']}\nDid you do it?",
                    reply_markup=reply_markup
                )
                total_sent += 1
                logger.info(f"Sent reminder to {user_id}: {event['idea']}")
            except Exception as e:
                logger.error(f"Failed to send reminder to {user_id}: {e}")

    logger.info(f"Daily reminders complete. Sent {total_sent} messages.")


def main():
    """Run the reminder script."""
    db.init_db()
    asyncio.run(send_reminders())


if __name__ == '__main__':
    main()
