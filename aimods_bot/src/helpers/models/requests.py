from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Annotated, Any, ClassVar

from pydantic import BaseModel, BeforeValidator, HttpUrl

from aimods_bot.src.helpers.constants.constants import Platform, Category, RequestField, RequestStatus
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.utils import MessageTemplate

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

    name: str
    version: str

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

    link: UxHttpUrl
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

    link: UxHttpUrl
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

    link: UxHttpUrl
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

    link: UxHttpUrl

    FLOW: ClassVar[list[RequestField]] = [
        RequestField.NAME,
        RequestField.LINK,
        RequestField.VERSION
    ]


class IosApp(BaseRequest):
    platform: Literal[Platform.IOS] = Platform.IOS
    category: Literal[Category.APP] = Category.APP

    link: UxHttpUrl
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

    link: UxHttpUrl
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

    link: UxHttpUrl
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
    model: type[BaseRequest]


PLATFORM_CATEGORY_REGISTRY: dict[Platform, dict[Category, CategoryConfig]] = {
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


FIELD_MESSAGES: dict[RequestField, MessageTemplate] = {
    RequestField.NAME: MessageTemplate(
        default="🔹 Indica il <b>nome</b> di ciò che vorresti richiedere.",
        app="🔹 Indica il <b>nome dell'app</b> che vorresti richiedere.",
        game="🔹 Indica il <b>nome del gioco</b> che vorresti richiedere.",
        software="🔹 Indica il <b>nome del software</b> che vorresti richiedere.",
        daw="🔹 Indica il <b>nome della DAW o del Plug-In</b> che vorresti richiedere.",
        adobe="🔹 Indica il <b>nome del prodotto Adobe</b> che vorresti richiedere."
    ),
    RequestField.LINK: MessageTemplate(
        default="🔹 Indica il <b>link di riferimento</b>.",
        app="🔹 Indica il <b>link ufficile dell'app</b>.",
        game="🔹 Indica il <b>link ufficiale del gioco</b>.",
        software="🔹 Indica il <b>link ufficiale del software</b>.",
        daw="🔹 Indica il <b>link ufficiale della DAW o del Plug-In</b>."
    ),
    RequestField.VERSION: MessageTemplate(
        default="🔹 Indica la <b>versione</b> che vorresti richiedere.",
        app="🔹 Indica la <b>versione dell'app</b> che vorresti richiedere.",
        game="🔹 Indica la <b>versione del gioco</b> che vorresti richiedere.",
        software="🔹 Indica la <b>versione del software</b> che vorresti richiedere.",
        daw="🔹 Indica la <b>versione della DAW o del Plug-In</b>.",
        adobe="🔹 Indica <b>la versione</b> del prodotto Adobe."
    ),
    RequestField.FEATURES: MessageTemplate(
        default="🔹 Indica le <b>funzionalità</b> che vorresti sbloccare.",
        app="🔹 Indica le <b>funzionalità dell'app</b> che vorresti sbloccare (es. Premium, No Pubblicità).",
        game="🔹 Indica le <b>funzionalità del gioco</b> che vorresti sbloccare (es. Gioco Pagato, Monete infinite).",
        software="🔹 Indica le <b>funzionalità del software</b> che vorresti sbloccare.",
        daw="🔹 Indica le <b>funzionalità della DAW o del Plug-In</b>.",
        adobe="🔹 Indica le <b>funzionalità o i filtri aggiuntivi</b> da sbloccare."
    ),
    RequestField.STEAMTOOLS: MessageTemplate(
        default="🔹 Accetteresti il titolo con i file <b>SteamTools</b>?"
    ),
    RequestField.HYPERVISOR: MessageTemplate(
        default="🔹 Accetteresti il titolo con metodo <b>Hypervisor</b>?"
    ),
    RequestField.ARCH_ARM: MessageTemplate(
        default="🔹 Il tuo dispositivo ha architettura <b>ARM</b>?"
    ),
    RequestField.MAC_OS_VERSION: MessageTemplate(
        default="🔹 Indica la tua versione esatta di <b>macOS</b> (es. Sonoma 14.5)."
    )
}
