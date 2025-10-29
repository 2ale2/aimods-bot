import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.user_utils import is_admin

log = logger.getChild(__name__)


async def reset_user_conversation(update: Update, context: CustomContext):
    await safe_delete(update=update, context=context)
    if update.effective_chat.type != "private" or not await is_admin(user_id=update.effective_user.id, context=context):
        return

    if not len(context.args) or not context.args[0].isdigit():
        await update.effective_message.reply_text(text="⚠ Indica uno user ID", allow_sending_without_reply=True)
        return

    user_id = int(context.args[0])

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ <b>Richiesta di Reset Conversazionale</b>\n\n"
                 "<blockquote>ℹ <b>Informazioni</b> – Un admin ti ha inoltrato una richiesta per <b>resettare lo stato "
                 "della conversazione</b>. Questo tipicamente è necessario quando un utente riscontra dei problemi "
                 "nel flusso delle conversazioni. Se hai contattato un admin perché riscontri malfunzionamenti di "
                 "questa natura, accetta la richiesta, altrimenti ignorala.</blockquote>",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton(text="🔄 Accetta e Resetta", callback_data="reset_conversation"),
                    InlineKeyboardButton(text="🚮 Ignora", callback_data="close_menu")
                ]]
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        log.warning(f"Error while contacting the user: {e}")


async def reset_chat_data(update: Update, context: CustomContext):
    await safe_delete(update, context)
    if not await is_admin(user_id=update.effective_user.id, context=context):
        return

    if not len(context.args) or not context.args[0].isdigit():
        await update.effective_message.reply_text(text="⚠ Indica uno user ID", allow_sending_without_reply=True)
        return

    user_id = int(context.args[0])

    context.application.drop_chat_data(chat_id=user_id)
    log.info(f"Chat data for user {user_id} has been reset.")

    await update.effective_message.reply_text(
        text=f"ℹ Chat Data per <code>{user_id}</code> resettata.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🚮 Chiudi", callback_data="close_menu")]]),
        parse_mode=ParseMode.HTML,
        allow_sending_without_reply=True
    )


async def erase_callback_queries(update: Update, context: CustomContext):
    await safe_delete(update, context)
    if not await is_admin(user_id=update.effective_user.id, context=context):
        return

    context.bot.callback_data_cache.clear_callback_queries()

    await update.effective_message.reply_text(
        text="ℹ Callback Queries Erased",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🚮 Chiudi", callback_data="close_menu")]])
    )

    log.info(f"Callback Queries Erased by {update.effective_user.id}")


async def get_chat_data(update: Update, context: CustomContext):
    await safe_delete(update, context)

    await update.effective_message.reply_text(
        text=f"<code>{json.dumps(context.pydc.persistent.model_dump(), indent=4)}</code>\n\n"
             "🔹 Invia questo messaggio all'admin che te lo ha richiesto.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🚮 Chiudi", callback_data="close_menu")]]),
        allow_sending_without_reply=True
    )
