from __future__ import annotations

import html
from dataclasses import dataclass
from typing import List

from telegram import InlineKeyboardButton, Update, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.error import Forbidden, TelegramError, BadRequest

from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)


@dataclass
class ButtonItem:
    text: str
    callback_key: PathBuilder | str


@dataclass
class PanelConfig:
    base_path: PathBuilder
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
                key = button.callback_key
                subkeyboard.append(
                    InlineKeyboardButton(
                        text=button.text,
                        callback_data=key.build() if isinstance(key, PathBuilder) else str(key)
                    )
                )
            keyboard.append(subkeyboard)
        return keyboard

    async def render(
            self,
            update: Update,
            context: CustomContext,
            user_id: int = None,
            message_id: int = None,
            send: bool = False
    ):
        """Renderizza il pannello nel chat."""
        text = self.build_text()
        reply_markup = InlineKeyboardMarkup(self.build_keyboard())
        preview_options = LinkPreviewOptions(is_disabled=True)

        target_chat_id = user_id or update.effective_chat.id
        should_send_new = self.send or send or user_id is not None

        if should_send_new:
            try:
                await context.bot.send_message(
                    chat_id=target_chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=preview_options
                )
            except Forbidden:
                log.warning(f"Cannot perform send massage action: user {target_chat_id} blocked the bot")
            except TelegramError as e:
                log.error(f"Error sending panel to {target_chat_id}: {e}")
            return

        text_changed = html.unescape(update.effective_message.text_html_urled) != text

        if text_changed:
            success = await self._try_edit_text(
                context, update, text, reply_markup, preview_options, message_id
            )
            if success:
                return

            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=preview_options
                )
                return
            except TelegramError:
                pass

        try:
            await context.bot.edit_message_reply_markup(
                message_id=message_id or update.effective_message.message_id,
                chat_id=update.effective_chat.id,
                reply_markup=reply_markup
            )
        except TelegramError:
            pass

    async def _try_edit_text(
            self,
            context: CustomContext,
            update: Update,
            text: str,
            reply_markup: InlineKeyboardMarkup,
            preview_options: LinkPreviewOptions,
            message_id: int = None
    ) -> bool:
        """Tenta di modificare il testo del messaggio. Restituisce True se ha successo."""
        # Prova con message_id specifico
        if message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=preview_options
                )
                return True
            except BadRequest:
                pass

        # Prova con il messaggio corrente
        try:
            await update.effective_message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
                link_preview_options=preview_options
            )
            return True
        except BadRequest:
            pass

        return False
