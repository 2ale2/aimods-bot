import asyncio
import json
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import MessageEntityType

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import MissingParameterException
from aimods_bot.src.core.pydantic import Request, Architecture
from aimods_bot.src.helpers.constants.constants import CATEGORY_DETAILS, REQUEST_DETAILS_CONFIG, Platform, Category, \
    RequestField, Arch
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.models.utils import MessageTemplate
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, edit_message_safely
from aimods_bot.src.helpers.utils.user_utils import check_auth

log = logger.getChild(__name__)

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
        app="🔹 Indica il <b>link ufficilae dell'app</b>.",
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




class KeyboardBuilder:
    """Costruisce keyboard per le diverse fasi"""

    @staticmethod
    def get_back_keyboard(
            request_data: Request,
            detail: Optional[RequestField],
            bool_keyboard: bool = False,
            callback_data: str = None
    ) -> InlineKeyboardMarkup:
        """Keyboard semplice con solo tasto indietro, oppure la tastiera completa nel caso dei giochi"""
        platform = request_data.platform
        category = request_data.category
        callback_data = callback_data or KeyboardBuilder.get_back_callback_data(
            platform=platform,
            category=category,
            detail=detail
        )

        keyboard = [[
            InlineKeyboardButton(text="🔙 Indietro", callback_data=callback_data)
        ]]

        if bool_keyboard:
            keyboard.insert(0, [
                InlineKeyboardButton(text="🟢 Sì", callback_data="bool_yes"),
                InlineKeyboardButton(text="🔴 No", callback_data="bool_no"),
            ])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_review_keyboard(request_data: Request) -> InlineKeyboardMarkup:
        """
        Tastiera per la review finale, generata in modo dichiarativo:
        - definisce l'ordine dei campi per categoria
        - crea pulsanti numerati automaticamente (1️⃣ 2️⃣ 3️⃣ ...)
        - inserisce 'SteamTools' solo per i giochi, con callback di toggle
        - aggiunge sempre '✅ Conferma' e '❌ Annulla' in fondo
        """
        category = request_data.category
        cat = category.value if category else "software"

        order_by_category = {
            "app": ["name", "link", "version", "functionalities"],
            "software": ["name", "link", "version", "functionalities"],
            "adobe": ["name", "version", "functionalities", "arch"],
            "daw": ["name", "link", "version"],
            "game": ["name", "link", "version", "functionalities", "steamtools"],
        }

        labels = {
            "name": "Nome",
            "link": "Link",
            "version": "Versione",
            "functionalities": "Funzionalità",
            "steamtools": "SteamTools",
            "arch": "CPU ARM"
        }

        edit_callbacks = {
            "name": "edit_name",
            "link": "edit_link",
            "version": "edit_version",
            "functionalities": "edit_functionalities",
            "arch": "edit_arch"
        }

        def num_emoji(i: int) -> str:
            digits = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
            return digits[i] if 0 <= i < len(digits) else f"{i}."

        def chunk(rows, n=2):
            return [rows[i:i + n] for i in range(0, len(rows), n)]

        fields = order_by_category.get(cat, order_by_category["software"])

        buttons = []
        idx = 1
        for field in fields:
            if field == "steamtools":
                steamtools = bool(request_data.steamtools)
                cb = "bool_no:steamtools" if steamtools else "bool_yes:steamtools"
                buttons.append(
                    InlineKeyboardButton(text=f"{num_emoji(idx)} {labels[field]}", callback_data=cb)
                )
            elif field == "arch":
                arch = request_data.arch.arm_bool
                cb = "bool_no:arch" if arch else "bool_yes:arch"
                buttons.append(
                    InlineKeyboardButton(text=f"{num_emoji(idx)} {labels[field]}", callback_data=cb)
                )
            else:
                buttons.append(
                    InlineKeyboardButton(text=f"{num_emoji(idx)} {labels[field]}", callback_data=edit_callbacks[field])
                )
            idx += 1

        keyboard_rows = [buttons] if len(buttons) <= 2 else chunk(buttons, 2)

        keyboard_rows.append([
            InlineKeyboardButton(text="✅ Conferma", callback_data="confirm_request"),
            InlineKeyboardButton(text="❌ Annulla", callback_data="back_main"),
        ])

        return InlineKeyboardMarkup(keyboard_rows)

    @staticmethod
    def get_confirmation_keyboard() -> InlineKeyboardMarkup:
        """Keyboard per la conferma finale"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(text="♟ Gestisci Richieste", callback_data="start/view_requests"),
                InlineKeyboardButton(text="🏠 Torna alla Home", callback_data="start")
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
            request_data: Request,
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
    def _build_header(request_data: Request) -> str:
        """Costruisce l'intestazione del messaggio"""
        platform = request_data.platform
        category = request_data.category

        category_item = CATEGORY_DETAILS[platform.value][category.value]

        icon = category_item["icon"]
        name = category_item["label"]

        return f"{icon} <b>Nuova Richiesta – {name}</b>"

    @staticmethod
    def _build_fields(request_data: Request, editing_field: Optional[str] = None) -> str:
        """Costruisce la lista dei campi della richiesta"""
        category = request_data.category
        platform = request_data.platform

        fields = []

        field_config = MessageBuilder._get_field_config(platform=platform, category=category)

        for field_name, field_info in field_config.items():
            value = getattr(request_data, field_name, None)
            if isinstance(value, Architecture):
                value = value.arm_bool
            if MessageBuilder._should_display_field(field_name, value):
                display_value = MessageBuilder._format_field_value(field_name, value, editing_field, field_info)
                fields.append(f"      🔸 <u>{field_info['label']}</u> – {display_value}")

        return "\n".join(fields)

    @staticmethod
    def _get_field_config(platform: Platform, category: Category) -> Dict[str, Dict[str, Any]]:
        """Ottiene la configurazione dei campi basata sul tipo di richiesta"""
        return REQUEST_DETAILS_CONFIG[platform.value][category.value]

    @staticmethod
    def _should_display_field(field_name: str, value: Any) -> bool:
        """Determina se un campo deve essere visualizzato"""
        if field_name in ('steamtools', 'arch'):
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
            return f"<i>{'✔️' if value else '✖'}</i>"

        return str(value)


