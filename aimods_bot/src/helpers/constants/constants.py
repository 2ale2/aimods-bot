import re
import html
from typing import List, Optional
from dataclasses import dataclass

from telegram import InlineKeyboardButton, Update, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from aimods_bot.src.helpers.utils.file_utils import get_data_from_json

TOPICS = get_data_from_json("forum_topics")
pyro_instance = None

ERROR_MESSAGES = {
    "command_syntax_error": "⚠️ Warning\n\n▪️ Sintassi del comando non corretta.",
    "no_user_provided": "⚠️ Warning\n\n▪️ Se non rispondi ad un messaggio, devi indicare un utente.",
    "cannot_parse_user": "⚠️ Warning\n\n▪️ Non riesco a risolvere l'utente specificato, riprova.\n\n"
                      "🔍 Tipicamente significa che l'utente non è nel gruppo.",
    "username_404": "⚠️ Warning\n\n▪️ Lo username {} non esiste.",
    "user_not_in_group": "⚠️ Warning\n\n▪️ L'utente non è nel gruppo.",
    "user_banned": "⚠️ Warning\n\n▪️ L'utente è bannato.",
}

PUNISHMENT_EMOJIS = {
        "ban": "🚫",
        "kick": "🥊",
        "mute": "🔒",
        "warn": "⚠️"
}


_commands = get_data_from_json("commands")

echo_pattern = re.compile(_commands["echo"]["pattern"], re.IGNORECASE)


@dataclass
class DisplayItem:
    display_icon: str
    display_name: str
    target_description: str


MODERATION_DISPLAY_ITEMS = {
    "antispam": DisplayItem("📨", "Anti-Spam", "a chi spamma"),
    "antiflood": DisplayItem("🌊", "Anti-Flood", "a chi fa flooding")
}


@dataclass
class ButtonItem:
    text: str
    callback_key: Optional[str]


@dataclass
class PanelConfig:
    base_path: str
    text: str
    keyboard: List[List[ButtonItem]]


class Panel:
    """Classe base per generare pannelli di menu con testo e tastiera inline."""
    def __init__(self, config: PanelConfig, send=False):
        self.base_path = config.base_path
        self.text = config.text
        self.keyboard = config.keyboard
        self.send = send

    def build_text(self) -> str:
        """Costruisce il testo del messaggio."""
        return self.text

    def build_keyboard(self) -> List[List[InlineKeyboardButton]]:
        """Costruisce la tastiera inline."""
        keyboard = []
        for sublist in self.keyboard:
            subkeyboard = []
            for button in sublist:
               subkeyboard.append(
                   InlineKeyboardButton(
                       text=button.text,
                       callback_data=self.generate_path(button.callback_key)
                   )
               )
            keyboard.append(subkeyboard)
        return keyboard

    def generate_path(self, subpath: Optional[str]) -> str:
        """Genera il percorso per il callback_data."""
        if not subpath:
            s = self.base_path.split("/")
            return f"{'/'.join(s[:-1])}"
        if not self.base_path:
            return subpath
        return f"{self.base_path}/{subpath}"

    async def render(self, update: Update, context: CallbackContext):
        """Renderizza il pannello nel chat."""
        if self.send:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=self.build_text(),
                reply_markup=InlineKeyboardMarkup(self.build_keyboard()),
                parse_mode=ParseMode.HTML
            )
        else:
            text = self.build_text()
            if html.unescape(update.effective_message.text_html_urled) != text:
                await update.effective_message.edit_text(
                    text=self.build_text(),
                    reply_markup=InlineKeyboardMarkup(self.build_keyboard()),
                    parse_mode=ParseMode.HTML
                )
