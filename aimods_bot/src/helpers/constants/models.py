from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Union, Literal, NamedTuple, TypedDict, NotRequired, Required, cast, Iterable, Type

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMedia, ReplyParameters
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from aimods_bot.src.helpers.constants.constants import (PlatformStr, WinCatStr, AndroidCatStr, IOSCatStr,
                                                        MacOSCatStr, StatusStr)


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


def _iter_category_enums_for_platform(p: Platform) -> Iterable[Type[Enum]]:
    if p is Platform.WINDOWS:
        return (WindowsCategory,)
    if p is Platform.ANDROID:
        return (AndroidCategory,)
    if p is Platform.IOS:
        return (IOSCategory,)
    if p is Platform.MACOS:
        return (MacOSCategory,)


def _parse_category(value: str, platform: Platform) -> Category:
    for enum_cls in _iter_category_enums_for_platform(platform):
        try:
            return cast(Category, enum_cls(value))
        except ValueError:
            continue
    raise ValueError(f"category='{value}' non valida per platform='{platform.value}'")


@dataclass
class RequestData:
    platform: Optional[Platform] = None
    category: Optional[Category] = None
    user_id: Optional[int] = None
    status: Optional[RequestStatus] = None
    issued_at: Optional[datetime] = None
    name: Optional[str] = None
    link: Optional[str] = None
    version: Optional[str] = None
    functionalities: Optional[str] = None
    steamtools: Optional[bool] = None
    requesting: Optional[RequestField] = None
    editing: Optional[str] = None

    def to_dict(self) -> RequestDataDict:
        """Serializza in un RequestDataDict per poter essere messo nella persistenza."""

        missing = []
        if self.platform is None: missing.append("platform")
        if self.category is None: missing.append("category")
        if self.user_id is None: missing.append("user_id")
        if self.status is None: missing.append("status")
        if self.issued_at is None: missing.append("issued_at")
        if self.name is None: missing.append("name")
        if self.version is None: missing.append("version")
        if missing:
            raise ValueError(f"RequestData incompleto, mancano: {', '.join(missing)}")

        result: RequestDataDict = {
            "platform": self.platform.value,  # PlatformStr
            "category": cast(str, cast(Enum, self.category).value),  # Cat Literal | str
            "user_id": int(self.user_id),
            "status": self.status.value,  # StatusStr
            "issued_at": self.issued_at.isoformat(),
            "name": self.name,
            "version": self.version,
        }
        if self.link is not None:
            result["link"] = self.link
        if self.functionalities is not None:
            result["functionalities"] = self.functionalities
        if self.steamtools is not None:
            result["steamtools"] = self.steamtools
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: RequestDataDict) -> RequestData:
        platform = Platform(data["platform"])

        category = _parse_category(data["category"], platform)

        # noinspection PyArgumentList
        status = RequestStatus(data["status"])

        issued_at = datetime.fromisoformat(data["issued_at"])

        link = data.get("link")
        functionalities = data.get("functionalities")
        steamtools = data.get("steamtools")

        return cls(
            platform=platform,
            category=category,
            user_id=data["user_id"],
            status=status,
            issued_at=issued_at,
            name=data["name"],
            link=link,
            version=data["version"],
            functionalities=functionalities,
            steamtools=steamtools,
        )

    @classmethod
    def from_json(cls, json_str: str) -> RequestDataDict:
        return cls.from_dict(json.loads(json_str))

    def get_category(self) -> Optional[Category]:
        """Determina la categoria per piattaforme Windows"""
        return self.category

    def get_platform(self) -> Platform:
        """Ritorna la piattaforma"""
        return self.platform


class RequestDataDict(TypedDict):
    platform: Required[PlatformStr]
    category: Required[WinCatStr | AndroidCatStr | IOSCatStr | MacOSCatStr]
    user_id: Required[int]
    status: Required[StatusStr]
    issued_at: Required[str]
    name: Required[str]
    version: Required[str]

    link: NotRequired[str]
    functionalities: NotRequired[str]
    steamtools: NotRequired[bool]
