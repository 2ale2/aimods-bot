import json
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import MessageEntityType
from telegram.ext import ConversationHandler

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.exceptions import MissingParameterException
from aimods_bot.src.core.pydantic import Request
from aimods_bot.src.helpers.constants.constants import CATEGORY_DETAILS, REQUEST_DETAILS_CONFIG, Platform, Category, \
    RequestField
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.constants.models import MessageTemplate
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, edit_message_safely

log = logger.getChild("request_handler")


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

REQUEST_FLOWS = get_data_from_json('request_conversation_flows')


class RequestDataManager:
    """Gestisce i dati della richiesta in modo centralizzato"""

    @staticmethod
    def initialize_request(
            context: CustomContext,
            platform: Optional[Platform] = None,
            category: Optional[Category] = None
    ):
        """
        (Re)inizializza una nuova richiesta nello stato della chat.
        - È sicura da richiamare più volte (idempotente).
        - Esegue il cleanup dello stato precedente, se presente.
        - Resetta flag/ID di messaggi e campo in editing.
        - Salva un timestamp di avvio richiesta.
        """
        chat = context.chat_data

        if chat.get("new_request") is not None:
            try:
                RequestDataManager.cleanup_request(context=context)
            except Exception as e:
                log.warning("cleanup_request failed: %s", e, exc_info=e)

        request_data = Request(platform=platform, category=category)
        chat["new_request"] = request_data.model_dump()

        log.info(
            "Initialized new request",
            extra={
                "platform": getattr(platform, "value", None),
                "category": getattr(category, "value", None),
            },
        )

    @staticmethod
    async def request_detail(
            update: Update,
            context: CustomContext,
            detail: RequestField
    ):
        request_data = RequestDataManager.get_request_data(context)
        category = request_data.category
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

        context.chat_data["bot_message_id"] = await edit_message_safely(
            context=context,
            message_id=context.chat_data["bot_message_id"],
            chat_id=update.effective_message.chat_id,
            text=text,
            keyboard=keyboard
        )

    @staticmethod
    async def request_detail_to_edit(
            update: Update,
            context: CustomContext
    ):
        if not update.callback_query:
            raise MissingParameterException("Manca la callback query in questo Update")

        try:
            await update.callback_query.answer()
        except Exception as e:
            log.warning(f"Non è stato possibile eseguire l'answer della cquery: {e}")

        # Expect: "edit_<field>"
        detail = update.callback_query.data.split("_")[1]
        request_data = RequestDataManager.get_request_data(context)
        category = request_data.category

        RequestDataManager.update_field(context, "editing", RequestField(detail))

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

        context.chat_data["bot_message_id"] = await edit_message_safely(
            context=context,
            message_id=context.chat_data["bot_message_id"],
            chat_id=update.effective_chat.id,
            text=text,
            keyboard=keyboard)

        return CONVERSATION_STATES[field_enum]

    @staticmethod
    def get_request_data(context: CustomContext) -> Request:
        """Ottiene i dati della richiesta corrente"""
        request = context.chat_data.get("new_request")
        return Request(**request)

    @staticmethod
    def update_field(context: CustomContext, field: str, value: Any) -> None:
        """Aggiorna un campo specifico della richiesta"""
        request_data = RequestDataManager.get_request_data(context)
        setattr(request_data, field, value)
        RequestDataManager.update_request_data(context, request_data)

        log.debug(f"Updated field {field} with value: {value}")

    @staticmethod
    def update_request_data(context: CustomContext, request_data: Request) -> None:
        context.chat_data["new_request"] = request_data.model_dump()

    @staticmethod
    async def recheck_request(update: Update, context: CustomContext):
        if update.callback_query:
            data = update.callback_query.data
            if data in ("steamtools_yes", "steamtools_no"):
                await InputHandler.handle_input(update=update, context=context)

        request_data = RequestDataManager.get_request_data(context)

        text = MessageBuilder.build_request_summary(request_data=request_data)
        text += ("\n🔹 Verifica i dettagli della tua richiesta. "
                 "<b>Premi uno dei tasti per modificare un elemento</b>, oppure <b>conferma per inviarla</b>.\n\n"
                 "<blockquote>⚠️ Assicurati che i dettagli siano <b>chiari</b>, "
                 "altrimenti <b>la tua richiesta sarà bocciata</b>.</blockquote>")

        keyboard = KeyboardBuilder.get_review_keyboard(request_data=request_data)

        context.chat_data["bot_message_id"] = await edit_message_safely(
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
            context: CustomContext
    ):
        """Conferma e salva la richiesta nel database"""
        request_data = RequestDataManager.get_request_data(context)

        await RequestDataManager.insert_request(
            update=update,
            context=context,
            request_data=request_data
        )

        confirmation_text = MessageBuilder.build_confirmation_message()
        confirmation_keyboard = KeyboardBuilder.get_confirmation_keyboard()

        context.chat_data["bot_message_id"] = await edit_message_safely(
            context=context,
            message_id=context.chat_data["bot_message_id"],
            chat_id=update.effective_chat.id,
            text=confirmation_text,
            keyboard=confirmation_keyboard
        )

        RequestDataManager.cleanup_request(context=context)
        return ConversationHandler.END

    # noinspection PyTypedDict
    @staticmethod
    async def insert_request(
            update: Update,
            context: CustomContext,
            request_data: Request
    ):
        """Aggiorna le richieste dell'utente nel context"""

        platform = request_data.platform
        category = request_data.category
        uid = update.effective_user.id

        request_for_db = request_data.model_dump()
        request_for_db.pop("platform", None)
        request_for_db.pop("category", None)
        request_for_db.pop("status", None)
        request_for_db.pop("requesting", None)
        request_for_db.pop("editing", None)
        request_for_db.pop("id", None)
        request_for_db.pop("user_id", None)
        request_for_db_str = json.dumps(request_for_db)

        query = """
                INSERT INTO requests (id, platform, content, user_id, status, issued_at, category)
                VALUES (DEFAULT, $1, $2, $3, DEFAULT, DEFAULT, $4)
                RETURNING id, issued_at"""

        result = await fetch_query(
            query=query,
            params=[platform.value, request_for_db_str, uid, category.value]
        )

        if not result:
            raise Exception(f"Errore durante l'inserimento della richiesta: \n\n{request_for_db}")

        inserted = dict(result[0])

        ix = int(inserted["id"])
        issued_at = inserted["issued_at"]

        context.pyd.active_requests.append(Request(
            id=ix,
            user_id=uid,
            # status = (default) RequestStatus.PENDING,
            issued_at=issued_at.isoformat(),
            platform=platform,
            category=category,
            name=request_for_db["name"],
            arch=request_for_db.get("arch", None),
            version=request_for_db.get("version", ""),
            link=request_for_db.get("link", ""),
            functionalities=request_for_db.get("functionalities", ""),
            steamtools=request_for_db.get("steamtools", False)
        ))

        log.info(f"Request inserted with ID {ix} for user {uid}")

    @staticmethod
    def cleanup_request(context: CustomContext) -> None:
        """Pulisce i dati della richiesta dal context"""
        context.chat_data.pop("new_request", None)
        context.chat_data.pop("bot_message_id", None)


