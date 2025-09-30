import os
import json
import time
import logging
import csv
from telegram import Bot

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
bot = Bot(token=TOKEN)

JSON_FILE = "messages.json"
CSV_FILE = "/data/affiliates.csv"
HEADERS = ["ChatID", "Frequency", "AffiliateID"]

def update_chat_id(old_chat_id, new_chat_id):
    """Update affiliates.csv replacing old_chat_id with new_chat_id"""
    if not os.path.exists(CSV_FILE):
        return

    rows = []
    with open(CSV_FILE, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    for row in rows:
        if row["ChatID"] == str(old_chat_id):
            row["ChatID"] = str(new_chat_id)

    with open(CSV_FILE, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"🔄 affiliates.csv updated: {old_chat_id} → {new_chat_id}")

def main():
    if not os.path.exists(JSON_FILE):
        logger.warning("⚠️ No messages.json found — nothing to broadcast.")
        return

    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            messages = json.load(f)

        if not isinstance(messages, list):
            logger.error("❌ Invalid messages.json format — must be a list of {chat_id, message}.")
            return

        sent_count = 0
        fail_count = 0
        failures = []

        for item in messages:
            chat_id = item.get("chat_id")
            message = item.get("message")

            if not chat_id or not message:
                logger.warning(f"⚠️ Skipping invalid entry: {item}")
                continue

            try:
                bot.send_message(chat_id=chat_id, text=message)
                sent_count += 1
                logger.info(f"📤 Sent to {chat_id}: {message[:50]}...")
                time.sleep(0.1)

            except Exception as e:
                error_str = str(e)
                fail_count += 1

                # Handle group migration
                if "migrated to supergroup" in error_str.lower() and "New chat id:" in error_str:
                    try:
                        new_chat_id = error_str.split("New chat id:")[-1].strip()
                        logger.info(f"🔄 Group migrated: {chat_id} → {new_chat_id}")

                        # Update affiliates.csv
                        update_chat_id(chat_id, new_chat_id)

                        # Retry sending the message
                        bot.send_message(chat_id=new_chat_id, text=message)
                        sent_count += 1
                        logger.info(f"📤 Resent to new chat_id {new_chat_id}: {message[:50]}...")
                        continue  # skip marking this as failure since retry succeeded

                    except Exception as inner_e:
                        failures.append((chat_id, f"Migration handling failed: {inner_e}"))
                        logger.error(f"❌ Migration handling failed for {chat_id}: {inner_e}")

                else:
                    failures.append((chat_id, str(e)))
                    logger.error(f"❌ Failed to send to {chat_id}: {e}")

        os.remove(JSON_FILE)
        logger.info("🗑️ messages.json deleted after broadcast.")

        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        logger.info("📂 New blank messages.json created.")

        logger.info(f"✅ Broadcast complete — {sent_count} sent, {fail_count} failed.")
        if failures:
            logger.info("❌ Failure details:")
            for chat_id, error in failures:
                logger.info(f"   - ChatID {chat_id}: {error}")

    except Exception as e:
        logger.error(f"❌ Broadcast failed: {e}")

if __name__ == "__main__":
    main()
