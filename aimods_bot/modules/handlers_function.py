import copy
import os
from copy import deepcopy

import telegram.error
from telegram.constants import ChatMemberStatus
from telegram.ext import ConversationHandler
from datetime import datetime, timedelta

from constants import Scopes
from utils import *

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
        await delete_effective_message(update, context)

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

    if await user_in_chat(user_id=update.effective_user.id, chat_id=context.bot_data["group_chat_id"], context=context):
        keyboard = [
            # link statico alla chat https://t.me/c/<group_chat_id>
            [InlineKeyboardButton(text="Vai alla Chat ↗️", url="https://t.me/+FbR5I5YukVBmYTM0")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=update.effective_user.id, text="❔ Sei già all'interno del gruppo.\n\n"
                                                                              "Usa /rules per leggere le regole.",
                                       reply_markup=reply_markup)
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
        return ConversationHandler.END

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
                                   'chat_id': update.effective_chat.id,
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
    if job := context.job_queue.get_jobs_by_name(f'captcha_failed_{update.effective_user.id}'):
        job[0].schedule_removal()

    if str(update.effective_user.id) == update.callback_query.data.split(" ")[1]:
        await context.bot.delete_message(chat_id=update.effective_user.id,
                                         message_id=update.effective_message.message_id)

        await context.bot.approve_chat_join_request(chat_id=context.bot_data["group_chat_id"],
                                                    user_id=update.effective_user.id)

        keyboard = [
            [InlineKeyboardButton(text="Vai al Gruppo ↗️", url="https://t.me/+FbR5I5YukVBmYTM0")]
        ]

        await send_action_message_after(
            update=update,
            context=context,
            text="✅ <b>La tua richiesta è stata approvata</b>\n\nLo staff di A&I Mods ti dà il benvenuto. "
                 "Grazie per averci scelto 😃",
            additional_job_data={
                "reply_markup": InlineKeyboardMarkup(keyboard)
            }
        )

        # await context.bot.send_chat_action(chat_id=update.effective_user.id, action=ChatAction.TYPING)
        # keyboard = [
        #     [InlineKeyboardButton(text="Vai al Gruppo ↗️", url="https://t.me/+FbR5I5YukVBmYTM0")]
        # ]
        # reply_markup = InlineKeyboardMarkup(keyboard)
        #
        # data = {
        #     "text": "✅ <b>La tua richiesta è stata approvata</b>\n\nLo staff di A&I Mods ti dà il benvenuto. "
        #             "Grazie per averci scelto 😃",
        #     "chat_id": update.effective_user.id,
        #     "reply_markup": reply_markup
        # }
        # context.job_queue.run_once(callback=job_queue_functions.scheduled_send_message, data=data, when=1)
        return ConversationHandler.END

    # if job := context.job_queue.get_jobs_by_name(f'captcha_failed_{update.effective_user.id}'):
    #     job[0].schedule_removal()
    #
    # if str(update.effective_user.id) == update.callback_query.data.split(" ")[1]: keyboard = [ [
    # InlineKeyboardButton(text="Vai al Gruppo ↗️", url="https://t.me/+FbR5I5YukVBmYTM0")] ] reply_markup =
    # InlineKeyboardMarkup(keyboard) await context.bot.approve_chat_join_request(chat_id=context.bot_data[
    # "group_chat_id"], user_id=update.effective_user.id) del context.user_data["group_join_request"] await
    # context.bot.edit_message_text(message_id=update.effective_message.message_id, chat_id=update.effective_user.id,
    # text="✅ <b>La tua richiesta è stata approvata</b>\n\nLo staff di A&I Mods " "ti dà il benvenuto. Grazie per
    # averci scelto 😃", parse_mode="HTML", reply_markup=reply_markup) return ConversationHandler.END


# }


# COMANDO RIMOZIONE MESSAGGI
async def delete_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = copy.deepcopy(update.effective_message.reply_to_message)

    await delete_effective_message(update, context)

    if not await is_admin(update.effective_user.id, context):
        await job_queue_functions.send_temporary_message(
            update=update,
            context=context,
            text="⚠️ Solo gli admin possono eseguire questa azione.",
            delay_before=2,  # per la chat action
            delay_delete=10
        )
        return

    if message.reply_to_message is None or message.reply_to_message.forum_topic_created is not None:
        await send_private_alert(
            update=update,
            context=context,
            text="ℹ️ INFO\n\nPer poter eliminare un messaggio, selezionalo rispondendovi.",
            delay=1
        )
        return

    if datetime.now((message_date := message.reply_to_message.date).tzinfo) - message_date > timedelta(hours=48):
        await send_private_alert(
            update=update,
            context=context,
            text="⚠️ Warning\n\nIl messaggio non può essere rimosso, perché è stato mandato più di 48 ore fa.",
            delay=1
        )
        return

    if context.args:
        reason = ' '.join(context.args)
    else:
        reason = "<code>no reason given</code>"

    try:
        await update.effective_message.reply_to_message.delete()
    except telegram.error.BadRequest as e:
        bot_logger.error(f"Errore nella rimozione di un messaggio: {e}")
        await send_private_alert(
            update=update,
            context=context,
            text="❌ Error\n\nIl messaggio non può essere rimosso a causa di un errore. Controlla i log dei comandi.",
            delay=1
        )
        return
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
        )


async def send_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id,
                                         message_id=update.effective_message.id)
    except telegram.error.BadRequest:
        pass

    message = await context.bot.send_message(chat_id=update.effective_chat.id,
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


async def is_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    return str(user_id) in context.bot_data["admins"].keys()


async def user_in_chat(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # tells if user_id is already in chat_id
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
