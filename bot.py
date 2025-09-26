import os
import csv
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, Dispatcher
from github import Github

# -------------------------------------------------
# Logging setup
# -------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# Environment variables
# -------------------------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "blake450/cashnet-bot")
CSV_FILE = "affiliates.csv"

if not TELEGRAM_TOKEN or not GITHUB_TOKEN:
    raise RuntimeError("❌ Missing TELEGRAM_BOT_TOKEN or GITHUB_TOKEN in environment variables")

# -------------------------------------------------
# Flask app for webhook
# -------------------------------------------------
app = Flask(__name__)

updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dispatcher: Dispatcher = updater.dispatcher

# -------------------------------------------------
# GitHub Helper
# -------------------------------------------------
def update_github_csv(chat_id: int, chat_name: str, frequency: str, affiliate_id: str):
    """Write/update affiliates.csv and push to GitHub."""
    logger.info("📂 Preparing to update affiliates.csv...")

    # Download or create CSV
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["chat_id", "chat_name", "frequency", "affiliate_id"])
        writer.writerow([chat_id, chat_name, frequency, affiliate_id])

    # Push to GitHub
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)

    try:
        contents = repo.get_contents(CSV_FILE)
        with open(CSV_FILE, "r") as f:
            repo.update_file(
                contents.path,
                f"Update {CSV_FILE}",
                f.read(),
                contents.sha
            )
        logger.info(f"✅ {CSV_FILE} updated and pushed to GitHub.")
    except Exception as e:
        logger.warning(f"{CSV_FILE} not found in repo, creating new one.")
        with open(CSV_FILE, "r") as f:
            repo.create_file(
                CSV_FILE,
                f"Create {CSV_FILE}",
                f.read()
            )
        logger.info(f"✅ {CSV_FILE} created and pushed to GitHub.")

# -------------------------------------------------
# Command Handlers
# -------------------------------------------------
def subscribe(update: Update, context: CallbackContext):
    """Handle /subscribe <frequency> #<affiliate_id>"""
    chat = update.effective_chat
    args = context.args

    if len(args) < 2 or not args[1].startswith("#"):
        update.message.reply_text("⚠️ Usage: /subscribe <daily|weekly|manual> #<affiliate_id>")
        return

    frequency = args[0].lower()
    affiliate_id = args[1].lstrip("#")

    if frequency not in ["daily", "weekly", "manual"]:
        update.message.reply_text("⚠️ Frequency must be one of: daily, weekly, manual")
        return

    update_github_csv(chat.id, chat.title or chat.username or "Private Chat", frequency, affiliate_id)
    update.message.reply_text(
        f"✅ Subscribed {chat.title or chat.username} "
        f"to {frequency} updates for affiliate #{affiliate_id}"
    )
    logger.info(f"📩 Received /subscribe: chat_id={chat.id}, affiliate_id={affiliate_id}, frequency={frequency}")

def unsubscribe(update: Update, context: CallbackContext):
    """Handle /unsubscribe"""
    chat = update.effective_chat
    update.message.reply_text("✅ Unsubscribed this chat.")
    logger.info(f"📩 Received /unsubscribe: chat_id={chat.id}")

# -------------------------------------------------
# Middleware for @sofiaCNbot normalization
# -------------------------------------------------
def normalize_commands(update: Update, context: CallbackContext):
    """Convert @sofiaCNbot /subscribe → /subscribe and let dispatcher handle it."""
    text = update.message.text.strip()
    logger.info(f"💬 Raw message received: {text}")
    if text.lower().startswith("@sofiacnbot "):
        new_text = text.split(" ", 1)[1]
        update.message.text = new_text
        logger.info(f"🔄 Normalized to: {new_text}")
    # Dispatcher will handle normally — no re-dispatch

# -------------------------------------------------
# Register Handlers
# -------------------------------------------------
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, normalize_commands))
dispatcher.add_handler(CommandHandler("subscribe", subscribe))
dispatcher.add_handler(CommandHandler("unsubscribe", unsubscribe))

# -------------------------------------------------
# Flask route for Telegram webhook
# -------------------------------------------------
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), updater.bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "🤖 Sofia CN Bot is running!"

# -------------------------------------------------
# Start Flask app
# -------------------------------------------------
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))
    logger.info("🚀 Starting Flask app 'bot'")
    app.run(host="0.0.0.0", port=PORT)
