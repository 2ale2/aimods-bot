from __future__ import annotations

import pytz

from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Union

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

PLATFORM_DETAILS = {
    "android": {
        "label": "Android",
        "icon": "🤖"
    },
    "windows": {
        "label": "Windows",
        "icon": "💻"
    },
    "ios": {
        "label": "iOS",
        "icon": "🍏"
    },
    "macos": {
        "label": "MacOS",
        "icon": "🖥"
    }
}

CATEGORY_DETAILS = {
    "android": {
        "app": {
            "label": "App",
            "icon": "🤖"
        }
    },
    "windows": {
        "game": {
            "label": "Gioco",
            "icon": "🕹"
        },
        "adobe": {
            "label": "Adobe",
            "icon": "🖌"
        },
        "daw": {
            "label": "DAW",
            "icon": "🎹"
        },
        "software": {
            "label": "Software",
            "icon": "⌨"
        }
    },
    "ios": {
        "app": {
            "label": "App",
            "icon": "🍏"
        }
    },
    "macos": {
        "daw": {
            "label": "DAW",
            "icon": "🎹"
        },
        "software": {
            "label": "Software",
            "icon": "🖥"
        }
    }
}

REQUEST_STATUS_DETAILS = {
    "pending": {
        "label": "In Attesa",
        "icon": "⏳"
    },
    "examining": {
        "label": "In Esame",
        "icon": "🔎"
    },
    "testing": {
        "label": "In Test",
        "icon": "🧪"
    },
    "completed": {
        "label": "Completata",
        "icon": "✅"
    },
    "rejected": {
        "label": "Rifiutata",
        "icon": "❌"
    },
    "cancelled": {
        "label": "Cancellata",
        "icon": "🗑️"
    }
}

REQUEST_DETAILS_CONFIG = {
    "android": {
        "app": {
            'name': {'label': 'Nome', 'format': 'text'},
            'link': {'label': 'Link', 'format': 'link'},
            'version': {'label': 'Versione', 'format': 'code'},
            'functionalities': {'label': 'Funzionalità', 'format': 'text'}
        }
    },
    "windows": {
        "software": {
            'name': {'label': 'Nome', 'format': 'text'},
            'link': {'label': 'Link', 'format': 'link'},
            'version': {'label': 'Versione', 'format': 'code'},
            'functionalities': {'label': 'Funzionalità', 'format': 'text'}
        },
        "game": {
            'name': {'label': 'Nome', 'format': 'text'},
            'link': {'label': 'Link', 'format': 'link'},
            'version': {'label': 'Versione', 'format': 'code'},
            'functionalities': {'label': 'Funzionalità', 'format': 'text'},
            'steamtools': {'label': 'Steam Tools', 'format': 'bool'}
        },
        "adobe": {
            'name': {'label': 'Nome', 'format': 'text'},
            'version': {'label': 'Versione', 'format': 'code'},
            'functionalities': {'label': 'Funzionalità', 'format': 'text'},
            'arch': {'label': 'CPU ARM', 'format': 'bool'}
        },
        "daw": {
            'name': {'label': 'Nome', 'format': 'text'},
            'link': {'label': 'Link', 'format': 'link'},
            'version': {'label': 'Versione', 'format': 'code'}
        }
    },
    "ios": {
        "app": {
            'name': {'label': 'Nome', 'format': 'text'},
            'link': {'label': 'Link', 'format': 'link'},
            'version': {'label': 'Versione', 'format': 'code'},
            'functionalities': {'label': 'Funzionalità', 'format': 'text'}
        }
    },
    "macos": {
        "software": {
            'name': {'label': 'Nome', 'format': 'text'},
            'link': {'label': 'Link', 'format': 'link'},
            'version': {'label': 'Versione', 'format': 'code'},
            'functionalities': {'label': 'Funzionalità', 'format': 'text'}
        },
        "daw": {
            'name': {'label': 'Nome', 'format': 'text'},
            'link': {'label': 'Link', 'format': 'link'},
            'version': {'label': 'Versione', 'format': 'code'}
        }
    }
}


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


class Arch(Enum):
    x86 = "x86"
    x86_64 = "x86_64"
    ARM = "arm"
    ARM_64 = "arm64"


class RequestStatus(Enum):
    PENDING = "pending"
    EXAMINING = "examining"
    TESTING = "testing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


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


class RejectRequestReason(Enum):
    SERVERSIDE = "serverside"
    NOT_AVAILABLE = "not_available"
    ALREADY_AVAILABLE = "already_available"
    UNCLEAR = "unclear"


REQUEST_REJECTION_REASONS = {
    "serverside": "Serverside",
    "not_available": "Non disponibile al momento",
    "already_available": "Già disponibile sul canale",
    "unclear": "Richiesta non chiara"
}

DATETIME_FORMAT = "%d %b %Y alle %H:%M:%S"

EMOJI_HOURGLASS = "⏳"
EMOJI_WARNING = "⚠️"
EMOJI_CHECKMARK = "✔"
EMOJI_QUESTION_RED = "❓"
EMOJI_ESCLAMATION_RED = "❗"
EMOJI_DOT_BLUE = "🔹"
EMOJI_DOT_ORANGE = "🔸"
