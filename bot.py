import os
import logging
import csv
from flask import Flask, request, Response, send_file
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, Dispatcher
from apscheduler.schedulers.background import BackgroundScheduler

# Logging for cleaner logs
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# File path for CSV
CSV_FILE = "affiliates.csv"

# Make sure the CSV exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["ChatID", "ChatName", "Frequency", "AffiliateID"])  # headers
    logger.info("📂 Created new affiliates.csv with headers")

# Flask app for webhooks + CSV download
app = Flask(__name__)

@app.route("/")
def home():
    return "🤖 SofiaCNBot is running!"

@app.route("/download")
def download():
    """Download the affiliates.csv file directly."""
    if os.path.exists(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True)
    return "CSV file not found", 404

# Telegram bot setup
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
updater = Updater(token=TOKEN, use_context=True)
dispatcher: Dispatcher = updater.dispatcher

def normalize_message(message: str) -> str:
    """Normalize by stripping bot mentions and extra spaces."""
    return message.replace("@sofiaCNbot", "").strip()

def subscribe(update: Update, context: CallbackContext):
    """Handle /subscribe commands from affiliate managers."""
    message = normalize_message(update.message.text)
    logger.info(f"💬 Raw message received: {update.message.text}")
    logger.info(f"🔄 Normalized to: {message}")

    try:
        parts = message.split()
        if len(parts) != 3:
            update.message.reply_text("⚠️ Usage: /subscribe <daily|weekly|manual> #<AffiliateID>")
            return

        command, frequency, affiliate_id = parts
        frequency = frequency.lower()

        if frequency not in ["daily", "weekly", "manual"]:
            update.message.reply_text("⚠️ Frequency must be one of: daily, weekly, manual")
            return

        chat_id = update.message.chat_id
        chat_name = update.message.chat.title or update.message.chat.username or "Private Chat"

        # Update CSV
        rows = []
        updated = False
        with open(CSV_FILE, mode="r", newline="") as file:
            reader = csv.reader(file)
            rows = list(reader)

        for row in rows:
            if row and row[0] == str(chat_id):
                row[2] = frequency
                row[3] = affiliate_id
                updated = True
                break

        if not updated:
            rows.append([chat_id, chat_name, frequency, affiliate_id])

        with open(CSV_FILE, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(rows)

        update.message.reply_text(f"✅ Subscription updated: {frequency} updates for {affiliate_id}")
        logger.info(f"📝 Updated CSV: {chat_id}, {chat_name}, {frequency}, {affiliate_id}")

    except Exception as e:
        logger.error(f"❌ Error in subscribe: {e}")
        update.message.reply_text("⚠️ Something went wrong while updating your subscription.")

# Add command handler
dispatcher.add_handler(CommandHandler("subscribe", subscribe))

# Scheduler (for future daily/weekly pushes)
scheduler = BackgroundScheduler()
scheduler.start()

# Flask webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """Handle incoming Telegram updates via webhook."""
    update = Update.de_json(request.get_json(force=True), updater.bot)
    dispatcher.process_update(update)
    return Response("ok", status=200)

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))
    updater.bot.set_webhook(url=f"{os.environ['RENDER_EXTERNAL_URL']}/{TOKEN}")
    logger.info(f"🌍 Webhook set to {os.environ['RENDER_EXTERNAL_URL']}/{TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
