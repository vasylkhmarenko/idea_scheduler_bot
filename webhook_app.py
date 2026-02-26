"""Flask webhook handler for IdeaScheduler Bot (PythonAnywhere deployment)."""

import os
import sys
import asyncio
import logging
import secrets
import threading
from pathlib import Path
from dotenv import load_dotenv

# Load .env BEFORE importing other modules that use env vars
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from flask import Flask, request, abort
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

import db
import oauth

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Required environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

# Validate required environment variables on startup
def _validate_env():
    """Ensure required environment variables are set."""
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append('TELEGRAM_BOT_TOKEN')
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)
    # Generate webhook secret if not set (warn but don't fail)
    global WEBHOOK_SECRET
    if not WEBHOOK_SECRET:
        WEBHOOK_SECRET = secrets.token_hex(32)
        logger.warning("WEBHOOK_SECRET not set. Generated temporary secret. Set it in .env for production.")

_validate_env()

# Flask app
app = Flask(__name__)

# Persistent event loop in a background thread (fixes "Event loop is closed" errors)
_loop = None
_loop_thread = None


def _start_background_loop(loop):
    """Run the event loop in a background thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def get_event_loop():
    """Get or create a persistent event loop running in a background thread."""
    global _loop, _loop_thread
    if _loop is None or not _loop.is_running():
        _loop = asyncio.new_event_loop()
        _loop_thread = threading.Thread(target=_start_background_loop, args=(_loop,), daemon=True)
        _loop_thread.start()
    return _loop


def run_async(coro):
    """Run an async coroutine in the persistent event loop."""
    loop = get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)  # 30 second timeout


# Telegram application (initialized lazily)
telegram_app = None
telegram_app_initialized = False


def get_telegram_app():
    """Get or create the Telegram Application instance."""
    global telegram_app
    if telegram_app is None:
        from main import (start, help_command, add_idea, pending, stats,
                          handle_completion, connect_google, disconnect_google,
                          handle_voice, handle_text_message)

        telegram_app = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .build()
        )

        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(CommandHandler("help", help_command))
        telegram_app.add_handler(CommandHandler("connect", connect_google))
        telegram_app.add_handler(CommandHandler("disconnect", disconnect_google))
        telegram_app.add_handler(CommandHandler("add", add_idea))
        telegram_app.add_handler(CommandHandler("pending", pending))
        telegram_app.add_handler(CommandHandler("stats", stats))
        telegram_app.add_handler(CallbackQueryHandler(handle_completion, pattern=r'^complete_\d+$'))
        telegram_app.add_handler(MessageHandler(filters.VOICE, handle_voice))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    return telegram_app


async def process_telegram_update(update_data):
    """Process a Telegram update with proper initialization."""
    global telegram_app_initialized
    telegram_app = get_telegram_app()

    # Initialize the application if not already done
    if not telegram_app_initialized:
        await telegram_app.initialize()
        telegram_app_initialized = True

    update = Update.de_json(update_data, telegram_app.bot)
    await telegram_app.process_update(update)


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates."""
    # Validate webhook secret token (if configured)
    if WEBHOOK_SECRET:
        token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if not token or not secrets.compare_digest(token, WEBHOOK_SECRET):
            logger.warning("Webhook request with invalid or missing secret token")
            abort(403)

    try:
        update_data = request.get_json()
        run_async(process_telegram_update(update_data))
        return 'OK', 200
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return 'OK', 200  # Return 200 to avoid Telegram retries


@app.route('/oauth/callback', methods=['GET'])
def oauth_callback():
    """Handle Google OAuth callback."""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error:
        logger.error(f"OAuth error: {error}")
        return render_callback_result(False, "Authorization failed. Please try again.")

    if not code or not state:
        return render_callback_result(False, "Missing authorization code or state")

    user_id, success, message = oauth.exchange_code_for_tokens(code, state)

    if success:
        try:
            run_async(send_connection_success_message(user_id))
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    return render_callback_result(success, message)


async def send_connection_success_message(user_id: int):
    """Send a Telegram message confirming successful connection."""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(
        chat_id=user_id,
        text=(
            "Google Calendar connected successfully!\n\n"
            "You can now use /add to schedule ideas to your calendar.\n"
            "Example: /add Review project tomorrow 3pm"
        )
    )


def render_callback_result(success: bool, message: str) -> str:
    """Render HTML page for OAuth callback result."""
    status_color = "#4CAF50" if success else "#f44336"
    icon = "&#10004;" if success else "&#10008;"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>IdeaScheduler - Calendar Connection</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: #f5f5f5;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 400px;
            }}
            .icon {{
                font-size: 48px;
                color: {status_color};
                margin-bottom: 20px;
            }}
            .message {{
                color: #333;
                font-size: 18px;
                margin-bottom: 20px;
            }}
            .instruction {{
                color: #666;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">{icon}</div>
            <div class="message">{message}</div>
            <div class="instruction">
                {"You can close this window and return to Telegram." if success
                 else "Please try again from the Telegram bot."}
            </div>
        </div>
    </body>
    </html>
    """


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return 'OK', 200


@app.route('/version', methods=['GET'])
def version():
    """Version check to verify deployment."""
    return 'v3-debug', 200


@app.route('/debug/user/<int:user_id>', methods=['GET'])
def debug_user(user_id: int):
    """Debug endpoint to check user state in database."""
    import json
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            user_data = dict(row)
            # Mask sensitive tokens
            if user_data.get('google_access_token'):
                user_data['google_access_token'] = user_data['google_access_token'][:20] + '...'
            if user_data.get('google_refresh_token'):
                user_data['google_refresh_token'] = user_data['google_refresh_token'][:20] + '...'
            if user_data.get('oauth_state'):
                user_data['oauth_state'] = user_data['oauth_state'][:50] + '...'
        else:
            user_data = None
    return json.dumps({
        'database_path': db.DATABASE_PATH,
        'user_exists': user_data is not None,
        'user_data': user_data
    }, indent=2, default=str), 200, {'Content-Type': 'application/json'}


@app.route('/debug/reset/<int:user_id>', methods=['GET'])
def reset_user(user_id: int):
    """Delete user from database to start fresh."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM events WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
    return f"User {user_id} deleted. Now try /start in Telegram.", 200


@app.route('/', methods=['GET'])
def index():
    """Root endpoint."""
    return 'IdeaScheduler Bot is running!', 200


# Initialize database on startup
db.init_db()


if __name__ == '__main__':
    # For local testing only
    app.run(debug=True, port=5000)
