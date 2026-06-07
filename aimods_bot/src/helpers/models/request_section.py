from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from aimods_bot.src.helpers.constants.constants import Platform, Category
from aimods_bot.src.helpers.models.requests import PLATFORM_CATEGORY_REGISTRY, CategoryConfig, BaseRequest


_SEPARATOR = ":"


class RequestSection(BaseModel):
    """Sezione richieste tipizzata (Platform, Category)."""
    model_config = ConfigDict(frozen=True)

    platform: Platform
    category: Category

    @model_validator(mode="after")
    def _validate_combination(self) -> Self:
        categories = PLATFORM_CATEGORY_REGISTRY.get(self.platform)
        if categories is None:
            raise ValueError(f"Platform {self.platform.value} not in registry.")
        if self.category not in categories:
            raise ValueError(
                f"Category {self.category.value} not valid for platform {self.platform.value}. "
                f"Valid: {[c.value for c in categories]}"
            )
        return self

    @classmethod
    def from_string(cls, raw: str, separator: str = _SEPARATOR) -> Self:
        platform_str, category_str = raw.split(separator, 1)
        return cls(
            platform=Platform(platform_str),
            category=Category(category_str),
        )

    def to_string(self, separator: str = _SEPARATOR) -> str:
        return f"{self.platform.value}{separator}{self.category.value}"

    def __str__(self) -> str:
        return self.to_string()

    @property
    def category_config(self) -> CategoryConfig:
        return PLATFORM_CATEGORY_REGISTRY[self.platform][self.category]

    @property
    def request_model(self) -> type[BaseRequest]:
        return self.category_config.model
