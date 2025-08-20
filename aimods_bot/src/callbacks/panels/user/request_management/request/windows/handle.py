import json
from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal, NamedTuple
from enum import Enum

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, ContextTypes

from aimods_bot.src.callbacks.panels.user.request_management.request.route import user_request_route
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, edit_message_safely
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.constants.constants import PLATFORM_ICONS, WINDOWS_CATEGORY_ICONS
from aimods_bot.src.helpers.constants.models import RequestStatuses as RS
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("request_handler")


class Platform(Enum):
    ANDROID = "android"
    IOS = "ios"
    WINDOWS = "windows"
    MACOS = "macos"


class RequestField(Enum):
    NAME = "name"
    LINK = "link"
    VERSION = "version"
    FUNCTIONALITIES = "functionalities"
    STEAMTOOLS = "steamtools"


class Category(Enum):
    class WindowsCategory(Enum):
        GAME = "game"
        DAW = "daw"
        ADOBE = "adobe"
        SOFTWARE = "software"


class MessageTemplate(NamedTuple):
    android_ios: str
    game: str
    daw: str
    software: str


FIELD_MESSAGES = {
    RequestField.NAME: MessageTemplate(
        android_ios="🔹 Indica il <b>nome dell'app</b> che vorresti richiedere.",
        game="🔹 Indica il <b>nome del gioco</b> che vorresti richiedere.",
        software="🔹 Indica il <b>nome del software</b> che vorresti richiedere.",
        daw="🔹 Indica il <b>nome della DAW o del Plug-In</b> che vorresti richiedere."
    ),
    RequestField.LINK: MessageTemplate(
        android_ios="🔹 Indica il <b>link dell'app</b> che vorresti richiedere.",
        game="🔹 Indica il <b>link del gioco</b> che vorresti richiedere.",
        software="🔹 Indica il <b>link del software</b> che vorresti richiedere.",
        daw="🔹 Indica il <b>link della DAW o del Plug-In</b> che vorresti richiedere."
    ),
    RequestField.VERSION: MessageTemplate(
        android_ios="🔹 Indica la <b>versione dell'app</b> che vorresti richiedere.",
        game="🔹 Indica la <b>versione del gioco</b> che vorresti richiedere.",
        software="🔹 Indica la <b>versione del software</b> che vorresti richiedere.",
        daw="🔹 Indica la <b>versione della DAW o del Plug-In</b> che vorresti richiedere."
    ),
    RequestField.FUNCTIONALITIES: MessageTemplate(
        android_ios="🔹 Indica le <b>funzionalità dell'app</b> che vorresti sbloccare.",
        game="🔹 Indica le <b>funzionalità del gioco</b> che vorresti sbloccare.",
        software="🔹 Indica le <b>funzionalità del software</b> che vorresti sbloccare.",
        daw="🔹 Indica le <b>funzionalità della DAW o del Plug-In</b> che vorresti richiedere."
    )
}

PLATFORM_DISPLAY_NAMES = {
    Platform.ANDROID: "Android",
    Platform.WINDOWS: "Windows",
    Platform.IOS: "iOS",
    Platform.MACOS: "MacOS"
}

CONVERSATION_STATES = {
    RequestField.NAME: RCS.EDIT_NAME,
    RequestField.LINK: RCS.EDIT_LINK,
    RequestField.VERSION: RCS.EDIT_VERSION,
    RequestField.FUNCTIONALITIES: RCS.EDIT_FUNCTIONALITIES
}

BACK_CALLBACKS = {
    "android": {
        "name": "back_main",
        "link": "back_name",
        "version": "back_link",
        "functionalities": "back_version"
    },
    "windows": {
        "game": {
            "name": "back_catagory",
            "link": "back_name",
            "version": "back_link",
            "functionalities": "back_version",
            "steamtools": "back_functionalities"
        },
        "adobe": {
            "name": "back_catagory",
            "version": "back_name",
            "functionalities": "back_version",
        },
        "daw": {
            "name": "back_catagory",
            "version": "back_name",
            "link": "back_version",
            "functionalities": "back_link"
        },
        "software": {
            "name": "back_main",
            "link": "back_name",
            "version": "back_link",
            "functionalities": "back_version"
        }
    }
}


