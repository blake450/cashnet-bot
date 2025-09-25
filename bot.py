import os
import csv
import logging
import subprocess
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# --- Logging setup ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Env Vars ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = "blake450/cashnet-bot"
CSV_FILE = "affiliates.csv"

# --- Telegram Bot Setup ---
bot = Bot(token=BOT_TOKEN)

# --- Flask App Setup ---
app = Flask(__name__)

# --- Ensure CSV Exists ---
def ensure_csv_exists():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["chat_id", "chat_name", "affiliate_id", "frequency"])
        logger.info("📄 Created new affiliates.csv with headers")

# --- GitHub Push ---
def push_to_github():
    repo_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
    try:
        subprocess.run(["git", "config", "user.email", "sofia-bot@cashnet.com"], check=True)
        subprocess.run(["git", "config", "user.name", "Sofia Bot"], check=True)
        subprocess.run(["git", "add", CSV_FILE], check=True)
        result = subprocess.run(
            ["git", "commit", "-m", "Update affiliates.csv"],
            capture_output=True, text=True
        )
        logger.info(f"🔍 Commit result: {result.stdout.strip()} {result.stderr.strip()}")
        if "nothing to commit" in result.stdout.lower():
            logger.info("ℹ️ No changes in affiliates.csv, skipping push.")
        else:
            subprocess.run(["git", "push", repo_url, "main"], check=True)
            logger.info("✅ affiliates.csv pushed to GitHub successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"⚠️ Git push failed: {e}")

# --- Command Handlers ---
def subscribe(update: Update, context: CallbackContext):
    message = update.message.text.strip()
    logger.info(f"📩 Received command: {message}")

    parts = message.split()
    if len(parts) < 3:
        update.message.reply_text("⚠️ Usage: /subscribe <daily|weekly|manual> #<affiliate_id>")
        return

    frequency = parts[1].lower()
    affiliate_id = parts[2].lstrip("#")

    if frequency not in ["daily", "weekly", "manual"]:
        update.message.reply_text("⚠️ Frequency must be one of: daily, weekly, manual")
        return

    chat_id = str(update.message.chat_id)
    chat_name = update.message.chat.title or update.message.chat.username or "Unknown"

    rows = []
    found = False
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    for row in rows:
        if row["chat_id"] == chat_id:
            row["affiliate_id"] = affiliate_id
            row["frequency"] = frequency
            found = True
            break

    if not found:
        rows.append(
            {"chat_id": chat_id, "chat_name": chat_name, "affiliate_id": affiliate_id, "frequency": frequency}
        )

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["chat_id", "chat_name", "affiliate_id", "frequency"])
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"📝 Updated CSV: chat_id={chat_id}, affiliate_id={affiliate_id}, frequency={frequency}")
    update.message.reply_text(f"✅ Subscribed {chat_name} (#{affiliate_id}) to {frequency} updates.")

    push_to_github()

def unsubscribe(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    chat_name = update.message.chat.title or update.message.chat.username or "Unknown"
    logger.info(f"📩 Received command: /unsubscribe from {chat_name} ({chat_id})")

    rows = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", newline="") as f:
            reader = csv.DictReader(f)
            rows = [row for row in reader if row["chat_id"] != chat_id]

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["chat_id", "chat_name", "affiliate_id", "frequency"])
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"🗑️ Removed subscription for chat_id={chat_id}")
    update.message.reply_text(f"✅ Unsubscribed {chat_name}.")
    push_to_github()

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Hi! I’m Sofia, your Cash Network Assistant.\n\n"
        "Commands:\n"
        "/subscribe <daily|weekly|manual> #<affiliate_id>\n"
        "/unsubscribe"
    )

def log_all_messages(update: Update, context: CallbackContext):
    """Log any text message (debugging only)."""
    logger.info(f"💬 Raw message received: {update.message.text}")

# --- Dispatcher Setup ---
dispatcher = Dispatcher(bot, None, workers=0)
dispatcher.add_handler(CommandHandler("subscribe", subscribe))
dispatcher.add_handler(CommandHandler("unsubscribe", unsubscribe))
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, log_all_messages))

# --- Flask Routes ---
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "🤖 Sofia bot is running with webhooks!", 200

# --- Main Entry ---
if __name__ == "__main__":
    ensure_csv_exists()

    render_url = os.getenv("RENDER_URL")
    if not render_url:
        raise RuntimeError("⚠️ Missing RENDER_URL environment variable in Render.")

    webhook_url = f"{render_url}/{BOT_TOKEN}"
    bot.delete_webhook()
    bot.set_webhook(webhook_url)

    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Starting Flask on port {port}, webhook set to {webhook_url}")
    app.run(host="0.0.0.0", port=port)
