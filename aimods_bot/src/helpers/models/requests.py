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


class AndroidAppDetails(BaseRequest):
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


REQUEST_MODELS = {
    (Platform.ANDROID, Category.APP): AndroidAppDetails,
    (Platform.WINDOWS, Category.SOFTWARE): WindowsSoftware,
    (Platform.WINDOWS, Category.GAME): WindowsGame,
    (Platform.WINDOWS, Category.ADOBE): WindowsAdobe,
    (Platform.WINDOWS, Category.DAW): WindowsDaw,
    (Platform.IOS, Category.APP): IosApp,
    (Platform.MACOS, Category.SOFTWARE): MacOsSoftware,
    (Platform.MACOS, Category.DAW): MacOsDaw,
}
