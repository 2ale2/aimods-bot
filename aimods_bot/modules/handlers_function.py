from telegram.ext import ContextTypes, ConversationHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from copy import deepcopy
import telegram.error

import core
from loggers import command_logger
from constants import Exceptions, Scopes
import database_functions
import job_queue_functions

RULES_ACCEPTED = range(1)


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
    inline_keyboard = [
        [InlineKeyboardButton("Ho letto e accetto le regole 🖋",
                              callback_data="accept_rules " + str(update.effective_user.id))],
    ]

    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await context.bot.send_message(chat_id=update.effective_user.id,
                                   text=context.bot_data["user_joined_message_text"]
                                   .format(update.effective_user.full_name),
                                   parse_mode="MARKDOWN", reply_markup=keyboard_markup,
                                   link_preview_options=telegram.LinkPreviewOptions(is_disabled=True))
    return RULES_ACCEPTED


async def new_member_accepted_the_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == update.callback_query.data.split(" ")[1]:
        keyboard = [
            [InlineKeyboardButton(text="Vai al Canale ↗️", url="https://t.me/+FbR5I5YukVBmYTM0")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.approve_chat_join_request(chat_id=context.bot_data["group_chat_id"],
                                                    user_id=update.effective_user.id)
        await context.bot.edit_message_text(text="✅ *La tua richiesta è stata approvata*\n"
                                                 "Lo staff di A&I Mods ti dà il benvenuto."
                                                 "Grazie per averci scelto 😃",
                                            chat_id=update.effective_user.id,
                                            message_id=update.callback_query.message.message_id,
                                            reply_markup=reply_markup)
        return ConversationHandler.END


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

        reason = ('_' + ' '.join(context.args if message.text.startswith('/') else message.text.split(' ')[1:])
                  + '_') if (context.args or len(message.text.split(' ')) > 1) else '`no reason given`'
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

            message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                                     message_thread_id=(message.message_thread_id
                                                                        if message.message_thread_id
                                                                           in scopes.FORUM_SCOPE.topics else None),
                                                     text=text, parse_mode="MARKDOWN")

            context.job_queue.run_once(callback=job_queue_functions.scheduled_delete_message,
                                       data={"chat_id": context.bot_data["group_chat_id"],
                                             "message_id": message.id},
                                       when=60)

            try:
                await database_functions.add_to_table(table_name='deleted_messages', content=update)
            except Exceptions.DatabaseException as e:
                command_logger.error(f'Something went wrong while operating with database: {e.error_message}')
    else:
        message = await context.bot.send_message(chat_id=context.bot_data["group_chat_id"],
                                                 message_thread_id=(message.message_thread_id
                                                                    if message.message_thread_id
                                                                       in scopes.FORUM_SCOPE.topics else None),
                                                 text="⚠️ Solo gli admin A&I Mods possono rimuovere i messaggi.")

        context.job_queue.run_once(callback=job_queue_functions.scheduled_delete_message,
                                   data={"chat_id": context.bot_data["group_chat_id"],
                                         "message_id": message.id},
                                   when=15)


# COMANDO LIMITAZIONE UTENTE
async def limit_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scopes = Scopes()
    message = deepcopy(update.message)
    if is_admin(update.effective_user.id, context):
        if update.message.text.split(" ")[0].endswith("limit"):
            user = await context.bot.get_chat_member(chat_id=context.bot_data["group_chat_id"],
                                                     user_id=update.effective_user.id)
            if user.status == user.MEMBER or user == user.RESTRICTED:
                pass
            else:
                if user.status == user.LEFT:
                    text = "⚠️ L'utente non è nel gruppo."
                elif user.status == user.ADMINISTRATOR or user.status == user.OWNER:
                    text = "⚠️ Non è consentito limitare gli altri admin."
                else:  # user.status == user.BANNED
                    text = "⚠️ L'utente è bannato."

                sent_message = await context.bot.send_message(chat_id=context.bot_data["group_chat_id"],
                                                              text=text,
                                                              message_thread_id=(message.message_thread_id
                                                                                 if message.message_thread_id
                                                                                 in scopes.FORUM_SCOPE.topics else None)
                                                              )

                context.job_queue.run_once(callback=job_queue_functions.scheduled_delete_message,
                                           data={"chat_id": context.bot_data["group_chat_id"],
                                                 "message_id": sent_message.id},
                                           when=60)
        else:
            # mute
            pass
    else:
        pass


def is_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    return str(user_id) in context.bot_data["admins"].keys()
