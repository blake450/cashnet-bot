import os
import logging
import csv
import subprocess
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
from telegram import Update
from telegram.ext import CallbackContext

# Enable logging (goes to Render logs)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Telegram Bot Token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Personal Access Token
GITHUB_REPO = "blake450/cashnet-bot"  # Update if your repo is different
CSV_FILE = "subscriptions.csv"


# Ensure CSV exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["chat_id", "chat_name", "frequency", "affiliate_id"])
    logger.info("Created new subscriptions.csv with headers")


def push_to_github():
    """Commit and push CSV changes back to GitHub"""
    try:
        subprocess.run(["git", "config", "--global", "user.email", "sofiabot@cashnet.com"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "SofiaBot"], check=True)
        subprocess.run(["git", "add", CSV_FILE], check=True)
        subprocess.run(["git", "commit", "-m", "Update subscriptions.csv"], check=True)
        subprocess.run([
            "git", "push",
            f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git",
            "HEAD:main"
        ], check=True)
        logger.info("✅ subscriptions.csv pushed to GitHub")
    except Exception as e:
        logger.error(f"❌ Failed to push CSV to GitHub: {e}")


def subscribe(update: Update, context: CallbackContext):
    """Handles /subscribe"""
    chat = update.effective_chat
    chat_id = chat.id
    chat_name = chat.title or chat.username or "Private Chat"

    args = context.args
    if len(args) < 2:
        update.message.reply_text("⚠️ Usage: @sofiacnbot /subscribe <frequency> #<affiliate_id>")
        return

    frequency = args[0].lower()
    affiliate_id = args[1].replace("#", "")

    if frequency not in ["daily", "weekly", "manual"]:
        update.message.reply_text("⚠️ Frequency must be one of: daily, weekly, manual")
        return

    # Read/update CSV
    rows = []
    found = False
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row["chat_id"]) == str(chat_id):
                    row["frequency"] = frequency
                    row["affiliate_id"] = affiliate_id
                    found = True
                rows.append(row)

    if not found:
        rows.append({
            "chat_id": chat_id,
            "chat_name": chat_name,
            "frequency": frequency,
            "affiliate_id": affiliate_id
        })

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["chat_id", "chat_name", "frequency", "affiliate_id"])
        writer.writeheader()
        writer.writerows(rows)

    update.message.reply_text(f"✅ Subscription updated: {frequency} updates for affiliate #{affiliate_id}")
    logger.info(f"Updated subscription → Chat ID={chat_id}, Chat Name={chat_name}, Frequency={frequency}, Affiliate ID={affiliate_id}")

    push_to_github()


def status(update: Update, context: CallbackContext):
    """Handles /status"""
    chat = update.effective_chat
    chat_id = chat.id

    if not os.path.exists(CSV_FILE):
        update.message.reply_text("ℹ️ No subscription data available yet.")
        return

    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row["chat_id"]) == str(chat_id):
                update.message.reply_text(
                    f"📊 Current subscription:\nAffiliate ID: {row['affiliate_id']}\nFrequency: {row['frequency'].upper()}"
                )
                return

    update.message.reply_text("ℹ️ This chat is not subscribed yet.")


def unsubscribe(update: Update, context: CallbackContext):
    """Handles /unsubscribe"""
    chat = update.effective_chat
    chat_id = chat.id

    rows = []
    removed = False
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row["chat_id"]) == str(chat_id):
                    removed = True
                    continue
                rows.append(row)

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["chat_id", "chat_name", "frequency", "affiliate_id"])
        writer.writeheader()
        writer.writerows(rows)

    if removed:
        update.message.reply_text("🗑️ This chat has been unsubscribed.")
    else:
        update.message.reply_text("ℹ️ This chat was not subscribed.")

    push_to_github()


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Hi! I’m Sofia, your Cash Network Assistant.\n\n"
        "Commands:\n"
        "@sofiacnbot /subscribe <frequency> #<affiliate_id>\n"
        "@sofiacnbot /status\n"
        "@sofiacnbot /unsubscribe"
    )


def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("subscribe", subscribe, pass_args=True))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("unsubscribe", unsubscribe))
    dp.add_handler(CommandHandler("start", start))

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, lambda u, c: None))

    updater.start_polling()
    logger.info("🤖 Bot is running and ready for commands...")
    updater.idle()


if __name__ == "__main__":
    main()
