from __future__ import annotations

import html
from dataclasses import dataclass
from typing import List

from telegram import InlineKeyboardButton, Update, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.error import Forbidden, TelegramError, BadRequest

from aimods_bot.src.helpers.constants.path_navigation import AdminRoute, UserRoute
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.infra.log import logger
from aimods_bot.src.infra.telegram.auth import is_admin

log = logger.getChild(__name__)


def _is_not_modified(error: BadRequest) -> bool:
    """
    Riconosce il `BadRequest` che Telegram alza quando testo e tastiera sono già
    quelli richiesti.

    Magic string, ma è l'unico modo che la Bot API offre per distinguere il caso.
    Senza questo, `_try_edit_text` ritorna False, `Panel.render` cade sul
    `send_message` di fallback e compare un pannello nuovo sotto quello vecchio.
    """
    return "not modified" in str(error).lower()


@dataclass
class ButtonItem:
    text: str
    callback_key: PathBuilder | str = ""
    # Se valorizzato il bottone apre un link e `callback_key` viene ignorato:
    # Telegram non accetta url e callback_data sullo stesso bottone.
    url: str | None = None


@dataclass
class PanelConfig:
    text: str
    keyboard: List[List[ButtonItem]]


class Panel:
    """Classe base per generare pannelli di menu con testo e tastiera inline."""

    def __init__(self, config: PanelConfig, send=False):
        self.text = config.text
        self.keyboard = config.keyboard
        self.send = send

    def build_text(self) -> str:
        """Costruisce il testo del messaggio."""
        return self.text

    def build_keyboard(self, fallback: str) -> List[List[InlineKeyboardButton]]:
        """Costruisce la tastiera inline."""
        keyboard = []
        for sublist in self.keyboard:
            subkeyboard = []
            for button in sublist:
                if button.url:
                    subkeyboard.append(InlineKeyboardButton(text=button.text, url=button.url))
                    continue
                key = button.callback_key
                data = key.build() if isinstance(key, PathBuilder) else str(key)
                if not data:
                    log.debug(f"Button '{button.text}' without callback_data, using {fallback!r}")
                    data = fallback
                subkeyboard.append(InlineKeyboardButton(text=button.text, callback_data=data))
            keyboard.append(subkeyboard)
        return keyboard

    async def render(
            self,
            update: Update,
            context: CustomContext,
            user_id: int = None,
            message_id: int = None,
            send: bool = False
    ) -> int | None:
        """Renderizza il pannello nel chat. Ritorna True se message_id != None e se la modifica va a buon fine."""
        text = self.build_text()
        target_chat_id = user_id or update.effective_chat.id
        fallback = str(
            AdminRoute.ROOT if is_admin(
                user_id=target_chat_id,
                context=context
            ) else UserRoute.ROOT
        )
        reply_markup = InlineKeyboardMarkup(self.build_keyboard(fallback))
        preview_options = LinkPreviewOptions(is_disabled=True)

        should_send_new = self.send or send or user_id is not None

        if should_send_new:
            try:
                message = await context.bot.send_message(
                    chat_id=target_chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=preview_options
                )
                return message.id
            except Forbidden:
                log.error(f"Cannot perform send massage action: user {target_chat_id} blocked the bot")
            except TelegramError as e:
                log.error(f"Error sending panel to {target_chat_id}: {e}")
            return

        text_changed = html.unescape(update.effective_message.text_html_urled) != text

        if text_changed:
            success = await self._try_edit_text(
                context=context,
                update=update,
                text=text,
                reply_markup=reply_markup,
                preview_options=preview_options,
                message_id=message_id
            )
            if success:
                return message_id

            try:
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=preview_options
                )
                return message.id
            except TelegramError as e:
                log.error(f"Something went wrong while trying to sending a message: {e}")
                return

        try:
            message = await context.bot.edit_message_reply_markup(
                message_id=message_id or update.effective_message.message_id,
                chat_id=update.effective_chat.id,
                reply_markup=reply_markup
            )
            if not isinstance(message, bool):
                return message.id
        except TelegramError as e:
            log.error(f"Error in trying editing message: {e}")

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
            except BadRequest as e:
                if _is_not_modified(e):
                    return True
                log.debug(f"Error in trying editing message: {e}")

        # Prova con il messaggio corrente
        try:
            await update.effective_message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
                link_preview_options=preview_options
            )
            return True
        except BadRequest as e:
            if _is_not_modified(e):
                return True
            log.warning(f"Error in trying editing message: {e}")

        return False
