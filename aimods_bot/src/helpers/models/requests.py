from collections import defaultdict
from dataclasses import dataclass
from typing import Literal, Annotated, Any, ClassVar
from pydantic import BaseModel, BeforeValidator, HttpUrl

from aimods_bot.src.helpers.constants.constants import Platform, Category, RequestField


def prepend_https(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        if not value.startswith(("http://", "https://")):
            return f"https://{value}"
    return value


UxHttpUrl = Annotated[HttpUrl, BeforeValidator(prepend_https)]


class BaseRequest(BaseModel):
    user_id: int
    platform: Platform
    category: Category
    requesting: RequestField | None = None
    editing: bool = False

    @property
    def kind(self) -> str:
        return f"{self.platform}_{self.category}"

    FLOW: ClassVar[list[RequestField]]


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


REQUESTS_LAYOUT_REGISTRY: dict[tuple[Platform, Category], CategoryConfig] = {
    (Platform.ANDROID, Category.APP): CategoryConfig("App", "🤖", AndroidApp),

    (Platform.WINDOWS, Category.GAME): CategoryConfig("Gioco", "🕹", WindowsGame),
    (Platform.WINDOWS, Category.ADOBE): CategoryConfig("Adobe", "🖌", WindowsAdobe),
    (Platform.WINDOWS, Category.DAW): CategoryConfig("DAW", "🎹", WindowsDaw),
    (Platform.WINDOWS, Category.SOFTWARE): CategoryConfig("Software", "⌨", WindowsSoftware),

    (Platform.IOS, Category.APP): CategoryConfig("App", "🍏", IosApp),

    (Platform.MACOS, Category.DAW): CategoryConfig("DAW", "🎹", MacOsDaw),
    (Platform.MACOS, Category.SOFTWARE): CategoryConfig("Software", "🖥", MacOsSoftware)
}


CATEGORIES_PER_PLATFORM: dict[Platform, list[CategoryConfig]] = defaultdict(list)

for (plat, _), config in REQUESTS_LAYOUT_REGISTRY.items():
    CATEGORIES_PER_PLATFORM[plat].append(config)