class KeyboardBuilder:
    """Costruisce keyboard per le diverse fasi"""

    @staticmethod
    def get_back_keyboard(
            request_data: Request,
            detail: Optional[RequestField],
            steamtools_keyboard: bool = False,
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

        if steamtools_keyboard:
            keyboard.insert(0, [
                InlineKeyboardButton(text="🟢 Sì", callback_data="steamtools_yes"),
                InlineKeyboardButton(text="🔴 No", callback_data="steamtools_no"),
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
            "adobe": ["name", "version", "functionalities"],
            "daw": ["name", "link", "version"],
            "game": ["name", "link", "version", "functionalities", "steamtools"],
        }

        labels = {
            "name": "Nome",
            "link": "Link",
            "version": "Versione",
            "functionalities": "Funzionalità",
            "steamtools": "SteamTools",
        }

        edit_callbacks = {
            "name": "edit_name",
            "link": "edit_link",
            "version": "edit_version",
            "functionalities": "edit_functionalities"
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
                cb = "steamtools_no" if steamtools else "steamtools_yes"
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
                InlineKeyboardButton(text="♟ Gestisci Richieste", callback_data="users/manage_requests"),
                InlineKeyboardButton(text="🏠 Torna alla Home", callback_data="users")
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
        elif detail == RequestField.STEAMTOOLS:
            if not update.callback_query:
                raise MissingParameterException("Per il valore SteamTools ci deve essere una callback query.")
            return update.callback_query.data == "steamtools_yes"
        else:
            return update.effective_message.text
