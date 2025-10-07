import os
import logging
import csv
from flask import Flask, request, Response, send_file
from telegram import Update
from telegram.ext import Updater, CallbackContext, Dispatcher, MessageHandler, Filters
from apscheduler.schedulers.background import BackgroundScheduler

# ----------------------------------------
# Logging setup
# ----------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------------------------------
# Constants and file setup
# ----------------------------------------
CSV_FILE = "/data/affiliates.csv"
HEADERS = ["ChatID", "Frequency", "AffiliateID"]

# ✅ Ensure affiliates.csv exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writeheader()
    logger.info("📂 Created new affiliates.csv with headers")

# ----------------------------------------
# Flask app setup
# ----------------------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "🤖 SofiaCNBot is running!"

@app.route("/download")
def download():
    if os.path.exists(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True)
    return "CSV file not found", 404

# ----------------------------------------
# Telegram setup
# ----------------------------------------
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
updater = Updater(token=TOKEN, use_context=True)
dispatcher: Dispatcher = updater.dispatcher

# ✅ Whitelisted Telegram usernames
APPROVED_USERNAMES = {"blakebarrett", "sarahbradford", "iamamil05", "gbrookshire"}

def normalize_message(message: str) -> str:
    return message.replace("@sofiaCNbot", "").strip()

# ----------------------------------------
# Message handler
# ----------------------------------------
def handle_message(update: Update, context: CallbackContext):
    raw_text = update.message.text or ""
    username = str(update.message.from_user.username or "")
    user_id = str(update.message.from_user.id)

    # 🚫 Ignore non-approved users
    if username.lower() not in APPROVED_USERNAMES:
        logger.warning(f"🚫 Unauthorized attempt by {username} (ID {user_id}) with message: {raw_text}")
        return

    logger.info(f"💬 Authorized command from {username}: {raw_text}")
    text = normalize_message(raw_text)
    logger.info(f"🔄 Normalized to: {text}")

    # ----------------------------------------
    # /subscribe command
    # ----------------------------------------
    if text.startswith("/subscribe"):
        try:
            parts = text.split()
            if len(parts) != 3:
                update.message.reply_text("⚠️ Usage: /subscribe <daily|weekly|manual|Sofia_*Type*> <AffiliateID>")
                return

            _, frequency, affiliate_id = parts
            chat_id = str(update.message.chat_id)
            chat_name = update.message.chat.title or update.message.chat.username or "Private Chat"

            # ✅ Case-insensitive Sofia detection
            freq_lower = frequency.lower()
            is_sofia_subscription = freq_lower.startswith("sofia_")

            # ✅ Only validate standard affiliate frequencies
            if not is_sofia_subscription:
                if freq_lower not in ["daily", "weekly", "manual"]:
                    update.message.reply_text("⚠️ Frequency must be one of: daily, weekly, or manual")
                    return
                frequency = freq_lower  # normalize for storage

            # ✅ Clean AffiliateID
            affiliate_id = affiliate_id.lstrip("#")
            if not affiliate_id.isdigit():
                update.message.reply_text("⚠️ AffiliateID must be numeric (use 0 for internal Sofia updates).")
                return

            # ✅ Load existing subscriptions
            rows = []
            if os.path.exists(CSV_FILE):
                with open(CSV_FILE, mode="r", newline="") as file:
                    reader = csv.DictReader(file)
                    rows = list(reader)

            # ✅ Prevent duplicate subscriptions (same ChatID + Frequency)
            duplicate = any(
                row["ChatID"] == chat_id and row["Frequency"].lower() == freq_lower
                for row in rows
            )

            if duplicate:
                update.message.reply_text(f"⚠️ This chat is already subscribed for {frequency}.")
            else:
                rows.append({
                    "ChatID": chat_id,
                    "Frequency": frequency,
                    "AffiliateID": affiliate_id
                })

                with open(CSV_FILE, mode="w", newline="") as file:
                    writer = csv.DictWriter(file, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(rows)

                if is_sofia_subscription:
                    update.message.reply_text(f"✅ Subscribed this chat for {frequency} updates.")
                else:
                    update.message.reply_text(f"✅ Subscribed: ID #{affiliate_id} | {frequency}")

                logger.info(
                    f"📝 affiliates.csv updated → {chat_id}, {frequency}, {affiliate_id} from chat '{chat_name}'"
                )

        except Exception as e:
            logger.error(f"❌ Error in subscribe: {e}")
            update.message.reply_text("⚠️ Something went wrong while updating your subscription.")

    # ----------------------------------------
    # /unsubscribe command
    # ----------------------------------------
    elif text.startswith("/unsubscribe"):
        try:
            chat_id = str(update.message.chat_id)
            chat_name = update.message.chat.title or update.message.chat.username or "Private Chat"

            rows = []
            if os.path.exists(CSV_FILE):
                with open(CSV_FILE, mode="r", newline="") as file:
                    reader = csv.DictReader(file)
                    # Remove all rows for this chat ID
                    rows = [row for row in reader if row["ChatID"] != chat_id]

            with open(CSV_FILE, mode="w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=HEADERS)
                writer.writeheader()
                writer.writerows(rows)

            logger.info(f"🗑️ Unsubscribed chat {chat_id} ('{chat_name}')")
            update.message.reply_text("✅ This chat has been unsubscribed.")

        except Exception as e:
            logger.error(f"❌ Error in unsubscribe: {e}")
            update.message.reply_text("⚠️ Something went wrong while unsubscribing.")

# ----------------------------------------
# Register message handler
# ----------------------------------------
dispatcher.add_handler(MessageHandler(Filters.text, handle_message))

# ----------------------------------------
# Scheduler & Webhook setup
# ----------------------------------------
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
