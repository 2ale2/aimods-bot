from __future__ import annotations

from dataclasses import dataclass
from typing import Union, Literal, Optional

from telegram import InputMedia

from aimods_bot.src.helpers.constants.constants import Category


@dataclass
class MediaItem:
    item: Union[str, InputMedia]
    type: Literal["document", "photo", "audio", "video", "gif"]
    as_doc: bool


@dataclass
class CanUserRequest:
    yn: bool
    reason: Optional[str]


@dataclass(frozen=True)
class MessageTemplate:
    default: str
    app: str | None = None
    game: str | None = None
    software: str | None = None
    daw: str | None = None
    adobe: str | None = None

    def get_prompt(self, category: Category) -> str:
        specific_prompt = getattr(self, category.value, None)
        return specific_prompt or self.default