class InputHandler:
    """Gestisce l'input utente delle richieste."""

    @staticmethod
    async def handle_input(
            update: Update,
            context: CustomContext
    ):
        """Gestisce l'input dell'utente per i diversi campi"""
        if not update.callback_query:
            await safe_delete(update, context)
        else:
            await update.callback_query.answer()

        request_data = RequestDataManager.get_request_data(context)
        detail = request_data.editing or request_data.requesting
        if not isinstance(detail, RequestField):
            detail = RequestField(detail)

        data = InputHandler._extract_data(update, detail)

        if detail == RequestField.ARCH:
            data = "arm" if data is True else "x86"

        RequestDataManager.update_field(context=context, field=detail.value, value=data)
        log.info(f"Handled input for {detail}: {data}")

    @staticmethod
    def _extract_data(update: Update, detail: RequestField):
        """Estrae i dati dall'update in base al tipo di campo"""
        if detail == RequestField.LINK:
            for el in update.effective_message.entities:
                if el.type == MessageEntityType.URL:
                    entity = el
            # entity è necessariamente definita a causa del filtro dell'handler
            # noinspection PyUnboundLocalVariable
            return update.effective_message.text[entity.offset:entity.offset + entity.length]
        elif detail in (RequestField.STEAMTOOLS, RequestField.ARCH):
            if not update.callback_query:
                raise MissingParameterException("Per il valore SteamTools e ARCH ci deve essere una callback query.")
            return update.callback_query.data.startswith("bool_yes")
        else:
            return update.effective_message.text
