import json
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, NamedTuple, Union

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode, MessageEntityType
from telegram.ext import ContextTypes, ConversationHandler

from aimods_bot.src.helpers.constants.constants import CATEGORY_DETAILS, REQUEST_FLOWS
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.constants.models import RequestStatuses as RS
from aimods_bot.src.helpers.constants.models import CanUserRequest
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, edit_message_safely
from aimods_bot.src.helpers.utils.user_utils import create_empty_user_data

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


class WindowsCategory(Enum):
    GAME = "game"
    DAW = "daw"
    ADOBE = "adobe"
    SOFTWARE = "software"


class AndroidCategory(Enum):
    APP = "app"


class IOSCategory(Enum):
    APP = "app"


class MacOSCategory(Enum):
    SOFTWARE = "software"
    DAW = "daw"


Category = Union[WindowsCategory, AndroidCategory, IOSCategory, MacOSCategory]


class MessageTemplate(NamedTuple):
    app: str
    game: str
    daw: str
    software: str


FIELD_MESSAGES = {
    RequestField.NAME: MessageTemplate(
        app="🔹 Indica il <b>nome dell'app</b> che vorresti richiedere.",
        game="🔹 Indica il <b>nome del gioco</b> che vorresti richiedere.",
        software="🔹 Indica il <b>nome del software</b> che vorresti richiedere.",
        daw="🔹 Indica il <b>nome della DAW o del Plug-In</b> che vorresti richiedere."
    ),
    RequestField.LINK: MessageTemplate(
        app="🔹 Indica il <b>link dell'app</b> che vorresti richiedere.",
        game="🔹 Indica il <b>link del gioco</b> che vorresti richiedere.",
        software="🔹 Indica il <b>link del software</b> che vorresti richiedere.",
        daw="🔹 Indica il <b>link della DAW o del Plug-In</b> che vorresti richiedere."
    ),
    RequestField.VERSION: MessageTemplate(
        app="🔹 Indica la <b>versione dell'app</b> che vorresti richiedere.",
        game="🔹 Indica la <b>versione del gioco</b> che vorresti richiedere.",
        software="🔹 Indica la <b>versione del software</b> che vorresti richiedere.",
        daw="🔹 Indica la <b>versione della DAW o del Plug-In</b> che vorresti richiedere."
    ),
    RequestField.FUNCTIONALITIES: MessageTemplate(
        app="🔹 Indica le <b>funzionalità dell'app</b> che vorresti sbloccare.",
        game="🔹 Indica le <b>funzionalità del gioco</b> che vorresti sbloccare.",
        software="🔹 Indica le <b>funzionalità del software</b> che vorresti sbloccare.",
        daw="🔹 Indica le <b>funzionalità della DAW o del Plug-In</b> che vorresti richiedere."
    )
}

CONVERSATION_STATES = {
    RequestField.NAME: RCS.EDIT_NAME,
    RequestField.LINK: RCS.EDIT_LINK,
    RequestField.VERSION: RCS.EDIT_VERSION,
    RequestField.FUNCTIONALITIES: RCS.EDIT_FUNCTIONALITIES
}


