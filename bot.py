import os
import csv
from telegram.ext import Updater, CommandHandler
from telegram import Update
from telegram.ext import CallbackContext

AFFILIATES_FILE = "affiliates.csv"
MANAGERS_FILE = "managers.txt"

# Load managers from file
def load_managers():
    if not os.path.exists(MANAGERS_FILE):
        return []
    with open(MANAGERS_FILE, "r") as f:
        return [line.strip().lower() for line in f.readlines()]

def is_manager(username):
    managers = load_managers()
    return username.lower() in managers

# Ensure affiliates.csv exists
def ensure_csv():
    if not os.path.exists(AFFILIATES_FILE):
        with open(AFFILIATES_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["AffiliateID", "ChatID", "ChatName", "MessageFrequency", "LastSent"])

def update_csv(affiliate_id, chat_id, chat_name, frequency):
    ensure_csv()
    rows = []
    updated = False

    with open(AFFILIATES_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row["ChatID"]) == str(chat_id):
                row["AffiliateID"] = affiliate_id
                row["ChatName"] = chat_name
                row["MessageFrequency"] = frequency
                updated = True
            rows.append(row)

    if not updated:
        rows.append({
            "AffiliateID": affiliate_id,
            "ChatID": chat_id,
            "ChatName": chat_name,
            "MessageFrequency": frequency,
            "LastSent": ""
        })

    with open(AFFILIATES_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["AffiliateID", "ChatID", "ChatName", "MessageFrequency", "LastSent"])
        writer.writeheader()
        writer.writerows(rows)

def subscribe(update: Update, context: CallbackContext):
    user = update.effective_user.username
    if not is_manager(user):
        update.message.reply_text("❌ You are not authorized to manage subscriptions for this group.")
        return

    if len(context.args) < 2 or not context.args[1].startswith("#"):
        update.message.reply_text("⚠️ Usage: /subscribe <daily|weekly|manual> #<AffiliateID>")
        return

    frequency = context.args[0].lower()
    affiliate_id = context.args[1].replace("#", "")
    chat = update.effective_chat

    if frequency not in ["daily", "weekly", "manual"]:
        update.message.reply_text("⚠️ Frequency must be one of: daily, weekly, manual")
        return

    update_csv(affiliate_id, chat.id, chat.title, frequency)
    update.message.reply_text(
        f"✅ Subscription updated:\nAffiliateID: {affiliate_id}\nFrequency: {frequency.upper()}"
    )

def status(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    ensure_csv()
    with open(AFFILIATES_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row["ChatID"]) == str(chat_id):
                update.message.reply_text(
                    f"📊 Current settings:\n"
                    f"AffiliateID: {row['AffiliateID']}\n"
                    f"Frequency: {row['MessageFrequency'].upper()}\n"
                    f"LastSent: {row['LastSent']}"
                )
                return
    update.message.reply_text("ℹ️ This group is not subscribed yet.")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ ERROR: BOT_TOKEN not found in environment variables.")
        return

    ensure_csv()
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("subscribe", subscribe))
    dp.add_handler(CommandHandler("status", status))

    print("🤖 Bot is running and ready for commands...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
