import logging, os

from telegram.ext import ApplicationBuilder, CommandHandler
from dotenv import load_dotenv

logging.getLogger('httpx').setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def start(update, context):
    await context.bot.approve_chat_join_request(chat_id=-1002012686250,
                                                user_id=update.effective_user.id)



def main():
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    application.add_handler(CommandHandler("start", callback=start))

    application.run_polling()


if __name__ == '__main__':
    load_dotenv('.env')
    main()