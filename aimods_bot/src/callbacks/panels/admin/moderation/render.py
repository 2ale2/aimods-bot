from typing import Optional, List

from telegram import InlineKeyboardButton, Update, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode


def _build_text() -> str:
    text = ("♟ <b>Impostazioni – Moderazione Gruppo e Canale</b>\n\n"
            "▫️ Da questo menù puoi regolare le impostazioni di moderazione del gruppo e del canale di "
            "<i>AIMods</i>.\n\n🔹 Scegli un'opzione.")
    return text


def _build_keyboard() -> List[List[InlineKeyboardButton]]:
    keyboard = [
        [InlineKeyboardButton(text="🔐 Sicurezza e Filtri", callback_data=_generate_path("security_filters"))],
        [InlineKeyboardButton(text="⚠️ Moderazione Utenti", callback_data=_generate_path("user_moderation"))],
        [InlineKeyboardButton(text="🎞 Messaggi e Contenuti", callback_data=_generate_path("media_contents"))],
        [InlineKeyboardButton(text="👥 Gestione Community", callback_data=_generate_path("community_settings"))],
        [InlineKeyboardButton(text="🏠 Home", callback_data=_generate_path(None))]
    ]
    return keyboard


def _generate_path(s: Optional[str]) -> str:
    if not s:
        return "moderation/"
    return f"moderation/{s}"


async def render_panel(update: Update, context: CallbackContext):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=_build_text(),
        reply_markup=InlineKeyboardMarkup(_build_keyboard()),
        parse_mode=ParseMode.HTML
    )
