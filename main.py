"""IdeaScheduler Bot - Capture ideas and schedule them to Google Calendar."""

import os
import re
import logging
from datetime import datetime
from dotenv import load_dotenv
import dateparser
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import time as dt_time

import db
import google_calendar

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
google_creds = None


def parse_add_command(text: str) -> tuple[str, str] | None:
    """Parse /add command. Returns (idea, time_str) or None."""
    text = text.strip()
    if text.startswith('/add'):
        text = text[4:].strip()

    if not text:
        return None

    time_patterns = [
        r'(today|tomorrow|next\s+\w+|in\s+\d+\s+\w+|\d{1,2}(?::\d{2})?\s*(?:am|pm)?|\w+day)',
        r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
        r'(\w+\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?)',
    ]

    for pattern in time_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            time_start = match.start()
            idea = text[:time_start].strip()
            time_str = text[time_start:].strip()
            if idea and time_str:
                return (idea, time_str)

    words = text.split()
    if len(words) >= 2:
        for i in range(len(words) - 1, 0, -1):
            time_str = ' '.join(words[i:])
            parsed = dateparser.parse(time_str)
            if parsed:
                idea = ' '.join(words[:i])
                return (idea, time_str)

    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user_id = update.effective_user.id
    db.add_user(user_id)

    await update.message.reply_text(
        "Welcome to IdeaScheduler!\n\n"
        "Capture ideas and schedule them instantly.\n\n"
        "Usage: /add [idea] [time]\n"
        "Example: /add Film YouTube video tomorrow 2pm\n\n"
        "Type /help for more info."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "IdeaScheduler Bot\n\n"
        "Commands:\n"
        "/add [idea] [time] - Schedule an idea\n"
        "/pending - View pending ideas\n"
        "/stats - View completion stats\n\n"
        "Time formats:\n"
        "- tomorrow 2pm\n"
        "- next Monday 10am\n"
        "- in 3 days\n"
        "- Friday afternoon\n"
        "- December 25"
    )


async def add_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add command."""
    user_id = update.effective_user.id
    db.add_user(user_id)

    text = update.message.text
    parsed = parse_add_command(text)

    if not parsed:
        await update.message.reply_text(
            "Couldn't parse your idea.\n"
            "Try: /add Write blog post tomorrow 10am"
        )
        return

    idea, time_str = parsed
    parsed_time = dateparser.parse(time_str)

    if not parsed_time:
        await update.message.reply_text(
            f"Couldn't understand '{time_str}'.\n"
            "Try: 'tomorrow 2pm' or 'next Monday 10am'"
        )
        return

    if parsed_time < datetime.now():
        await update.message.reply_text(
            "That time is in the past. Please choose a future time."
        )
        return

    try:
        global google_creds
        if google_creds is None:
            google_creds = google_calendar.load_credentials()

        event_id = google_calendar.create_event(google_creds, idea, parsed_time)
        db.store_event(user_id, event_id, idea, parsed_time)

        formatted_time = parsed_time.strftime("%B %d at %I:%M %p")
        await update.message.reply_text(f"Added to calendar for {formatted_time}")

    except Exception as e:
        logger.error(f"Error creating event: {e}")
        await update.message.reply_text(
            "Failed to create calendar event. Check your Google credentials."
        )


async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending ideas."""
    user_id = update.effective_user.id
    events = db.get_pending_events(user_id)

    if not events:
        await update.message.reply_text("No pending ideas!")
        return

    lines = ["Your pending ideas:\n"]
    for e in events[:10]:
        time = datetime.fromisoformat(e['scheduled_time'])
        lines.append(f"- {e['idea']} ({time.strftime('%b %d %I:%M %p')})")

    await update.message.reply_text('\n'.join(lines))


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show completion stats."""
    user_id = update.effective_user.id
    s = db.get_completion_stats(user_id)

    await update.message.reply_text(
        f"This week: {s['completed']}/{s['total']} ideas completed ({s['rate']:.0f}%)"
    )


async def handle_completion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle completion callback from inline buttons."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith('complete_'):
        return

    event_db_id = int(data.replace('complete_', ''))
    event = db.get_event_by_id(event_db_id)

    if not event:
        await query.edit_message_text("Event not found.")
        return

    db.mark_event_complete(event_db_id)

    try:
        global google_creds
        if google_creds is None:
            google_creds = google_calendar.load_credentials()
        google_calendar.update_event_completion(google_creds, event['event_id'])
    except Exception as e:
        logger.error(f"Error updating calendar: {e}")

    user_id = event['user_id']
    s = db.get_completion_stats(user_id)

    await query.edit_message_text(
        f"Great! You've completed {s['completed']}/{s['total']} ideas this week."
    )


async def send_daily_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Send daily reminders for pending events."""
    events_by_user = db.get_all_pending_events_by_user()

    for user_id, events in events_by_user.items():
        for event in events[:5]:
            keyboard = [[
                InlineKeyboardButton("Done", callback_data=f"complete_{event['id']}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Reminder: {event['idea']}\nDid you do it?",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Failed to send reminder to {user_id}: {e}")


def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")

    db.init_db()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_idea))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(handle_completion, pattern=r'^complete_\d+$'))

    # Schedule daily reminders at 9am UTC using built-in job queue
    app.job_queue.run_daily(send_daily_reminders, time=dt_time(hour=9, minute=0))

    logger.info("Bot started")
    app.run_polling()


if __name__ == '__main__':
    main()
