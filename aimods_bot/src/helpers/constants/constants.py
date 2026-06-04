from __future__ import annotations

import pytz

from dataclasses import dataclass
from enum import StrEnum

YAML_CONFIG_PATH = "aimods_bot/misc/BotConfigurationStructure.yml"

CHANNEL_JOIN_LINK = "https://t.me/+YmSMpGvSrlphYjJk"
GROUP_JOIN_LINK = "https://t.me/+s3kZBM549qE1ZTU8"

LOCAL_TZ = pytz.timezone('Europe/Rome')

SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE = 86400

pyro_instance = None

ERROR_MESSAGES = {
    "command_syntax_error": "⚠️ Warning\n\n▪️ Sintassi del comando non corretta.",
    "no_user_provided": "⚠️ Warning\n\n▪️ Se non rispondi ad un messaggio, devi indicare un utente.",
    "cannot_parse_user": "⚠️ Warning\n\n▪️ Non riesco a risolvere l'utente specificato, riprova.\n\n"
                         "🔍 Tipicamente significa che l'utente non è nel gruppo.",
    "username_404": "⚠️ Warning\n\n▪️ Lo username {} non esiste.",
    "user_not_in_group": "⚠️ Warning\n\n▪️ L'utente non è nel gruppo.",
    "user_banned": "⚠️ Warning\n\n▪️ L'utente è bannato.",
}

PUNISHMENT_EMOJIS = {
    "ban": "🚫",
    "kick": "🥊",
    "mute": "🔒",
    "warn": "⚠️"
}

LIST_DETAILS = {
    "whitelist": {
        "icon": "📨",
        "desc": "I domini aggiunti a questa lista <b>non verranno puniti</b> se spammati."
    },
    "blacklist": {
        "icon": "📓",
        "desc": "I domini aggiunti a questa lista verranno <b>puniti con il ban, "
                "indipendentemente dalla punizione impostata</b>."
    },
    "greylist": {
        "icon": "🧙‍♂️",
        "desc": "I link aggiunti a questa lista <b>non verranno puniti</b>."
    }
}


@dataclass
class DisplayItem:
    display_icon: str
    display_name: str
    target_description: str


MODERATION_DISPLAY_ITEMS = {
    "antispam": DisplayItem("📨", "Anti-Spam", "a chi spamma"),
    "antispam/forward/user": DisplayItem("📨", "Anti-Spam → Inoltro", "a chi inoltra un messaggio di un utente"),
    "antispam/forward/group": DisplayItem("📨", "Anti-Spam → Inoltro", "a chi inoltra un messaggio da un gruppo"),
    "antispam/forward/channel": DisplayItem("📨", "Anti-Spam → Inoltro", "a chi inoltra un messaggio da un canale"),
    "antispam/forward/bot": DisplayItem("📨", "Anti-Spam → Inoltro", "a chi inoltra un messaggio di un bot"),
    "antispam/link": DisplayItem("📨", "Anti-Spam → Link", "a chi spamma link"),
    "antispam/mention/user": DisplayItem("📨", "Anti-Spam → Menzione", "a chi menziona un utente"),
    "antispam/mention/group": DisplayItem("📨", "Anti-Spam → Menzione", "a chi menziona un gruppo"),
    "antispam/mention/channel": DisplayItem("📨", "Anti-Spam → Menzione", "a chi menziona un canale"),
    "antispam/mention/bot": DisplayItem("📨", "Anti-Spam → Menzione", "a chi menziona un bot"),
    "antiflood": DisplayItem("🌊", "Anti-Flood", "a chi fa flooding")
}


class FieldFormat(StrEnum):
    TEXT = "text"  # <i>valore</i>
    CODE = "code"  # <code>valore</code>
    LINK = "link"  # <a href="valore">🔗 Link</a>
    BOOL = "bool"  # ✔️ / ✖️


class Platform(StrEnum):
    ANDROID = "android"
    WINDOWS = "windows"
    IOS = "ios"
    MACOS = "macos"

    @property
    def icon(self) -> str:
        match self:
            case Platform.ANDROID:
                return "🤖"
            case Platform.WINDOWS:
                return "💻"
            case Platform.IOS:
                return "🍏"
            case Platform.MACOS:
                return "🖥"

    @property
    def label(self) -> str:
        match self:
            case Platform.ANDROID:
                return "Android"
            case Platform.WINDOWS:
                return "Windows"
            case Platform.IOS:
                return "iOS"
            case Platform.MACOS:
                return "MacOS"


class Category(StrEnum):
    APP = "app"
    GAME = "game"
    DAW = "daw"
    ADOBE = "adobe"
    SOFTWARE = "software"


class Arch(StrEnum):
    x86 = "x86"
    x86_64 = "x86_64"
    ARM = "arm"
    ARM_64 = "arm64"


