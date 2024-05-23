from telegram.ext import ContextTypes
from telegram import Update
from datetime import datetime, timedelta
import telegram.error
import datetime

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


# DOPPIA VERIFICA
async def new_member_joined_forum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


# COMANDO RIMOZIONE MESSAGGI
async def delete_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id, context):
        try:
            await context.bot.delete_message(chat_id=context.bot_data["group_chat_id"],
                                             message_id=update.message.external_reply.message_id)
        except telegram.error.TelegramError as e:
            if update.message.external_reply.origin.date - datetime.now() > timedelta(hours=48):
                core.command_logger.info("Message ")
            pass


def is_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    return user_id in context.bot_data["admins"].keys()
