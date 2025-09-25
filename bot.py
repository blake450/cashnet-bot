import os
from telegram.ext import Updater, MessageHandler, Filters

def log_chat_id(update, context):
    chat = update.effective_chat
    user = update.effective_user
    message = update.message.text if update.message else "non-text message"
    print(f"[MESSAGE RECEIVED] Chat ID: {chat.id} | Chat Title: {chat.title} | From: {user.username} | Text: {message}")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ ERROR: BOT_TOKEN not found in environment variables.")
        return

    print("✅ Bot is starting... Waiting for messages...")
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    # Log all messages (text, stickers, images, etc.)
    dp.add_handler(MessageHandler(Filters.all, log_chat_id))

    updater.start_polling()
    print("🤖 Bot is running and listening for messages...")
    updater.idle()

if __name__ == "__main__":
    main()
