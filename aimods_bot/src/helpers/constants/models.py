from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Union, Literal, NamedTuple, TypedDict, cast, Iterable, Type

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMedia, ReplyParameters
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

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
    id: Optional[str] = None
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
    editing: Optional[RequestField] = None

    def to_dict(self) -> RequestDataDict:
        """Serializza in un RequestDataDict per poter essere messo nella persistenza."""
        result: RequestDataDict = {}
        if self.id is not None:
            result["id"] = self.id
        if self.platform is not None:
            result["platform"] = cast(PlatformStr, self.platform.value)
        if self.category is not None:
            result["category"] = cast(CatStr, self.category.value)
        if self.user_id is not None:
            result["user_id"] = self.user_id
        if self.status is not None:
            result["status"] = cast(StatusStr, self.status.value)
        if self.issued_at is not None:
            result["issued_at"] = self.issued_at.isoformat()
        if self.name is not None:
            result["name"] = self.name
        if self.version is not None:
            result["version"] = self.version
        if self.link is not None:
            result["link"] = self.link
        if self.functionalities is not None:
            result["functionalities"] = self.functionalities
        if self.steamtools is not None:
            result["steamtools"] = self.steamtools
        if self.requesting is not None:
            result["requesting"] = self.requesting.value
        if self.editing is not None:
            result["editing"] = self.editing.value

        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: RequestDataDict) -> RequestData:
        raw_id = data.get("id", None)
        raw_platform = data.get("platform", None)
        raw_category = data.get("category", None)
        raw_user_id = data.get("user_id", None)
        raw_status = data.get("status", None)
        raw_issued_at = data.get("issued_at", None)
        raw_name = data.get("name", None)
        raw_version = data.get("version", None)
        raw_link = data.get("link", None)
        raw_functionalities = data.get("functionalities", None)
        raw_steamtools = data.get("steamtools", None)
        raw_requesting = data.get("requesting", None)
        raw_editing = data.get("editing", None)
        platform = Platform(raw_platform) if raw_platform else None
        category = _parse_category(raw_category, platform) if raw_category and platform else None
        # noinspection PyArgumentList
        status = RequestStatus(raw_status) if raw_status else None
        issued_at = datetime.fromisoformat(raw_issued_at) if raw_issued_at else None
        requesting = RequestField(raw_requesting) if raw_requesting else None
        editing = RequestField(raw_editing) if raw_editing else None

        return cls(
            id=raw_id,
            platform=platform,
            category=category,
            user_id=raw_user_id,
            status=status,
            issued_at=issued_at,
            name=raw_name,
            link=raw_link,
            version=raw_version,
            functionalities=raw_functionalities,
            steamtools=raw_steamtools,
            requesting=requesting,
            editing=editing
        )

    @classmethod
    def from_json(cls, json_str: str) -> RequestDataDict:
        return cls.from_dict(json.loads(json_str))

    def get_category(self, request_dict: RequestDataDict = None) -> Optional[Category]:
        """Determina la categoria per piattaforme Windows"""
        if request_dict:
            return request_dict["category"]
        return self.category

    def get_platform(self, request_dict: RequestDataDict = None) -> Platform:
        """Ritorna la piattaforma"""
        if request_dict:
            return request_dict["platform"]
        return self.platform


class RequestDataDict(TypedDict, total=False):
    id: str
    platform: PlatformStr
    category: WinCatStr | AndroidCatStr | IOSCatStr | MacOSCatStr
    user_id: int
    status: StatusStr
    issued_at: str
    name: str
    version: str
    link: str
    functionalities: str
    steamtools: bool
    requesting: str
    editing: str
