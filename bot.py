import os
import logging
import csv
from flask import Flask, request, Response, send_file
from telegram import Update
from telegram.ext import Updater, CallbackContext, Dispatcher, MessageHandler, Filters
from apscheduler.schedulers.background import BackgroundScheduler

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

CSV_FILE = "/data/affiliates.csv"
HEADERS = ["ChatID", "Frequency", "AffiliateID"]

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writeheader()
    logger.info("📂 Created new affiliates.csv with headers")

app = Flask(__name__)

@app.route("/")
def home():
    return "🤖 SofiaCNBot is running!"

@app.route("/download")
def download():
    if os.path.exists(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True)
    return "CSV file not found", 404

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
updater = Updater(token=TOKEN, use_context=True)
dispatcher: Dispatcher = updater.dispatcher

def normalize_message(message: str) -> str:
    return message.replace("@sofiaCNbot", "").strip()

def handle_message(update: Update, context: CallbackContext):
    raw_text = update.message.text or ""
    logger.info(f"💬 Raw message received: {raw_text}")
    text = normalize_message(raw_text)
    logger.info(f"🔄 Normalized to: {text}")

    if text.startswith("/subscribe"):
        try:
            parts = text.split()
            if len(parts) != 3:
                update.message.reply_text("⚠️ Usage: /subscribe <daily|weekly|manual> #<AffiliateID>")
                return

            _, frequency, affiliate_id = parts
            frequency = frequency.lower()

            if frequency not in ["daily", "weekly", "manual"]:
                update.message.reply_text("⚠️ Frequency must be one of: daily, weekly, manual")
                return

            affiliate_id = affiliate_id.lstrip("#")
            chat_id = str(update.message.chat_id)
            chat_name = update.message.chat.title or update.message.chat.username or "Private Chat"

            rows = []
            if os.path.exists(CSV_FILE):
                with open(CSV_FILE, mode="r", newline="") as file:
                    reader = csv.DictReader(file)
                    rows = list(reader)

            # ✅ Check for duplicate (ChatID + AffiliateID combo)
            duplicate = any(
                row["ChatID"] == chat_id and row["AffiliateID"] == affiliate_id
                for row in rows
            )

            if duplicate:
                update.message.reply_text(f"⚠️ ID #{affiliate_id} is already subscribed in this chat.")
            else:
                # Add a new row for this ChatID + AffiliateID
                rows.append({
                    "ChatID": chat_id,
                    "Frequency": frequency,
                    "AffiliateID": affiliate_id
                })

                with open(CSV_FILE, mode="w", newline="") as file:
                    writer = csv.DictWriter(file, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(rows)

                logger.info(f"📝 affiliates.csv updated → {chat_id}, {frequency}, {affiliate_id} from chat '{chat_name}'")
                update.message.reply_text(f"✅ Subscribed: ID #{affiliate_id} | {frequency}")

        except Exception as e:
            logger.error(f"❌ Error in subscribe: {e}")
            update.message.reply_text("⚠️ Something went wrong while updating your subscription.")

    elif text.startswith("/unsubscribe"):
        try:
            chat_id = str(update.message.chat_id)
            chat_name = update.message.chat.title or update.message.chat.username or "Private Chat"

            rows = []
            if os.path.exists(CSV_FILE):
                with open(CSV_FILE, mode="r", newline="") as file:
                    reader = csv.DictReader(file)
                    rows = [row for row in reader if row["ChatID"] != chat_id]

            with open(CSV_FILE, mode="w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=HEADERS)
                writer.writeheader()
                writer.writerows(rows)

            logger.info(f"🗑️ Removed subscription → {chat_id} from chat '{chat_name}'")
            update.message.reply_text(f"✅ Unsubscribed this chat.")

        except Exception as e:
            logger.error(f"❌ Error in unsubscribe: {e}")
            update.message.reply_text("⚠️ Something went wrong while unsubscribing.")

dispatcher.add_handler(MessageHandler(Filters.text, handle_message))

scheduler = BackgroundScheduler()
scheduler.start()

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), updater.bot)
    dispatcher.process_update(update)
    return Response("ok", status=200)

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))
    updater.bot.set_webhook(url=f"{os.environ['RENDER_EXTERNAL_URL']}/{TOKEN}")
    logger.info(f"🌍 Webhook set to {os.environ['RENDER_EXTERNAL_URL']}/{TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
