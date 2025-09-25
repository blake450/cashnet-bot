import os
from telegram.ext import Updater, MessageHandler, Filters

def log_chat_id(update, context):
    chat = update.effective_chat
    print(f"Chat ID: {chat.id} | Chat Title: {chat.title}")

def main():
    # Get your bot token from Render environment variable
    token = os.getenv("BOT_TOKEN")
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    # Log all messages to get chat IDs
    dp.add_handler(MessageHandler(Filters.all, log_chat_id))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
