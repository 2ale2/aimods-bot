from telegram.ext import ContextTypes
from telegram import Update
import core


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    La risposta dipende dall'utente: se è admin, allora stampo il pannello di controllo; altrimenti do il benvenuto.
    """
    if is_admin(update.effective_user.id, context):
        # stampa pannello di controllo
        pass
    else:
        # stampa
        pass

    # per ora stampiamo semplicemente il benvenuto
    await context.bot.send_message(chat_id=update.effective_user.id, text="Hi A&I Mods Staff! :)")


def is_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    return user_id in context.bot_data["admins"].keys()
