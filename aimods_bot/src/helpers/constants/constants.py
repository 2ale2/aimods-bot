import re

from aimods_bot.src.helpers.constants.models import DisplayItem
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json

TOPICS = get_data_from_json("forum_topics")
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

_commands = get_data_from_json("commands")

echo_pattern = re.compile(_commands["echo"]["pattern"], re.IGNORECASE)

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

PLATFORM_ICONS = {
    "android": "🤖",
    "windows": "💻",
    "ios": "🍏",
    "macos": "🖥"
}

CATEGORY_DETAILS = {
    "android": {
        "app": {
            "label": "Android",
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
            "icons": "🎹"
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

REQUEST_FLOWS = {
    "android": {
        "app": {
            "flow": ["name", "link", "version", "functionalities"],
            "back_data": ["back_main", "back_name", "back_version", "back_functionalities"]
        }
    },
    "windows": {
        "software": {
            "flow": ["name", "link", "version", "functionalities"],
            "back_data": ["back_category", "back_name", "back_version", "back_functionalities"]
        },
        "game": {
            "flow": ["name", "link", "version", "functionalities", "steamtools"],
            "back_data": ["back_category", "back_name", "back_version", "back_functionalities", "back_steamtools"]
        },
        "daw": {
            "flow": ["name", "link", "version"],
            "back_data": ["back_category", "back_name", "back_link", "back_version"]
        },
        "adobe": {
            "flow": ["name", "version", "functionalities"],
            "back_data": ["back_category", "back_name", "back_version", "back_functionalities"]
        }
    },
    "ios": {
        "app": {
            "flow": ["name", "link", "version", "functionalities"],
            "back_data": ["back_main", "back_name", "back_version", "back_functionalities"]
        }
    },
    "macos": {
        "software": {
            "flow": ["name", "link", "version", "functionalities"],
            "back_data": ["back_category", "back_name", "back_version", "back_functionalities"]
        },
        "daw": {
            "flow": ["name", "link", "version"],
            "back_data": ["back_category", "back_name", "back_link", "back_version"]
        }
    }
}
