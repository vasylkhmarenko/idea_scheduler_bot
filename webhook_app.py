"""Flask webhook handler for IdeaScheduler Bot (PythonAnywhere deployment)."""

import os
import asyncio
import logging
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

import db
import google_calendar

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Flask app
app = Flask(__name__)

# Telegram application (initialized lazily)
telegram_app = None
google_creds = None


def get_telegram_app():
    """Get or create the Telegram Application instance."""
    global telegram_app
    if telegram_app is None:
        from main import start, help_command, add_idea, pending, stats, handle_completion

        telegram_app = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .build()
        )

        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(CommandHandler("help", help_command))
        telegram_app.add_handler(CommandHandler("add", add_idea))
        telegram_app.add_handler(CommandHandler("pending", pending))
        telegram_app.add_handler(CommandHandler("stats", stats))
        telegram_app.add_handler(CallbackQueryHandler(handle_completion, pattern=r'^complete_\d+$'))

    return telegram_app


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates."""
    try:
        telegram_app = get_telegram_app()
        update = Update.de_json(request.get_json(), telegram_app.bot)

        # Process update asynchronously
        asyncio.run(telegram_app.process_update(update))

        return 'OK', 200
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return 'OK', 200  # Return 200 to avoid Telegram retries


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return 'OK', 200


@app.route('/', methods=['GET'])
def index():
    """Root endpoint."""
    return 'IdeaScheduler Bot is running!', 200


# Initialize database on startup
db.init_db()


if __name__ == '__main__':
    # For local testing only
    app.run(debug=True, port=5000)