@dataclass
class RequestData:
    """Rappresenta i dati di una richiesta in modo strutturato"""
    platform: Platform
    category: Category = None
    name: Optional[str] = None
    link: Optional[str] = None
    version: Optional[str] = None
    functionalities: Optional[str] = None
    steamtools: Optional[bool] = None
    editing: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte a dizionario escludendo il campo editing"""
        return {k: v for k, v in self.__dict__().items() if k != 'editing'}

    def get_category(self) -> Optional[Category]:
        """Determina la categoria per piattaforme Windows"""
        return self.category

    def get_platform(self) -> Platform:
        """Ritona la piattaforma"""
        return self.platform

    def get_item_type(self) -> str:
        """Restituisce il tipo di item basato sulla piattaforma e categoria"""
        category = self.get_category()
        if self.platform in (Platform.ANDROID.value, Platform.IOS.value):
            return "dell'app"
        elif category in (Category.WindowsCategory.GAME):
            return "del gioco"
        elif category in (Category.WindowsCategory.DAW):
            return "della DAW o del Plug-In"
        else:
            return "del software"

    def __dict__(self):
        """Override per supportare la serializzazione JSON"""
        return {
            'platform': self.platform,
            'category': self.category,
            'name': self.name,
            'link': self.link,
            'version': self.version,
            'functionalities': self.functionalities,
            'steamtools': self.steamtools,
            'editing': self.editing
        }


class RequestDataManager:
    """Gestisce i dati della richiesta in modo centralizzato"""

    @staticmethod
    def initialize_request(
            context: CallbackContext,
            platform: Platform,
            category: Optional[Category]
    ) -> None:
        """Inizializza una nuova richiesta nel context"""
        request_data = RequestData(
            platform=platform,
            category=category
        )
        context.chat_data["new_request"] = request_data
        logger.info(f"Initialized new request for platform: {platform}")

    @staticmethod
    async def request_detail(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            detail: Literal["name", "link", "version", "functionalities", "steamtools"]
    ):
        request_data = RequestDataManager.get_request_data(context)
        platform = request_data.get_platform()
        category = request_data.get_category()
        text = MessageBuilder.build_request_summary(request_data=request_data)

        if detail == RequestField.STEAMTOOLS.value:
            link_steamtools = "https://t.me/c/1523566735/13066"
            text += f"\n🔹 Accetteresti anche i file <a href=\"{link_steamtools}\">Steam Tools</a>?"
        else:
            field_enum = RequestField(detail)
            message_template = FIELD_MESSAGES[field_enum]

            if request_data.platform in (Platform.ANDROID.value, Platform.IOS.value):
                text += f"\n{message_template.android_ios}"
            elif category == Category.WindowsCategory.GAME:
                text += f"\n{message_template.game}"
            elif category == Category.WindowsCategory.DAW:
                text += f"\n{message_template.daw}"
            else:
                text += f"\n{message_template.software}"

        keyboard = KeyboardBuilder.get_back_keyboard(
            callback_data=back_data,
            steamtools_keyboard=(detail == RequestField.STEAMTOOLS.value)
        )

        await edit_message_safely(
            context=context,
            message_id=context.chat_data["bot_message_id"],
            chat_id=update.effective_message.chat_id,
            text=text,
            keyboard=keyboard
        )

    @staticmethod
    async def request_detail_to_edit(
            update: Update,
            context: CallbackContext
    ):
        await update.callback_query.answer()
        detail = update.callback_query.data.split("_")[1]
        request_data = RequestDataManager.get_request_data(context)

        RequestDataManager.update_field(context, "editing", detail)

        # Costruisci il messaggio
        field_enum = RequestField(detail)
        message_template = FIELD_MESSAGES[field_enum]

        if request_data.platform in (Platform.ANDROID.value, Platform.IOS.value):
            field_message = message_template.android_ios
        elif request_data.game:
            field_message = message_template.game
        else:
            field_message = message_template.software

        text = MessageBuilder.build_request_summary(
            request_data=request_data,
            editing_field=detail
        )
        text += f"\n{field_message}"

        keyboard = KeyboardBuilder.get_back_keyboard("no_edit")

        await edit_message_safely(
            context=context,
            message_id=context.chat_data["bot_message_id"],
            chat_id=update.effective_chat.id,
            text=text,
            keyboard=keyboard)

        return CONVERSATION_STATES[field_enum]

    @staticmethod
    def get_request_data(context: CallbackContext) -> RequestData:
        """Ottiene i dati della richiesta corrente"""
        data = context.chat_data.get("new_request")

        # Migrazione da dict legacy a RequestData
        if isinstance(data, dict):
            request_data = RequestData(**data)
            context.chat_data["new_request"] = request_data
            return request_data

        return data

    @staticmethod
    def update_field(context: CallbackContext, field: str, value: Any) -> None:
        """Aggiorna un campo specifico della richiesta"""
        request_data = RequestDataManager.get_request_data(context)
        setattr(request_data, field, value)
        logger.debug(f"Updated field {field} with value: {value}")

    @staticmethod
    async def confirm_request(
            update: Update,
            context: CallbackContext,
            platform: Literal["android", "ios", "windows", "macos"]
    ):
        """Conferma e salva la richiesta nel database"""
        uid = update.effective_user.id
        request_data = RequestDataManager.get_request_data(context)

        request_for_db = request_data.to_dict()
        request_for_db_str = json.dumps(request_for_db)

        query = """
                INSERT INTO requests (id, platform, content, user_id, status, issued_at)
                VALUES (DEFAULT, $1, $2, $3, DEFAULT, DEFAULT) 
                RETURNING id"""

        result = await fetch_query(
            query=query,
            params=[platform, request_for_db_str, uid]
        )

        if not result:
            raise Exception("Errore durante l'inserimento della richiesta")

        inserted_id = dict(result[0])["id"]
        logger.info(f"Request inserted with ID: {inserted_id} for user: {uid}")

        request_for_db.update({
            "status": RS.PENDING,
            "id": inserted_id
        })

        RequestDataManager.insert_request(context, request_data, request_for_db)

    @staticmethod
    def insert_request(
            context: CallbackContext,
            request_data: RequestData,
            request_for_db: Dict[str, Any]
    ):
        """Aggiorna le richieste dell'utente nel context"""
        platform = request_data.platform

        if platform not in (Platform.WINDOWS.value, Platform.MACOS.value):
            context.user_data["requests"][platform].append(request_for_db)
        else:
            category = request_data.get_category()
            if category:
                context.user_data["requests"][platform][category.value].append(request_for_db)

    @staticmethod
    def cleanup_request(context: CallbackContext) -> None:
        """Pulisce i dati della richiesta dal context"""
        context.chat_data.pop("new_request", None)
        context.chat_data.pop("bot_message_id", None)


