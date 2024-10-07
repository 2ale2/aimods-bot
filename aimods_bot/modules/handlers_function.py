from copy import deepcopy
from datetime import datetime, timedelta

import telegram.error
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes, ConversationHandler, CallbackContext

import core
import database_functions
import job_queue_functions
from constants import Exceptions, Scopes
from loggers import command_logger, db_logger

RULES_ACCEPTED = 0


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


# {DOPPIA VERIFICA
async def new_member_joined_forum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message is not None:
        try:
            await context.bot.delete_message(chat_id=update.effective_user.id,
                                             message_id=update.effective_message.message_id)
        except telegram.error.BadRequest:
            pass

    if await user_in_chat(user_id=update.effective_user.id, chat_id=context.bot_data["group_chat_id"], context=context):
        keyboard = [
            [InlineKeyboardButton(text="Vai alla Chat ↗️", url="https://t.me/+FbR5I5YukVBmYTM0")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=update.effective_user.id, text="❔ Sei già all'interno del gruppo.\n\n"
                                                                              "Usa /rules per leggere le regole.",
                                       reply_markup=reply_markup)
        return ConversationHandler.END

    if await user_is_banned(user_id=update.effective_user.id,
                            chat_id=context.bot_data["group_chat_id"],
                            context=context):
        message = await context.bot.send_message(chat_id=update.effective_user.id, text="❌ Il tuo ID è stato "
                                                                                        "<b>bannato</b>.\n\n"
                                                                                        "Non puoi unirti al gruppo.",
                                                 parse_mode="HTML")
        context.job_queue.run_once(callback=job_queue_functions.scheduled_delete_message, when=10,
                                   data={"message_id": message.message_id, "chat_id": update.effective_user.id})
        return ConversationHandler.END

    if update.chat_join_request and "group_join_request" not in context.user_data:
        context.user_data["group_join_request"] = True

    if "group_join_request" not in context.user_data:
        keyboard = [
            [InlineKeyboardButton(text="Chiedi l'accesso ➕", url="https://t.me/+FbR5I5YukVBmYTM0")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text='⚠️ Devi prima chiedere di accedere al gruppo tramite link di invito.',
                                       reply_markup=reply_markup)
        return

    # codice eseguito se "group_join_request" è in context.user_data

    inline_keyboard = [
        [InlineKeyboardButton("Ho letto e accetto le regole 🖋",
                              callback_data="accept_rules " + str(update.effective_user.id))],
    ]

    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    message = await context.bot.send_message(chat_id=update.effective_user.id,
                                             text=context.bot_data["user_joined_message_text"]
                                             .format(update.effective_user.full_name),
                                             parse_mode="HTML", reply_markup=keyboard_markup,
                                             link_preview_options=telegram.LinkPreviewOptions(is_disabled=True))

    context.job_queue.run_once(callback=job_queue_functions.scheduled_edit_message,
                               data={
                                   'chat_id': update.effective_user.id,
                                   'message_id': message.message_id,
                                   'text': '⚠️ <b>Non hai completato la verifica</b>.\n\n'
                                           'Per far accettare la tua richiesta di accesso al gruppo, puoi fornire il '
                                           'comando /request.'
                               },
                               when=600,  # tempo massimo di accettazione delle regole
                               name=f'captcha_failed_{update.effective_user.id}')
    return RULES_ACCEPTED


async def new_member_accepted_the_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    L'utente ha accettato le regole. La richiesta viene approvata e l'utente è indirizzato al gruppo.

    :param update: Update: l'Update da gestire
    :param context: ContextTypes: il contesto dell'istanza di Application
    :return: ConversationHandler.END
    """
    # if job := context.job_queue.get_jobs_by_name(f'captcha_failed_{update.effective_user.id}'):
    #     job[0].schedule_removal()
    #
    # if str(update.effective_user.id) == update.callback_query.data.split(" ")[1]:
    #     await context.bot.delete_message(chat_id=update.effective_user.id,
    #                                      message_id=update.effective_message.message_id)
    #     await context.bot.send_chat_action(chat_id=update.effective_user.id, action=ChatAction.TYPING)
    #     keyboard = [
    #         [InlineKeyboardButton(text="Vai al Gruppo ↗️", url="https://t.me/+FbR5I5YukVBmYTM0")]
    #     ]
    #     reply_markup = InlineKeyboardMarkup(keyboard)
    #     await context.bot.approve_chat_join_request(chat_id=context.bot_data["group_chat_id"],
    #                                                 user_id=update.effective_user.id)
    #     data = {
    #         "text": "✅ <b>La tua richiesta è stata approvata</b>\n\nLo staff di A&I Mods ti dà il benvenuto. "
    #                 "Grazie per averci scelto 😃",
    #         "chat_id": update.effective_user.id,
    #         "reply_markup": reply_markup
    #     }
    #     context.job_queue.run_once(callback=job_queue_functions.scheduled_send_message, data=data, when=1)
    #     return ConversationHandler.END

    if job := context.job_queue.get_jobs_by_name(f'captcha_failed_{update.effective_user.id}'):
        job[0].schedule_removal()

    if str(update.effective_user.id) == update.callback_query.data.split(" ")[1]:
        keyboard = [
            [InlineKeyboardButton(text="Vai al Gruppo ↗️", url="https://t.me/+FbR5I5YukVBmYTM0")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.approve_chat_join_request(chat_id=context.bot_data["group_chat_id"],
                                                    user_id=update.effective_user.id)
        del context.user_data["group_join_request"]
        await context.bot.edit_message_text(message_id=update.effective_message.message_id,
                                            chat_id=update.effective_user.id,
                                            text="✅ <b>La tua richiesta è stata approvata</b>\n\nLo staff di A&I Mods "
                                                 "ti dà il benvenuto. Grazie per averci scelto 😃",
                                            parse_mode="HTML",
                                            reply_markup=reply_markup)
        return ConversationHandler.END


# }


# COMANDO RIMOZIONE MESSAGGI
async def delete_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Rimuove il messaggio selezionato tramite comando.
    :param update: Update: l'Update da gestire
    :param context: ContextTypes: il contesto dell'istanza di Application
    :return:
    """
    scopes = Scopes()
    message = deepcopy(update.message)

    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id,
                                         message_id=update.message.message_id)
    except telegram.error.TelegramError:
        pass

    if is_admin(update.effective_user.id, context):
        if message.reply_to_message is None or message.reply_to_message.forum_topic_created is not None:
            reply_markup = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(text='Open It Privately 💬',
                                          callback_data=f'open_private_alert {update.effective_user.id}')]
                ]
            )
            admin_identifier = (update.effective_user.username or
                                update.message.reply_to_message.from_user.id)
            text = f'🔐 Message for [{update.effective_user.first_name}](tg;//user?=id={admin_identifier})' \
                if admin_identifier.isnumeric() else f'🔐 Message for @{update.effective_user.username}'

            await context.bot.send_message(chat_id=context.bot_data["group_chat_id"],
                                           message_thread_id=(message.message_thread_id
                                                              if message.message_thread_id
                                                                 in scopes.FORUM_SCOPE.topics else None),
                                           text=text,
                                           reply_markup=reply_markup)
            return

        if datetime.now(message.reply_to_message.date.tzinfo) - message.reply_to_message.date > timedelta(hours=48):
            message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                                     message_thread_id=update.effective_message.message_thread_id,
                                                     text="⚠️ Non posso rimuovere il messaggio perché è stato mandato"
                                                          " più di 48 ore fa.\n\n💡 Puoi rimuoverlo manualmente, "
                                                          "ma non verrà aggiunto .")
            core.command_logger.error("Message cannot be deleted from bot cause it was sent more than 48h ago.")
            context.job_queue.run_once(callback=job_queue_functions.scheduled_delete_message,
                                       data={"chat_id": context.bot_data["group_chat_id"],
                                             "message_id": message.id},
                                       when=15)
            return

        user_identifier = (update.message.reply_to_message.from_user.username or
                           update.message.reply_to_message.from_user.id)

        reason = ('_' + ' '.join(context.args if message.text.startswith('/') else message.text.split(' ')[1:])
                  + '_') if len(message.text.split(' ')) > 1 else '`no reason given`'
        try:
            await database_functions.add_to_table(table_name='deleted_messages', content=update)
            await context.bot.delete_message(chat_id=context.bot_data["group_chat_id"],
                                             message_id=message.reply_to_message.message_id)
        except telegram.error.TelegramError as e:
            core.command_logger.error(f"Message cannot be deleted {e}")
        except Exceptions.DatabaseException as e:
            command_logger.error(f'Something went wrong while operating with database: {e.error_message}')
            db_logger.error(f'Something went wrong while operating with database: {e.error_message}')
        else:
            if isinstance(user_identifier, int):
                text = (f'♻️ Message sent by '
                        f'[{update.message.reply_to_message.from_user.first_name}](tg://user?id={user_identifier})'
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


async def alert_del_message_not_selected(update: Update, context: CallbackContext):
    """
    Invia un messaggio privato all'utente specificato, all'interno del gruppo.
    :param update: Update: l'Update da gestire
    :param context: ContextTypes: il contesto dell'istanza di Application
    :return:
    """
    if not update.callback_query.data.endswith(str(update.effective_user.id)):
        return

    await context.bot.answer_callback_query(callback_query_id=update.callback_query.id,
                                            text='ℹ️ INFO\n\n'
                                                 'Per poter eliminare un messaggio, selezionalo rispondendovi.',
                                            show_alert=True)
    await context.bot.delete_message(chat_id=context.bot_data["group_chat_id"],
                                     message_id=update.effective_message.id)


async def send_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.delete_message(chat_id=update.effective_user.id,
                                         message_id=update.effective_message.id)
    except telegram.error.BadRequest:
        pass

    message = await context.bot.send_message(chat_id=update.effective_user.id,
                                             text=context.bot_data["rules_text"],
                                             parse_mode="HTML")
    keyboard = [
        [InlineKeyboardButton(text="Close 📖", callback_data=f"close {message.id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.edit_message_reply_markup(chat_id=update.effective_user.id, message_id=message.message_id,
                                                reply_markup=reply_markup)


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


async def user_in_chat(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    res = await context.bot.get_chat_member(user_id=user_id, chat_id=chat_id)
    if res.status is ChatMemberStatus.MEMBER or res.status is ChatMemberStatus.ADMINISTRATOR:
        return True
    return False


async def user_is_banned(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    res = await context.bot.get_chat_member(user_id=user_id, chat_id=chat_id)
    if res.status is ChatMemberStatus.BANNED:
        return True
    return False


async def callback_close_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Deletes the message by gathering its id from given call back data
    :param update: Update: l'Update da gestire
    :param context: ContextTypes: il contesto dell'istanza di Application
    :return:
    """
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id,
                                         message_id=update.callback_query.data.split(" ")[1])
    except telegram.error.BadRequest:
        pass
