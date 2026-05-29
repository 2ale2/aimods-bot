from __future__ import annotations

from dataclasses import dataclass
from typing import Union, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
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


class MessageTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    default: str
    overrides: dict[Category, str] = Field(default_factory=dict)

    def get_prompt(self, category: Category) -> str:
        return self.overrides.get(category, self.default)