class KeyboardBuilder:
    """Costruisce keyboard per le diverse fasi"""

    @staticmethod
    def get_back_keyboard(
            request_data: RequestData,
            context: ContextTypes.DEFAULT_TYPE,
            detail: Literal["name", "link", "version", "functionalities", "steamtools"],
            steamtools_keyboard: bool = False
    ) -> InlineKeyboardMarkup:
        """Keyboard semplice con solo tasto indietro, oppure la tastiera completa nel caso dei giochi"""
        platform = request_data.platform
        category = request_data.get_category()
        keyboard = [[
            InlineKeyboardButton(text="🔙 Indietro", callback_data=callback_data)
        ]]

        if steamtools_keyboard:
            keyboard.insert(0, [
                InlineKeyboardButton(text="🟢 Sì", callback_data="steamtools_yes"),
                InlineKeyboardButton(text="🔴 No", callback_data="steamtools_no"),
            ])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_review_keyboard(
            context: ContextTypes.DEFAULT_TYPE,
            game: bool = False,
            daw: bool = False,
            adobe: bool = False
    ) -> InlineKeyboardMarkup:
        """Keyboard per la review finale della richiesta"""
        request_data = RequestDataManager.get_request_data(context)
        keyboard = [[InlineKeyboardButton(text="1️⃣ Nome", callback_data="edit_name")]]

        if adobe:
            keyboard.insert(1, [
                InlineKeyboardButton(text="2️⃣ Versione", callback_data="edit_version"),
                InlineKeyboardButton(text="3️⃣ Funzionalità", callback_data="edit_functionalities")
            ])
            keyboard.insert(2, [
                InlineKeyboardButton(text="✅ Conferma", callback_data="confirm_request"),
                InlineKeyboardButton(text="❌ Annulla", callback_data="back_main")
            ])
        else:
            keyboard[0].insert(1, InlineKeyboardButton(text="2️⃣ Link", callback_data="edit_link"))
            keyboard.insert(1, [InlineKeyboardButton(text="3️⃣ Versione", callback_data="edit_version")])

            if not daw:
                keyboard[1].insert(1, InlineKeyboardButton(
                    text="4️⃣ Funzionalità",
                    callback_data="edit_functionalities"
                ))

            if game:
                steamtools = request_data.steamtools
                steamtools_data = "steamtools_yes" if not steamtools else "steamtools_no"
                keyboard.insert(2, [InlineKeyboardButton(text="5️⃣ SteamTools", callback_data=steamtools_data)])

            keyboard.insert(3, [
                InlineKeyboardButton(text="✅ Conferma", callback_data="confirm_request"),
                InlineKeyboardButton(text="❌ Annulla", callback_data="back_main")
            ])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_confirmation_keyboard() -> InlineKeyboardMarkup:
        """Keyboard per la conferma finale"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(text="♟ Gestisci Richieste", callback_data="users/manage_requests"),
                InlineKeyboardButton(text="🔙 Indietro", callback_data="users")
            ]
        ])

    @staticmethod
    def get_back_callback_data(
            platform: Literal["android", "windows", "ios", "macos"],
            category: Optional[Category],
            detail: Literal["name", "link", "version", "functionalities", "steamtools"]
    ):
        if platform in ("windows", "macos"):
            return BACK_CALLBACKS[platform][category.value][detail]
        return BACK_CALLBACKS[platform][detail]


class MessageBuilder:
    """Costruisce messaggi per le diverse fasi della conversazione"""

    @staticmethod
    def build_request_summary(
            request_data: RequestData,
            editing_field: Optional[str] = None
    ) -> str:
        """Costruisce il riepilogo della richiesta con evidenziazione del campo in editing"""
        header = MessageBuilder._build_header(request_data)

        fields = MessageBuilder._build_fields(request_data, editing_field)

        return f"{header}\n\n{fields}\n" if fields else f"{header}\n"

    @staticmethod
    def _build_header(request_data: RequestData) -> str:
        """Costruisce l'intestazione del messaggio"""
        platform = request_data.get_platform()
        category = request_data.get_category()

        if platform not in (Platform.WINDOWS, Platform.MACOS):
            icon = PLATFORM_ICONS[platform]
            platform_name = PLATFORM_DISPLAY_NAMES[platform]
            return f"{icon} <b>Nuova Richiesta – {platform_name}</b>"
        else:
            category_icons = {
                Platform.WINDOWS: WINDOWS_CATEGORY_ICONS
            }
            category_names = {
                Platform.WINDOWS: {
                    Category.WindowsCategory.GAME: "Gioco",
                    Category.WindowsCategory.DAW: "DAW",
                    Category.WindowsCategory.ADOBE: "Adobe",
                    Category.WindowsCategory.SOFTWARE: "Software"
                }
            }
            icon = category_icons[platform][category]
            name = category_names[platform][category]

            return f"{icon} <b>Nuova Richiesta – {name}</b>"

    @staticmethod
    def _build_fields(request_data: RequestData, editing_field: Optional[str] = None) -> str:
        """Costruisce la lista dei campi della richiesta"""
        platform = request_data.get_platform()
        category = request_data.get_category()

        fields = []

        field_config = MessageBuilder._get_field_config(category=category)

        for field_name, field_info in field_config.items():
            value = getattr(request_data, field_name, None)
            if MessageBuilder._should_display_field(field_name, value):
                display_value = MessageBuilder._format_field_value(field_name, value, editing_field, field_info)
                fields.append(f"      🔸 <u>{field_info['label']}</u> – {display_value}")

        return "\n".join(fields)

    @staticmethod
    def _get_field_config(category: Optional[Category.WindowsCategory]) -> Dict[str, Dict[str, Any]]:
        """Ottiene la configurazione dei campi basata sul tipo di richiesta"""
        if not category:
            return {
                'name': {'label': 'Nome', 'format': 'text'},
                'link': {'label': 'Link', 'format': 'link'},
                'version': {'label': 'Versione', 'format': 'code'},
                'functionalities': {'label': 'Funzionalità', 'format': 'text'}
            }

        config = {
            'name': {'label': 'Nome', 'format': 'text'},
        }

        if category not in (Category.WindowsCategory.ADOBE,):
            config['link'] = {'label': 'Link', 'format': 'link'}

        config['version'] = {'label': 'Versione', 'format': 'code'}

        if category not in (Category.WindowsCategory.DAW,):
            config['functionalities'] = {'label': 'Funzionalità', 'format': 'text'}

        if category not in (Category.WindowsCategory.GAME,):
            config['steamtools'] = {'label': 'Steam Tools', 'format': 'bool'}

        return config


    @staticmethod
    def _should_display_field(field_name: str, value: Any) -> bool:
        """Determina se un campo deve essere visualizzato"""
        if field_name == 'steamtools':
            return value is not None
        return value is not None and len(str(value)) > 0

    @staticmethod
    def _format_field_value(
            field_name: str,
            value: Any,
            editing_field: Optional[str],
            field_info: Dict[str, Any]
    ) -> str:
        """Formatta il valore di un campo"""
        if editing_field == field_name:
            return "<i><b>Editing...</b></i>"

        format_type = field_info['format']

        if format_type == 'text':
            return f"<i>{value}</i>"
        elif format_type == 'code':
            return f"<code>{value}</code>"
        elif format_type == 'link':
            return f"🔗 <i><a href='{value}'>Link</a></i>"
        elif format_type == 'bool':
            return f"<i>{'Sì' if value else 'No'}</i>"

        return str(value)


class InputHandler:
    """Gestisce l'input utente delle richieste."""

    @staticmethod
    async def handle_input(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            detail: Literal["name", "link", "version", "functionalities", "steamtools"]
    ):
        """Gestisce l'input dell'utente per i diversi campi"""
        if not update.callback_query:
            await safe_delete(update, context)

        data = InputHandler._extract_data(update, detail)
        RequestDataManager.update_field(context=context, field=detail, value=data)
        logger.debug(f"Handled input for {detail}: {data}")

    @staticmethod
    def _extract_data(update: Update, detail: str):
        """Estrae i dati dall'update in base al tipo di campo"""
        if detail == RequestField.LINK.value:
            entity = update.effective_message.entities[0]
            return update.effective_message.text[entity.offset:entity.offset + entity.length]
        elif detail == RequestField.STEAMTOOLS.value:
            return update.callback_query.data == "steamtools_yes"
        else:
            return update.effective_message.text


async def handle_back_to_main(update: Update, context: CallbackContext):
    """Gestisce il ritorno al menu principale"""
    await user_request_route(update=update, context=context, path=[])
    return RCS.MAIN_BACKER
