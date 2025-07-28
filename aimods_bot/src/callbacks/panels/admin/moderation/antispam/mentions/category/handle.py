from typing import Literal

from pyrogram.types import InlineKeyboardButton
from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ContextTypes

from aimods_bot.src.core.config_accessor import set_value, get_value
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.models import JobData
from aimods_bot.src.helpers.job_queue import send_action_message_after
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import make_temp_file
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete

log = logger.getChild("antispam_mention_category")

map_to_word = {
        "user": "Utenti",
        "group": "Gruppi",
        "channel": "Canali",
        "bot": "Bot"
    }


async def set_category_toggle(update: Update, context: CallbackContext, category: str, value: bool):
    set_value(context=context, path=f"moderation.antispam.mention.{category}", value=value)
    log.info(f"Antispam: controllo menzioni categoria {category} modificato in '{value}' da {update.effective_user.id}")


async def view_whitelist(update: Update, context: CallbackContext, category: str):
    l = get_value(context=context, path=f"moderation.antispam.mention.whitelist.{category}")
    word = map_to_word[category]
    if await _handle_if_list_empty(update=update, context=context, category=category, l=l):
        return PCS.ADMIN_CONVERSATION

    filename = await make_temp_file(content=l)

    if not filename:
        text = "❌ Errore durante la creazione del file di testo. Contatta l'admin."
        keyboard = [[InlineKeyboardButton(
            text="🔙 Indietro",
            callback_data=f"moderation/security_filters/antispam/mention/{category}/whitelist")
        ]]

        await update.effective_message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

        return PCS.ADMIN_CONVERSATION

    await send_action_message_after(
        update=update,
        context=context,
        text=f"📄 Ecco la lista di identificativi aggiunti alla Whitelist per "
             f"{'i' if category != 'user' else 'gli'} {word}.",
        additional_job_data=JobData(
            files=filename,
            send_as_document=True,
            delete_after_sending=True,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🚮 Chiudi", callback_data="close")]])
        )
    )

    return PCS.ADMIN_CONVERSATION


async def edit_whitelist(update: Update, context: CallbackContext, category: str, action: Literal["add", "remove"]):
    l = get_value(context=context, path=f"moderation.antispam.mention.whitelist.{category}")
    word = map_to_word[category]

    if await _handle_if_list_empty(update=update, context=context, category=category, l=l) and action == "remove":
        return PCS.ADMIN_CONVERSATION

    if action == "add":
        text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
                f"↦ 💬 <i>Blocco Menzioni</i> – <i>Whitelist Menzione {word}</i>\n\n"
                f"🔹 Indica gli ID {'degli' if category == 'user' else 'dei'} {word} da aggiungere alla Whitelist.")
    else:  # "remove"
        text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
                f"↦ 💬 <i>Blocco Menzioni</i> – <i>Whitelist Menzione {word}</i>\n\n"
                f"🔍 Ecco gli elementi presenti:\n\n")
        for el in l:
            text += f"     ▪<code>{el}</code>\n"
        text += f"\n🔹 Scrivi gli ID da rimuovere dalla Whitelist."

    context.chat_data["editing_mention_category_whitelist"] = {
        "action": action,
        "message_id": update.effective_message.message_id,
    }

    await update.effective_message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(
                text="🔙 Indietro",
                callback_data=f"moderation/security_filters/antispam/mention/{category}/whitelist"
            )]]),
        parse_mode=ParseMode.HTML
    )

    return PCS.EDIT_ANTISPAM_MENTION_CATEGORY_WHITELIST


async def _handle_if_list_empty(update: Update, context: CallbackContext, category: str, l: str) -> bool:
    word = map_to_word[category]

    if len(l) == 0:
        text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
                f"↦ 💬 <i>Blocco Menzioni</i> – <i>Whitelist Menzione {word}</i>\n\n"
                f"0️⃣ <b>La Whitelist è attualmente vuota</b>.")
        keyboard = [[
            InlineKeyboardButton(
                text="🔙 Indietro",
                callback_data=f"moderation/security_filters/antispam/mention/{category}/whitelist"
            )]]

        await update.effective_message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return True
    return False


async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_delete(update=update, context=context)
    action = context.chat_data["editing_mention_category_whitelist"]["action"]
    message_id = context.chat_data["editing_mention_category_whitelist"]["message_id"]

    # Logica verifica input
