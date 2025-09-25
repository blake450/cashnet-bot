import os
import logging
import csv
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
from telegram import Update
from telegram.ext import CallbackContext

# Enable logging (logs will go to Render console automatically)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")  # make sure it's BOT_TOKEN in Render
CSV_FILE = "subscriptions.csv"

# Ensure CSV exists with headers
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["chat_id", "chat_name", "frequency", "affiliate_id"])
    logger.info("Created new subscriptions.csv with headers")


def subscribe(update: Update, context: CallbackContext):
    """Handles the /subscribe command from affiliate managers"""
    chat = update.effective_chat
    chat_id = chat.id
    chat_name = chat.title or chat.username or "Private Chat"

    args = context.args
    if len(args) < 2:
        update.message.reply_text("⚠️ Usage: /subscribe <frequency> #<affiliate_id>")
        return

    frequency = args[0].lower()
    affiliate_id = args[1].replace("#", "")

    if frequency not in ["daily", "weekly", "manual"]:
        update.message.reply_text("⚠️ Frequency must be one of: daily, weekly, manual")
        return

    # Read existing rows
    rows = []
    found = False
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row["chat_id"]) == str(chat_id):
                    row["frequency"] = frequency
                    row["affiliate_id"] = affiliate_id
                    found = True
                rows.append(row)

    # Add new row if not found
    if not found:
        rows.append({
            "chat_id": chat_id,
            "chat_name": chat_name,
            "frequency": frequency,
            "affiliate_id": affiliate_id
        })

    # Write back to CSV
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["chat_id", "chat_name", "frequency", "affiliate_id"])
        writer.writeheader()
        writer.writerows(rows)

    update.message.reply_text(f"✅ Subscription updated: {frequency} updates for affiliate #{affiliate_id}")
    logger.info(f"Updated subscription → Chat ID={chat_id}, Chat Name={chat_name}, Frequency={frequency}, Affiliate ID={affiliate_id}")


def start(update: Update, context: CallbackContext):
    """Handles /start command"""
    update.message.reply_text("👋 Hi! I’m Sofia, your Cash Network Assistant.\nUse /subscribe <frequency> #<affiliate_id> to manage updates.")


def main():
    """Start the bot"""
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Command handlers
    dp.add_handler(CommandHandler(["subscribe", "subscribe@sofiacnbot"], subscribe, pass_args=True))
    dp.add_handler(CommandHandler("start", start))

    # Fallback handler for unknown text
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, lambda u, c: None))

    # Start polling
    updater.start_polling()
    logger.info("🤖 Bot is running and ready for commands...")
    updater.idle()


if __name__ == "__main__":
    main()
