from __future__ import annotations

import html
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Union, Literal, NamedTuple, cast, Type, Tuple, Dict

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMedia, ReplyParameters, LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.error import Forbidden, BadRequest, TelegramError

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import Platform, WindowsCategory, AndroidCategory, IOSCategory, \
    MacOSCategory, Category
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("models")

PlatformStr = Literal["android", "ios", "windows", "macos"]
WinCatStr = Literal["game", "daw", "adobe", "software"]
AndroidCatStr = Literal["app"]
IOSCatStr = Literal["app"]
MacOSCatStr = Literal["software", "daw"]
CatStr = WinCatStr | AndroidCatStr | IOSCatStr | MacOSCatStr
StatusStr = Literal["pending", "examining", "testing", "completed", "rejected", "cancelled"]


@dataclass
class JobData:
    files: Union[str, InputMedia, List[Union[str, InputMedia]]] = None
    message_id: Optional[int | telegram.Message] = None
    send_as_document: bool = False
    delete_after_sending: bool = False
    thread_id: Optional[int] = None
    reply_markup: Optional[InlineKeyboardMarkup] = None
    reply_parameters: Optional[ReplyParameters] = None
    delete_after: Optional[int] = None


@dataclass
class ScheduledJobData:
    chat_id: int
    text: Optional[str] = None
    additional_data: Optional[JobData] = None


@dataclass
class MediaItem:
    item: Union[str, InputMedia]
    type: Literal["document", "photo", "audio", "video", "gif"]
    as_doc: bool


@dataclass
class ButtonItem:
    text: str
    callback_key: Optional[str]
    override_path_generation: bool = False


@dataclass
class PanelConfig:
    base_path: str
    text: str
    keyboard: List[List[ButtonItem]]


@dataclass
class CanUserRequest:
    yn: bool
    reason: Optional[str]


class MessageTemplate(NamedTuple):
    app: str
    game: str
    daw: str
    software: str


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
                if not button.override_path_generation:
                    c_data = self.generate_path(button.callback_key)
                else:  # La callback key è il percorso completo
                    c_data = button.callback_key
                subkeyboard.append(
                    InlineKeyboardButton(
                        text=button.text,
                        callback_data=c_data
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


_PLATFORM_CATEGORY_MAP: Dict[Platform, Tuple[Type[Enum], ...]] = {
    Platform.WINDOWS: (WindowsCategory,),
    Platform.ANDROID: (AndroidCategory,),
    Platform.IOS: (IOSCategory,),
    Platform.MACOS: (MacOSCategory,)
}

def _parse_category(value: str, platform: Platform) -> Category:
    for enum_cls in _PLATFORM_CATEGORY_MAP.get(platform):
        try:
            return cast(Category, enum_cls(value))
        except ValueError:
            continue
    raise ValueError(f"category='{value}' non valida per platform='{platform.value}'")