@dataclass
class RequestData:
    """Rappresenta i dati di una richiesta in modo strutturato"""
    platform: Platform = None
    category: Category = None
    name: Optional[str] = None
    link: Optional[str] = None
    version: Optional[str] = None
    functionalities: Optional[str] = None
    steamtools: Optional[bool] = None
    requesting: RequestField = None
    editing: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte a dizionario escludendo il campo editing"""
        return {k: v for k, v in self.__dict__().items() if k not in ('requesting', 'editing')}

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
        elif category in (WindowsCategory.GAME,):
            return "del gioco"
        elif category in (WindowsCategory.DAW,):
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
            context: ContextTypes.DEFAULT_TYPE,
            platform: Platform = None,
            category: Category = None
    ) -> None:
        """Inizializza una nuova richiesta nel context"""
        request_data = RequestData(
            platform=platform,
            category=category
        )

        if "new_request" in context.chat_data:
            RequestDataManager.cleanup_request(context=context)

        context.chat_data["new_request"] = request_data

        if platform:
            if category:
                log_text = f"Initialized new request for platform (category): {platform.value} ({category.value})"
            else:
                log_text = f"Initialized new request for platform ({platform.value})"
        else:
            log_text = f"Initialized new empty request"

        log.info(log_text)

    @staticmethod
    async def request_detail(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            detail: RequestField
    ):
        request_data = RequestDataManager.get_request_data(context)
        category = request_data.get_category()
        text = MessageBuilder.build_request_summary(request_data=request_data)

        RequestDataManager.update_field(context=context, field="requesting", value=detail)

        if detail == RequestField.STEAMTOOLS:
            link_steamtools = "https://t.me/c/1523566735/13066"
            text += f"\n🔹 Accetteresti anche i file <a href=\"{link_steamtools}\">Steam Tools</a>?"
        else:
            field_enum = RequestField(detail)
            message_template = FIELD_MESSAGES[field_enum]

            if category.value == "app":
                text += f"\n{message_template.app}"
            elif category.value == "game":
                text += f"\n{message_template.game}"
            elif category.value == "daw":
                text += f"\n{message_template.daw}"
            else:
                text += f"\n{message_template.software}"

        keyboard = KeyboardBuilder.get_back_keyboard(
            request_data=request_data,
            detail=detail,
            steamtools_keyboard=(detail == RequestField.STEAMTOOLS)
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
            context: ContextTypes.DEFAULT_TYPE
    ):
        await update.callback_query.answer()
        detail = update.callback_query.data.split("_")[1]
        request_data = RequestDataManager.get_request_data(context)
        category = request_data.get_category()

        RequestDataManager.update_field(context, "editing", detail)

        field_enum = RequestField(detail)
        message_template = FIELD_MESSAGES[field_enum]

        if category.value == "app":
            field_message = message_template.app
        elif category.value == "game":
            field_message = message_template.game
        elif category.value == "daw":
            field_message = message_template.daw
        else:
            field_message = message_template.software

        text = MessageBuilder.build_request_summary(
            request_data=request_data,
            editing_field=detail
        )
        text += f"\n{field_message}"

        keyboard = KeyboardBuilder.get_back_keyboard(
            request_data=request_data,
            detail=None,
            callback_data="no_edit"
        )

        await edit_message_safely(
            context=context,
            message_id=context.chat_data["bot_message_id"],
            chat_id=update.effective_chat.id,
            text=text,
            keyboard=keyboard)

        return CONVERSATION_STATES[field_enum]

    @staticmethod
    def get_request_data(context: ContextTypes.DEFAULT_TYPE) -> RequestData:
        """Ottiene i dati della richiesta corrente"""
        data = context.chat_data.get("new_request")

        # Migrazione da dict legacy a RequestData
        if isinstance(data, dict):
            request_data = RequestData(**data)
            context.chat_data["new_request"] = request_data
            return request_data

        return data

    @staticmethod
    def update_field(context: ContextTypes.DEFAULT_TYPE, field: str, value: Any) -> None:
        """Aggiorna un campo specifico della richiesta"""
        request_data = RequestDataManager.get_request_data(context)
        setattr(request_data, field, value)
        log.debug(f"Updated field {field} with value: {value}")

    @staticmethod
    async def recheck_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
        request_data = RequestDataManager.get_request_data(context)

        if update.callback_query:
            data = update.callback_query.data
            if data in ("steamtools_yes", "steamtools_no"):
                await InputHandler.handle_input(update=update, context=context)

        text = MessageBuilder.build_request_summary(request_data=request_data)
        text += ("\n🔹 Verifica i dettagli della tua richiesta. "
                 "<b>Premi uno dei tasti per modificare un elemento</b>, oppure <b>conferma per inviarla</b>.\n\n"
                 "<blockquote>⚠️ Assicurati che i dettagli siano <b>chiari</b>, "
                 "altrimenti <b>la tua richiesta sarà bocciata</b>.</blockquote>")

        keyboard = KeyboardBuilder.get_review_keyboard(request_data=request_data)

        await edit_message_safely(
            context=context,
            message_id=context.chat_data["bot_message_id"],
            chat_id=update.effective_chat.id,
            text=text,
            keyboard=keyboard
        )

        return RCS.CHECK_REQUEST

    @staticmethod
    async def confirm_request(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE
    ):
        """Conferma e salva la richiesta nel database"""
        uid = update.effective_user.id
        request_data = RequestDataManager.get_request_data(context)

        platform = request_data.get_platform()
        category = request_data.get_category()

        request_for_db = request_data.to_dict()
        request_for_db.pop('platform')
        request_for_db.pop('category')

        request_for_db_str = json.dumps(request_for_db)

        query = """
                INSERT INTO requests (id, platform, content, user_id, status, issued_at, category)
                VALUES (DEFAULT, $1, $2, $3, DEFAULT, DEFAULT, $4) 
                RETURNING id"""

        result = await fetch_query(
            query=query,
            params=[platform.value, request_for_db_str, uid, category.value]
        )

        if not result:
            raise Exception("Errore durante l'inserimento della richiesta")

        inserted_id = dict(result[0])["id"]
        log.info(f"Request inserted with ID: {inserted_id} for user: {uid}")

        request_for_db.update({
            "status": RS.PENDING,
            "id": inserted_id
        })

        RequestDataManager.insert_request(context, request_data, request_for_db)

        confirmation_text = MessageBuilder.build_confirmation_message()
        confirmation_keyboard = KeyboardBuilder.get_confirmation_keyboard()

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=context.chat_data["bot_message_id"],
            text=confirmation_text,
            reply_markup=confirmation_keyboard,
            parse_mode=ParseMode.HTML
        )

        RequestDataManager.cleanup_request(context=context)
        return ConversationHandler.END

    @staticmethod
    def insert_request(
            context: ContextTypes.DEFAULT_TYPE,
            request_data: RequestData,
            request_for_db: Dict[str, Any]
    ):
        """Aggiorna le richieste dell'utente nel context"""
        platform = request_data.get_platform()
        category = request_data.get_category()

        if "requests" not in context.user_data:
            create_empty_user_data(context=context, admin=False)

        context.user_data["requests"][platform.value][category.value].append(request_for_db)

    @staticmethod
    def cleanup_request(context: ContextTypes.DEFAULT_TYPE) -> None:
        """Pulisce i dati della richiesta dal context"""
        context.chat_data.pop("new_request", None)
        context.chat_data.pop("bot_message_id", None)


