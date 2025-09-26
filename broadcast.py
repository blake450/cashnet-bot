import os
import json
import time
import logging
from telegram import Bot

# -------------------------------------------------
# Logging setup
# -------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# Telegram setup
# -------------------------------------------------
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
bot = Bot(token=TOKEN)

# -------------------------------------------------
# Broadcast runner
# -------------------------------------------------
JSON_FILE = "messages.json"

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
                time.sleep(0.1)  # throttle to ~10 msgs/sec max
            except Exception as e:
                fail_count += 1
                failures.append((chat_id, str(e)))
                logger.error(f"❌ Failed to send to {chat_id}: {e}")

        # Delete old file
        os.remove(JSON_FILE)
        logger.info("🗑️ messages.json deleted after broadcast.")

        # Create new blank file for next time
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        logger.info("📂 New blank messages.json created.")

        # Summary
        logger.info(f"✅ Broadcast complete — {sent_count} sent, {fail_count} failed.")
        if failures:
            logger.info("❌ Failure details:")
            for chat_id, error in failures:
                logger.info(f"   - ChatID {chat_id}: {error}")

    except Exception as e:
        logger.error(f"❌ Broadcast failed: {e}")

if __name__ == "__main__":
    main()