class RequestStatus(StrEnum):
    PENDING = "pending"
    EXAMINING = "examining"
    TESTING = "testing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

    @property
    def label(self) -> str:
        match self:
            case RequestStatus.PENDING:
                return "In Attesa"
            case RequestStatus.EXAMINING:
                return "In Esame"
            case RequestStatus.TESTING:
                return "In Test"
            case RequestStatus.COMPLETED:
                return "Completata"
            case RequestStatus.REJECTED:
                return "Rifiutata"
            case RequestStatus.CANCELLED:
                return "Cancellata"

    @property
    def icon(self) -> str:
        match self:
            case RequestStatus.PENDING:
                return "⏳"
            case RequestStatus.EXAMINING:
                return "🔎"
            case RequestStatus.TESTING:
                return "🧪"
            case RequestStatus.COMPLETED:
                return "✅"
            case RequestStatus.REJECTED:
                return "❌"
            case RequestStatus.CANCELLED:
                return "🗑️"


class RequestField(StrEnum):
    NAME = "name"
    LINK = "link"
    VERSION = "version"
    FEATURES = "features"
    STEAMTOOLS = "steamtools"
    HYPERVISOR = "hypervisor"
    ARCH_ARM = "arch_arm"
    MAC_OS_VERSION = "mac_os_version"

    @property
    def label(self) -> str:
        match self:
            case RequestField.NAME:
                return "Nome"
            case RequestField.LINK:
                return "Link"
            case RequestField.VERSION:
                return "Versione"
            case RequestField.FEATURES:
                return "Funzionalità"
            case RequestField.STEAMTOOLS:
                return "SteamTools"
            case RequestField.HYPERVISOR:
                return "HyperVisor"
            case RequestField.ARCH_ARM:
                return "Arch. ARM"
            case RequestField.MAC_OS_VERSION:
                return "Versione MacOS"

    @property
    def format(self) -> FieldFormat:
        match self:
            case RequestField.NAME | RequestField.FEATURES:
                return FieldFormat.TEXT
            case RequestField.LINK:
                return FieldFormat.LINK
            case RequestField.VERSION | RequestField.MAC_OS_VERSION:
                return FieldFormat.CODE
            case RequestField.STEAMTOOLS | RequestField.HYPERVISOR | RequestField.ARCH_ARM:
                return FieldFormat.BOOL


class ChatType(StrEnum):
    USER = "user"
    GROUP = "group"
    CHANNEL = "channel"
    BOT = "bot"

    @property
    def label(self) -> str:
        match self:
            case ChatType.USER:
                return "Utenti"
            case ChatType.GROUP:
                return "Gruppi"
            case ChatType.CHANNEL:
                return "Canali"
            case ChatType.BOT:
                return "Bot"

    @property
    def icon(self) -> str:
        match self:
            case ChatType.USER:
                return "👤"
            case ChatType.GROUP:
                return "👥"
            case ChatType.CHANNEL:
                return "📢"
            case ChatType.BOT:
                return "🤖"


class RejectRequestReason(StrEnum):
    SERVERSIDE = "serverside"
    NOT_AVAILABLE = "not_available"
    ALREADY_AVAILABLE = "already_available"
    UNCLEAR = "unclear"

    @property
    def label(self) -> str:
        match self:
            case RejectRequestReason.SERVERSIDE:
                return "Serverside"
            case RejectRequestReason.NOT_AVAILABLE:
                return "Non disponibile al momento"
            case RejectRequestReason.ALREADY_AVAILABLE:
                return "Già disponibile sul canale"
            case RejectRequestReason.UNCLEAR:
                return "Richiesta non chiara"


class ModerationList(StrEnum):
    WHITELIST = "whitelist"
    GREYLIST = "greylist"
    BLACKLIST = "blacklist"

    @property
    def icon(self) -> str:
        match self:
            case ModerationList.WHITELIST:
                return "📨"
            case ModerationList.GREYLIST:
                return "🧙‍♂️"
            case ModerationList.BLACKLIST:
                return "📓"

    @property
    def description(self) -> str:
        match self:
            case ModerationList.WHITELIST:
                return "I domini aggiunti a questa lista <b>non verranno puniti</b> se spammati."
            case ModerationList.GREYLIST:
                return "I link aggiunti a questa lista <b>non verranno puniti</b>."
            case ModerationList.BLACKLIST:
                return ("I domini aggiunti a questa lista verranno <b>puniti con il ban, "
                        "indipendentemente dalla punizione impostata</b>.")

    @property
    def item_label_singular(self) -> str:
        match self:
            case ModerationList.WHITELIST | ModerationList.BLACKLIST:
                return "dominio"
            case ModerationList.GREYLIST:
                return "link"

    @property
    def item_label_plural(self) -> str:
        match self:
            case ModerationList.WHITELIST | ModerationList.BLACKLIST:
                return "domini"
            case ModerationList.GREYLIST:
                return "link"


DATETIME_FORMAT = "%d %b %Y alle %H:%M:%S"

EMOJI_HOURGLASS = "⏳"
EMOJI_WARNING = "⚠️"
EMOJI_CHECKMARK = "✔"
EMOJI_QUESTION_RED = "❓"
EMOJI_EXCLAMATION_RED = "❗"
EMOJI_DOT_BLUE = "🔹"
EMOJI_DOT_ORANGE = "🔸"

EMOJI_NUMBER = {
    0: "0️⃣",
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣",
    7: "7️⃣",
    8: "8️⃣",
    9: "9️⃣",
    10: "🔟"
}

COMMAND_PREFIX = [".", "!", "/"]