class KeyboardBuilder:
    """Costruisce keyboard per le diverse fasi"""

    @staticmethod
    def get_back_keyboard(
            request_data: RequestData,
            detail: Optional[RequestField],
            steamtools_keyboard: bool = False,
            callback_data: str = None
    ) -> InlineKeyboardMarkup:
        """Keyboard semplice con solo tasto indietro, oppure la tastiera completa nel caso dei giochi"""
        platform = request_data.platform
        category = request_data.get_category()
        callback_data = callback_data or KeyboardBuilder.get_back_callback_data(
            platform=platform,
            category=category,
            detail=detail
        )

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
            request_data: RequestData
    ) -> InlineKeyboardMarkup:
        """Keyboard per la review finale della richiesta"""
        category = request_data.get_category()

        if category.value == "app":
            keyboard = [
                [
                    InlineKeyboardButton(text="1️⃣ Nome", callback_data="edit_name"),
                    InlineKeyboardButton(text="2️⃣ Link", callback_data="edit_link")
                ],
                [
                    InlineKeyboardButton(text="3️⃣ Versione", callback_data="edit_version"),
                    InlineKeyboardButton(text="4️⃣ Funzionalità", callback_data="edit_functionalities")
                ]
            ]

        else:
            keyboard = [[InlineKeyboardButton(text="1️⃣ Nome", callback_data="edit_name")]]

            if category.value == "adobe":
                keyboard[0].append(InlineKeyboardButton(text="2️⃣ Versione", callback_data="edit_version"))
                keyboard.insert(1, [
                    InlineKeyboardButton(text="3️⃣ Funzionalità", callback_data="edit_functionalities")
                ])
            else:
                keyboard[0].insert(1, InlineKeyboardButton(text="2️⃣ Link", callback_data="edit_link"))
                keyboard.insert(1, [InlineKeyboardButton(text="3️⃣ Versione", callback_data="edit_version")])

                if category.value != "daw":
                    keyboard[1].insert(1, InlineKeyboardButton(
                        text="4️⃣ Funzionalità",
                        callback_data="edit_functionalities"
                    ))

                if category.value == "game":
                    steamtools = request_data.steamtools
                    steamtools_data = "steamtools_yes" if not steamtools else "steamtools_no"
                    keyboard.insert(2, [InlineKeyboardButton(text="5️⃣ SteamTools", callback_data=steamtools_data)])

        keyboard.append([
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
            platform: Platform,
            category: Optional[Category],
            detail: RequestField
    ):
        section = REQUEST_FLOWS[platform.value]
        flow_data = section[category.value]['flow']
        back_data = section[category.value]['back_data']

        ix = flow_data.index(detail.value)
        return back_data[ix]


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
    def build_confirmation_message():
        text = ("✅ <b>Richiesta Inviata Correttamente</b>\n\n"
                "🔹 Puoi controllare lo stato delle tue richieste dal pannello di controllo.")
        return text

    @staticmethod
    def _build_header(request_data: RequestData) -> str:
        """Costruisce l'intestazione del messaggio"""
        platform = request_data.get_platform()
        category = request_data.get_category()

        category_item = CATEGORY_DETAILS[platform.value][category.value]

        icon = category_item["icon"]
        name = category_item["label"]

        return f"{icon} <b>Nuova Richiesta – {name}</b>"

    @staticmethod
    def _build_fields(request_data: RequestData, editing_field: Optional[str] = None) -> str:
        """Costruisce la lista dei campi della richiesta"""
        category = request_data.get_category()
        platform = request_data.get_platform()

        fields = []

        field_config = MessageBuilder._get_field_config(platform=platform, category=category)

        for field_name, field_info in field_config.items():
            value = getattr(request_data, field_name, None)
            if MessageBuilder._should_display_field(field_name, value):
                display_value = MessageBuilder._format_field_value(field_name, value, editing_field, field_info)
                fields.append(f"      🔸 <u>{field_info['label']}</u> – {display_value}")

        return "\n".join(fields)

    @staticmethod
    def _get_field_config(platform: Platform, category: Category) -> Dict[str, Dict[str, Any]]:
        """Ottiene la configurazione dei campi basata sul tipo di richiesta"""
        configs = {
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
                    'functionalities': {'label': 'Funzionalità', 'format': 'text'}
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

        return configs[platform.value][category.value]

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
            context: ContextTypes.DEFAULT_TYPE
    ):
        """Gestisce l'input dell'utente per i diversi campi"""
        if not update.callback_query:
            await safe_delete(update, context)

        request_data = RequestDataManager.get_request_data(context)
        detail = request_data.editing or request_data.requesting
        if not isinstance(detail, RequestField):
            detail = RequestField(detail)

        data = InputHandler._extract_data(update, detail)

        RequestDataManager.update_field(context=context, field=detail.value, value=data)
        log.debug(f"Handled input for {detail}: {data}")

    @staticmethod
    def _extract_data(update: Update, detail: str):
        """Estrae i dati dall'update in base al tipo di campo"""
        if detail == RequestField.LINK:
            for el in update.effective_message.entities:
                if el.type == MessageEntityType.URL:
                    entity = el
            # entity è necessariamente definita a causa del filtro dell'handler
            # noinspection PyUnboundLocalVariable
            return update.effective_message.text[entity.offset:entity.offset + entity.length]
        elif detail == RequestField.STEAMTOOLS:
            return update.callback_query.data == "steamtools_yes"
        else:
            return update.effective_message.text


async def can_user_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> CanUserRequest:
    """Verifica se l'utente può fare richieste, per limiti di moderazione o imposti dalla gestione."""
    return CanUserRequest(
        yn=True,
        reason=None
    )
