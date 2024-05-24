from telegram.ext import ContextTypes
from telegram import Update
from datetime import datetime, timedelta
from copy import deepcopy
import telegram.error

import core
from loggers import command_logger
from constants import Exceptions, Scopes
import database_functions


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
    scopes = Scopes()
    message = deepcopy(update.message)
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id,
                                         message_id=update.message.message_id)
    except telegram.error.TelegramError:
        pass

    if is_admin(update.effective_user.id, context):
        if datetime.now(message.reply_to_message.date.tzinfo) - message.reply_to_message.date > timedelta(hours=48):
            core.command_logger.error("Message cannot be deleted from bot cause it was sent more than 48h ago.")
            return

        user_identifier = (update.message.reply_to_message.from_user.username or
                           update.message.reply_to_message.from_user.id)
        reason = "_" + ' '.join(context.args) + "_" if context.args else '`no reason given`'
        try:
            await context.bot.delete_message(chat_id=context.bot_data["group_chat_id"],
                                             message_id=message.reply_to_message.message_id)
        except telegram.error.TelegramError as e:
            core.command_logger.error(f"Message cannot be deleted {e}")
        else:
            if user_identifier.isnumeric():
                text = (f'♻️ Message sent by [{update.effective_user.first_name}](tg://user?id={user_identifier})'
                        f' was removed: {reason}')
            else:
                text = f'♻️ Message sent by @{user_identifier} was removed: {reason}'

            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           message_thread_id=(
                                               message.message_thread_id
                                               if message.message_thread_id in scopes.FORUM_SCOPE.topics else None),
                                           text=text, parse_mode="MARKDOWN")

            try:
                await database_functions.add_to_table(table_name='deleted_messages', content=update)
            except Exceptions.DatabaseException as e:
                command_logger.error(f'Something went wrong while operating with database: {e.error_message}')


def is_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    return str(user_id) in context.bot_data["admins"].keys()
