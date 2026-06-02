from typing import Annotated, Literal, Union
from enum import StrEnum
from pydantic import BaseModel, Field, ValidationError
from aimods_bot.src.helpers.loggers import logger


log = logger.getChild(__name__)
_SEPARATOR = ":"


class CallbackType(StrEnum):
    ALERT = "alert"


class _BaseCallbackData(BaseModel):
    model_config = {"frozen": True}

    def __str__(self) -> str:
        return self.to_string()

    def to_string(self) -> str:
        raise NotImplementedError


class AlertCallbackData(_BaseCallbackData):
    type: Literal[CallbackType.ALERT] = CallbackType.ALERT
    user_id: int
    alert_id: str

    def to_string(self) -> str:
        return _SEPARATOR.join([self.type.value, str(self.user_id), self.alert_id])


CallbackData = Annotated[
    Union[
        AlertCallbackData,
    ],
    Field(discriminator="type"),
]


def parse_callback_data(raw: str) -> CallbackData | None:
    if not raw:
        return None

    head, *args = raw.split(_SEPARATOR)

    try:
        kind = CallbackType(head)
    except ValueError:
        log.error(f"Invalid callback data ('{raw}'): {head} typed callback data type does not exist!")
        return None

    try:
        match kind:
            case CallbackType.ALERT:
                if len(args) != 2:
                    log.error(f"Alert callbacktype wrong syntax ('{raw}'): incorrect number of arguments!")
                    return None
                return AlertCallbackData(
                    user_id=int(args[0]),
                    alert_id=args[1],
                )
    except (ValueError, ValidationError) as e:
        log.error(f"Invalid callback data ('{raw}'): {e}")
        return None
