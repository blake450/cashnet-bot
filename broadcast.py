import os
import json
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

        for item in messages:
            chat_id = item.get("chat_id")
            message = item.get("message")

            if not chat_id or not message:
                logger.warning(f"⚠️ Skipping invalid entry: {item}")
                continue

            bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"📤 Sent to {chat_id}: {message[:50]}...")

        # Delete file after sending
        os.remove(JSON_FILE)
        logger.info("🗑️ messages.json deleted after broadcast.")

    except Exception as e:
        logger.error(f"❌ Broadcast failed: {e}")

if __name__ == "__main__":
    main()
