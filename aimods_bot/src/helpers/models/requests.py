from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Annotated, Any, ClassVar
from pydantic import BaseModel, BeforeValidator, HttpUrl, Field

from aimods_bot.src.helpers.constants.constants import Platform, Category, RequestField, RequestStatus
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)


def prepend_https(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        if not value.startswith(("http://", "https://")):
            return f"https://{value}"
    return value


UxHttpUrl = Annotated[HttpUrl, BeforeValidator(prepend_https)]


class BaseRequest(BaseModel):
    id: int | None = None
    user_id: int

    platform: Platform
    category: Category

    issued_at: datetime | None = None
    status: RequestStatus | None = None

    rejection_reason: str | None = None
    status_change_notifications: bool = True

    FLOW: ClassVar[list[RequestField]]

    @property
    def is_active(self) -> bool:
        if not self.status:
            return False
        return self.status not in (RequestStatus.CANCELLED, RequestStatus.COMPLETED, RequestStatus.REJECTED)

    def confirm_submission(self) -> None:
        self.status = RequestStatus.PENDING
        self.issued_at = datetime.now(timezone.utc)

    def can_be_cancelled(self, cancel_time_sec: int) -> bool:
        if self.status != RequestStatus.PENDING or not self.issued_at:
            return False
        delta = datetime.now(timezone.utc) - self.issued_at
        return delta.total_seconds() < cancel_time_sec

    def edit_status(self, status: RequestStatus, rejection_reason: str | None = None) -> None:
        if status == RequestStatus.REJECTED:
            if not rejection_reason or not rejection_reason.strip():
                raise ValueError("A rejection reason must be provided.")
            else:
                self.rejection_reason = rejection_reason
        self.status = status


class AndroidApp(BaseRequest):
    platform: Literal[Platform.ANDROID] = Platform.ANDROID
    category: Literal[Category.APP] = Category.APP

    name: str
    link: UxHttpUrl
    version: str
    features: str

    FLOW: ClassVar[list[RequestField]] = [
        RequestField.NAME,
        RequestField.LINK,
        RequestField.VERSION,
        RequestField.FEATURES,
    ]


class WindowsSoftware(BaseRequest):
    platform: Literal[Platform.WINDOWS] = Platform.WINDOWS
    category: Literal[Category.SOFTWARE] = Category.SOFTWARE

    name: str
    link: UxHttpUrl
    version: str
    features: str

    FLOW: ClassVar[list[RequestField]] = [
        RequestField.NAME,
        RequestField.LINK,
        RequestField.VERSION,
        RequestField.FEATURES
    ]


class WindowsGame(BaseRequest):
    platform: Literal[Platform.WINDOWS] = Platform.WINDOWS
    category: Literal[Category.GAME] = Category.GAME

    name: str
    link: UxHttpUrl
    version: str
    features: str
    steamtools: bool
    hypervisor: bool

    FLOW: ClassVar[list[RequestField]] = [
        RequestField.NAME,
        RequestField.LINK,
        RequestField.VERSION,
        RequestField.FEATURES,
        RequestField.STEAMTOOLS,
        RequestField.HYPERVISOR
    ]


class WindowsAdobe(BaseRequest):
    platform: Literal[Platform.WINDOWS] = Platform.WINDOWS
    category: Literal[Category.ADOBE] = Category.ADOBE

    name: str
    version: str
    features: str
    arch_arm: bool

    FLOW: ClassVar[list[RequestField]] = [
        RequestField.NAME,
        RequestField.VERSION,
        RequestField.FEATURES,
        RequestField.ARCH_ARM
    ]


class WindowsDaw(BaseRequest):
    platform: Literal[Platform.WINDOWS] = Platform.WINDOWS
    category: Literal[Category.DAW] = Category.DAW

    name: str
    link: UxHttpUrl
    version: str

    FLOW: ClassVar[list[RequestField]] = [
        RequestField.NAME,
        RequestField.LINK,
        RequestField.VERSION
    ]


class IosApp(BaseRequest):
    platform: Literal[Platform.IOS] = Platform.IOS
    category: Literal[Category.APP] = Category.APP

    name: str
    link: UxHttpUrl
    version: str
    features: str

    FLOW: ClassVar[list[RequestField]] = [
        RequestField.NAME,
        RequestField.LINK,
        RequestField.VERSION,
        RequestField.FEATURES
    ]


class MacOsSoftware(BaseRequest):
    platform: Literal[Platform.MACOS] = Platform.MACOS
    category: Literal[Category.SOFTWARE] = Category.SOFTWARE

    name: str
    link: UxHttpUrl
    version: str
    features: str
    mac_os_version: str
    arch_arm: bool

    FLOW: ClassVar[list[RequestField]] = [
        RequestField.NAME,
        RequestField.LINK,
        RequestField.VERSION,
        RequestField.FEATURES,
        RequestField.MAC_OS_VERSION,
        RequestField.ARCH_ARM
    ]


class MacOsDaw(BaseRequest):
    platform: Literal[Platform.MACOS] = Platform.MACOS
    category: Literal[Category.DAW] = Category.DAW

    name: str
    link: UxHttpUrl
    version: str
    mac_os_version: str
    arch_arm: bool

    FLOW: ClassVar[list[RequestField]] = [
        RequestField.NAME,
        RequestField.LINK,
        RequestField.VERSION,
        RequestField.MAC_OS_VERSION,
        RequestField.ARCH_ARM
    ]


@dataclass(frozen=True)
class CategoryConfig:
    label: str
    icon: str
    model: type


REQUESTS_LAYOUT_REGISTRY: dict[Platform, dict[Category, CategoryConfig]] = {
    Platform.ANDROID: {
        Category.APP: CategoryConfig("App", "🤖", AndroidApp),
    },

    Platform.WINDOWS: {
        Category.GAME: CategoryConfig("Gioco", "🕹", WindowsGame),
        Category.ADOBE: CategoryConfig("Adobe", "🖌", WindowsAdobe),
        Category.DAW: CategoryConfig("DAW", "🎹", WindowsDaw),
        Category.SOFTWARE: CategoryConfig("Software", "⌨", WindowsSoftware),
    },

    Platform.IOS: {
        Category.APP: CategoryConfig("App", "🍏", IosApp),
    },

    Platform.MACOS: {
        Category.DAW: CategoryConfig("DAW", "🎹", MacOsDaw),
        Category.SOFTWARE: CategoryConfig("Software", "🖥", MacOsSoftware),
    }
}
