import os
import csv
import logging
import subprocess
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# --- Logging setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

CSV_FILE = "affiliates.csv"

# --- CSV Setup ---
def ensure_csv_exists():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["chat_id", "chat_name", "affiliate_id", "frequency"])
        logger.info("Created new affiliates.csv with headers")

# --- GitHub Auto-Push ---
def push_to_github():
    repo_url = f"https://{os.environ['GITHUB_TOKEN']}@github.com/blake450/cashnet-bot.git"
    try:
        subprocess.run(["git", "config", "--global", "user.email", "sofia-bot@cashnet.com"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "Sofia Bot"], check=True)
        subprocess.run(["git", "add", CSV_FILE], check=True)
        subprocess.run(["git", "commit", "-m", "Update affiliates.csv"], check=True)
        subprocess.run(["git", "push", repo_url, "main"], check=True)
        logger.info("✅ affiliates.csv pushed to GitHub successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"⚠️ Git push failed: {e}")

# --- Handlers ---
def subscribe(update: Update, context: CallbackContext):
    message = update.message.text.strip()
    parts = message.split()

    if len(parts) < 4:
        update.message.reply_text("⚠️ Usage: @sofiacnbot /subscribe <daily|weekly|manual> #<affiliate_id>")
        return

    frequency = parts[2].lower()
    affiliate_id = parts[3].lstrip("#")

    if frequency not in ["daily", "weekly", "manual"]:
        update.message.reply_text("⚠️ Frequency must be one of: daily, weekly, manual")
        return

    chat_id = update.message.chat_id
    chat_name = update.message.chat.title or update.message.chat.username or "Unknown"

    rows = []
    found = False
    with open(CSV_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        if row["chat_id"] == str(chat_id):
            row["affiliate_id"] = affiliate_id
            row["frequency"] = frequency
            found = True
            break

    if not found:
        rows.append(
            {
                "chat_id": chat_id,
                "chat_name": chat_name,
                "affiliate_id": affiliate_id,
                "frequency": frequency,
            }
        )

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["chat_id", "chat_name", "affiliate_id", "frequency"])
        writer.writeheader()
        writer.writerows(rows)

    update.message.reply_text(f"✅ Subscribed {chat_name} (#{affiliate_id}) to {frequency} updates.")
    push_to_github()

def unsubscribe(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    chat_name = update.message.chat.title or update.message.chat.username or "Unknown"

    rows = []
    with open(CSV_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader if row["chat_id"] != chat_id]

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["chat_id", "chat_name", "affiliate_id", "frequency"])
        writer.writeheader()
        writer.writerows(rows)

    update.message.reply_text(f"✅ Unsubscribed {chat_name}.")
    push_to_github()

# --- Main ---
def main():
    ensure_csv_exists()

    TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Commands
    dp.add_handler(CommandHandler("subscribe", subscribe))
    dp.add_handler(CommandHandler("unsubscribe", unsubscribe))

    logger.info("🤖 Bot is running and ready for commands...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
