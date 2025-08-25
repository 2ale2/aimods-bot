import html
import json

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Union, Literal, NamedTuple, Dict, Any
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


@dataclass
class RequestData:
    platform: Optional['Platform'] = None
    category: Optional['Category'] = None
    user_id: Optional[int] = None
    status: Optional['RequestStatus'] = None
    issued_at: Optional[datetime] = None
    name: Optional[str] = None
    link: Optional[str] = None
    version: Optional[str] = None
    functionalities: Optional[str] = None
    steamtools: Optional[bool] = None
    requesting: Optional['RequestField'] = None
    editing: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for k, v in asdict(self).items():
            if k not in ('requesting', 'editing'):
                if isinstance(v, Enum):
                    result[k] = v.value
                elif isinstance(v, datetime):
                    result[k] = v.isoformat()
                elif v is not None:
                    result[k] = v
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RequestData':
        data_copy = data.copy()

        if 'platform' in data_copy and data_copy['platform'] is not None:
            data_copy['platform'] = Platform(data_copy['platform'])

        if 'category' in data_copy and data_copy['category'] is not None:
            data_copy['category'] = Category(data_copy['category'])

        if 'status' in data_copy and data_copy['status'] is not None:
            # noinspection PyArgumentList
            data_copy['status'] = RequestStatus(data_copy['status'])

        if 'requesting' in data_copy and data_copy['requesting'] is not None:
            data_copy['requesting'] = RequestField(data_copy['requesting'])

        if 'issued_at' in data_copy and data_copy['issued_at'] is not None:
            data_copy['issued_at'] = datetime.fromisoformat(data_copy['issued_at'])

        return cls(**data_copy)

    @classmethod
    def from_json(cls, json_str: str) -> 'RequestData':
        return cls.from_dict(json.loads(json_str))

    def get_category(self) -> Optional[Category]:
        """Determina la categoria per piattaforme Windows"""
        return self.category

    def get_platform(self) -> Platform:
        """Ritorna la piattaforma"""
        return self.platform
