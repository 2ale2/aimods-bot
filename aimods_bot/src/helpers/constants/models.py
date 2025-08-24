import html

from dataclasses import dataclass
from typing import Optional, List, Union, Literal, NamedTuple
from enum import Enum

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMedia, ReplyParameters
from telegram.constants import ParseMode
from telegram.ext import CallbackContext


@dataclass
class JobData:
    files: Union[str, InputMedia, List[Union[str, InputMedia]]] = None
    message_id: Optional[int | telegram.Message] = None
    send_as_document: bool = False
    delete_after_sending: bool = False
    thread_id: Optional[int] = None
    reply_markup: Optional[InlineKeyboardMarkup] = None
    reply_parameters: Optional[ReplyParameters] = None


@dataclass
class ScheduledJobData:
    chat_id: int
    text: Optional[str]
    additional_data: Optional[JobData] = None


@dataclass
class MediaItem:
    item: Union[str, InputMedia]
    type: Literal["document", "photo", "audio", "video", "gif"]
    as_doc: bool


@dataclass
class DisplayItem:
    display_icon: str
    display_name: str
    target_description: str


@dataclass
class ButtonItem:
    text: str
    callback_key: Optional[str]


@dataclass
class PanelConfig:
    base_path: str
    text: str
    keyboard: List[List[ButtonItem]]


@dataclass
class CanUserRequest:
    yn: bool
    reason: Optional[str]


class Platform(Enum):
    ANDROID = "android"
    IOS = "ios"
    WINDOWS = "windows"
    MACOS = "macos"


class RequestField(Enum):
    NAME = "name"
    LINK = "link"
    VERSION = "version"
    FUNCTIONALITIES = "functionalities"
    STEAMTOOLS = "steamtools"


class WindowsCategory(Enum):
    GAME = "game"
    DAW = "daw"
    ADOBE = "adobe"
    SOFTWARE = "software"


class AndroidCategory(Enum):
    APP = "app"


class IOSCategory(Enum):
    APP = "app"


class MacOSCategory(Enum):
    SOFTWARE = "software"
    DAW = "daw"


Category = Union[WindowsCategory, AndroidCategory, IOSCategory, MacOSCategory]


class MessageTemplate(NamedTuple):
    app: str
    game: str
    daw: str
    software: str


@dataclass
class RequestStatus(Enum):
    PENDING = "pending"
    EXAMINING = "examining"
    TESTING = "testing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


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

    async def render(self, update: Update, context: CallbackContext, message_id: int = None, send: bool = False):
        """Renderizza il pannello nel chat."""
        text = self.build_text()
        reply_markup = InlineKeyboardMarkup(self.build_keyboard())
        if self.send or send:
            await context.bot.send_message(
                chat_id=message_id or update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        else:
            if html.unescape(update.effective_message.text_html_urled) != text:
                if message_id:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=message_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await update.effective_message.edit_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
            try:
                await update.effective_message.edit_reply_markup(
                    reply_markup=reply_markup
                )
            except telegram.error:
                pass
