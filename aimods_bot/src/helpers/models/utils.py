from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Union, Literal, Optional, NamedTuple, Dict, Tuple, Type

from telegram import InputMedia

from aimods_bot.src.helpers.constants.constants import Platform, WindowsCategory, AndroidCategory, IOSCategory, \
    MacOSCategory


@dataclass
class MediaItem:
    item: Union[str, InputMedia]
    type: Literal["document", "photo", "audio", "video", "gif"]
    as_doc: bool


@dataclass
class CanUserRequest:
    yn: bool
    reason: Optional[str]


class MessageTemplate(NamedTuple):
    app: str
    game: str
    daw: str
    software: str


_PLATFORM_CATEGORY_MAP: Dict[Platform, Tuple[Type[Enum], ...]] = {
    Platform.WINDOWS: (WindowsCategory,),
    Platform.ANDROID: (AndroidCategory,),
    Platform.IOS: (IOSCategory,),
    Platform.MACOS: (MacOSCategory,)
}
