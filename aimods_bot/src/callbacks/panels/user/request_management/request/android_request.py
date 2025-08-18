import copy
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ContextTypes, ConversationHandler

from aimods_bot.src.callbacks.panels.user.request_management.request.route import user_request_route
from aimods_bot.src.helpers.constants.conversation_states import AndroidRequestConversationState as ARCS
from aimods_bot.src.helpers.constants.models import RequestStatuses as RS
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("android_request")


class RequestDataManager:
    """Gestisce i dati della richiesta in modo centralizzato"""

    @staticmethod
    def initialize_request(context: CallbackContext) -> None:
        """Inizializza una nuova richiesta nel context"""
        context.chat_data["new_request"] = {
            "editing": None,
            "name": None,
            "link": None,
            "version": None,
            "functionalities": None
        }

    @staticmethod
    def get_request_data(context: CallbackContext) -> Dict[str, Any]:
        """Ottiene i dati della richiesta corrente"""
        # Se non è presente, deve essere scatenata un'eccezione.
        return context.chat_data["new_request"]

    @staticmethod
    def update_field(context: CallbackContext, field: str, value: Any) -> None:
        """Aggiorna un campo specifico della richiesta"""
        # Anche qua, "new_request" DEVE essere presente quando viene chiamata questa funzione
        if "new_request" not in context.chat_data:
            RequestDataManager.initialize_request(context)
        context.chat_data["new_request"][field] = value

    @staticmethod
    def cleanup_request(context: CallbackContext) -> None:
        """Pulisce i dati della richiesta dal context"""
        context.chat_data.pop("new_request", None)
        context.chat_data.pop("bot_message_id", None)


class MessageBuilder:
    """Costruisce messaggi per le diverse fasi della conversazione"""

    @staticmethod
    def build_request_summary(request_data: Dict[str, Any], editing_field: Optional[str] = None) -> str:
        """Costruisce il riepilogo della richiesta con evidenziazione del campo in editing"""
        name = request_data.get("name", "")
        link = request_data.get("link", "")
        version = request_data.get("version", "")
        functionalities = request_data.get("functionalities", "")

        # Formatta i campi con evidenziazione se in editing
        name_display = f"<i><b>Editing...</b></i>" if editing_field == "name" else f"<i>{name}</i>"
        link_display = f"<i><b>Editing...</b></i>" if editing_field == "link" else f"🔗 <i><a href='{link}'>Link</a></i>"
        version_display = f"<i><b>Editing...</b></i>" if editing_field == "version" else f"<code>{version}</code>"
        functionalities_display = f"<i><b>Editing...</b></i>" if editing_field == "functionalities" else f"<i>{functionalities}</i>"

        summary = "🤖 <b>Nuova Richiesta – Android</b>\n\n"

        if name:
            summary += f"      🔸 <u>Nome</u> – {name_display}\n"
        if link:
            summary += f"      🔸 <u>Link</u> – {link_display}\n"
        if version:
            summary += f"      🔸 <u>Versione</u> – {version_display}\n"
        if functionalities:
            summary += f"      🔸 <u>Funzionalità</u> – {functionalities_display}\n"

        return summary


class KeyboardBuilder:
    """Costruisce keyboard per le diverse fasi"""

    @staticmethod
    def get_back_keyboard(callback_data: str) -> InlineKeyboardMarkup:
        """Keyboard semplice con solo tasto indietro"""
        return InlineKeyboardMarkup([[
            InlineKeyboardButton(text="🔙 Indietro", callback_data=callback_data)
        ]])

    @staticmethod
    def get_review_keyboard() -> InlineKeyboardMarkup:
        """Keyboard per la review finale della richiesta"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(text="1️⃣ Nome", callback_data="edit_name"),
                InlineKeyboardButton(text="2️⃣ Link", callback_data="edit_link"),
            ],
            [
                InlineKeyboardButton(text="3️⃣ Versione", callback_data="edit_version"),
                InlineKeyboardButton(text="4️⃣ Funzionalità", callback_data="edit_functionalities")
            ],
            [
                InlineKeyboardButton(text="✅ Conferma", callback_data="confirm_request"),
                InlineKeyboardButton(text="❌ Annulla", callback_data="back_main")
            ]
        ])

    @staticmethod
    def get_confirmation_keyboard() -> InlineKeyboardMarkup:
        """Keyboard per la conferma finale"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(text="♟ Gestisci Richieste", callback_data="users/manage_requests"),
                InlineKeyboardButton(text="🔙 Indietro", callback_data="users")
            ]
        ])


async def edit_message_safely(context: CallbackContext, chat_id: int, text: str,
                            keyboard: InlineKeyboardMarkup) -> None:
    """Wrapper per edit_message_text con gestione errori"""
    try:
        await context.bot.edit_message_text(
            message_id=context.chat_data["bot_message_id"],
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except Exception as e:
        # Log dell'errore se necessario
        print(f"Errore nell'aggiornamento del messaggio: {e}")


async def request_app_name(update: Update, context: CallbackContext):
    """Inizia il flusso di richiesta chiedendo il nome dell'app"""
    await update.callback_query.answer()

    text = ("🤖 <b>Nuova Richiesta – Android</b>\n\n"
            "🔹 Indica il <b>nome dell'app</b> che vorresti richiedere.")

    RequestDataManager.initialize_request(context)
    context.chat_data["bot_message_id"] = update.effective_message.id

    keyboard = KeyboardBuilder.get_back_keyboard("back_main")

    await update.effective_message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

    return ARCS.APP_NAME


async def request_app_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Raccoglie il link dell'app"""
    if not update.callback_query:
        await safe_delete(update, context)
        RequestDataManager.update_field(context, "name", update.effective_message.text)

    request_data = RequestDataManager.get_request_data(context)
    text = MessageBuilder.build_request_summary(request_data)
    text += "\n🔹 Indica il <b>link dell'app</b> che vorresti richiedere."

    keyboard = KeyboardBuilder.get_back_keyboard("back_name")

    await edit_message_safely(context, update.effective_chat.id, text, keyboard)

    return ARCS.APP_LINK


async def request_app_version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Raccoglie la versione dell'app"""
    if not update.callback_query:
        await safe_delete(update, context)

        entity = update.effective_message.entities[0] or []
        link = update.effective_message.text[entity.offset:entity.offset + entity.length]

        RequestDataManager.update_field(context, "link", link)

    request_data = RequestDataManager.get_request_data(context)
    text = MessageBuilder.build_request_summary(request_data)
    text += "\n🔹 Indica la <b>versione dell'app</b> che vorresti richiedere."

    keyboard = KeyboardBuilder.get_back_keyboard("back_link")

    await edit_message_safely(context, update.effective_chat.id, text, keyboard)

    return ARCS.APP_VERSION


async def request_app_functionalities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Raccoglie le funzionalità dell'app"""
    if not update.callback_query:
        await safe_delete(update, context)
        RequestDataManager.update_field(context, "version", update.effective_message.text)

    request_data = RequestDataManager.get_request_data(context)
    text = MessageBuilder.build_request_summary(request_data)
    text += "\n🔹 Indica le <b>funzionalità dell'app</b> che vorresti sbloccare."

    keyboard = KeyboardBuilder.get_back_keyboard("back_version")

    await edit_message_safely(context, update.effective_chat.id, text, keyboard)

    return ARCS.APP_FUNCTIONALITIES


async def recheck_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra il riepilogo finale per la conferma"""
    request_data = RequestDataManager.get_request_data(context)

    if not request_data.get("editing"):
        if update.effective_message and update.effective_message.text:
            await safe_delete(update, context)
            RequestDataManager.update_field(context, "functionalities", update.effective_message.text)
            request_data = RequestDataManager.get_request_data(context)

    text = MessageBuilder.build_request_summary(request_data)
    text += ("\n🔹 Verifica i dettagli della tua richiesta. "
             "<b>Premi uno dei tasti per modificare un elemento</b>, oppure <b>conferma per inviarla</b>.\n\n"
             "<blockquote>⚠️ Assicurati che i dettagli siano <b>chiari</b>, "
             "altrimenti <b>la tua richiesta sarà bocciata</b>.</blockquote>")

    keyboard = KeyboardBuilder.get_review_keyboard()

    await edit_message_safely(context, update.effective_chat.id, text, keyboard)

    return ARCS.CHECK_REQUEST


async def edit_request_detail(update: Update, context: CallbackContext):
    """Gestisce l'editing di un campo specifico della richiesta"""
    await update.callback_query.answer()
    detail = update.callback_query.data.split("_")[1]
    request_data = RequestDataManager.get_request_data(context)

    RequestDataManager.update_field(context, "editing", detail)

    field_messages = {
        "name": "🔹 Indica il <b>nome dell'app</b> che vorresti richiedere.",
        "link": "🔹 Indica il <b>link dell'app</b> che vorresti richiedere.",
        "version": "🔹 Indica la <b>versione dell'app</b> che vorresti richiedere.",
        "functionalities": "🔹 Indica le <b>funzionalità dell'app</b> che vorresti sbloccare."
    }

    return_states = {
        "name": ARCS.EDIT_NAME,
        "link": ARCS.EDIT_LINK,
        "version": ARCS.EDIT_VERSION,
        "functionalities": ARCS.EDIT_FUNCTIONALITIES
    }

    text = MessageBuilder.build_request_summary(request_data, editing_field=detail)
    text += f"\n{field_messages.get(detail, '')}"

    keyboard = KeyboardBuilder.get_back_keyboard("no_edit")

    await edit_message_safely(context, update.effective_chat.id, text, keyboard)

    return return_states.get(detail, ARCS.EDIT_NAME)


async def edited_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce l'aggiornamento di un campo editato"""
    await safe_delete(update, context)
    request_data = RequestDataManager.get_request_data(context)
    editing_field = request_data.get("editing")

    if editing_field == "link":
        entity = update.effective_message.entities[0]
        data = update.effective_message.text[entity.offset:entity.offset + entity.length]
    else:
        data = update.effective_message.text

    RequestDataManager.update_field(context, editing_field, data)

    try:
        return await recheck_request(update=update, context=context)
    finally:
        RequestDataManager.update_field(context, "editing", None)


async def backer(update: Update, context: CallbackContext):
    """Gestisce la navigazione all'indietro in modo centralizzato"""
    data = update.callback_query.data
    detail = data.split("_")[1]

    back_actions = {
        "no_edit": lambda: recheck_request(update=update, context=context),
        "back_main": lambda: _handle_back_to_main(update, context),
        "back_name": lambda: request_app_name(update=update, context=context),
        "back_link": lambda: request_app_link(update=update, context=context),
        "back_version": lambda: request_app_version(update=update, context=context)
    }

    action = back_actions.get(data)
    try:
        if action:
            if detail in ("name", "link", "version"):
                context.chat_data["new_request"][detail] = None
            return await action()

        if data.endswith("main"):
            context.chat_data.pop("new_request", None)
            return await _handle_back_to_main(update, context)

        return ARCS.CHECK_REQUEST
    finally:
        await update.callback_query.answer()


async def _handle_back_to_main(update: Update, context: CallbackContext):
    """Gestisce il ritorno al menu principale"""
    await user_request_route(update=update, context=context, path=[])
    return ARCS.MAIN_BACKER


async def confirm_request(update: Update, context: CallbackContext):
    """Conferma e salva la richiesta nel database"""
    uid = update.effective_user.id
    request_data = RequestDataManager.get_request_data(context)

    request_for_db = copy.deepcopy(request_data)
    request_for_db.pop("editing", None)

    try:
        query = """
                INSERT INTO requests (id, platform, content, user_id, status, issued_at)
                VALUES (DEFAULT, 'android', $1, $2, DEFAULT, DEFAULT)
                RETURNING id \
                """

        result = await fetch_query(
            query=query,
            params=[str(request_for_db).replace("'", "\""), uid]
        )

        if not result:
            raise Exception("Errore durante l'inserimento della richiesta")

        inserted_id = dict(result[0])["id"]

        request_for_db.update({
            "status": RS.PENDING,
            "id": inserted_id
        })

        context.user_data["requests"]["android"].append(request_for_db)

        text = ("✅ <b>Richiesta Inviata</b>\n\n"
                "▫️ Puoi visionare lo stato delle tue richieste dal pannello di controllo.")

        keyboard = KeyboardBuilder.get_confirmation_keyboard()

        await edit_message_safely(context, update.effective_chat.id, text, keyboard)

    except Exception as e:
        error_text = ("❌ <b>Errore</b>\n\n"
                      "Si è verificato un errore durante l'invio della richiesta. "
                      "Riprova più tardi.")

        keyboard = KeyboardBuilder.get_back_keyboard("back_main")

        await edit_message_safely(context, update.effective_chat.id, error_text, keyboard)

        log.error(f"Errore durante conferma richiesta: {e}")

    finally:
        RequestDataManager.cleanup_request(context)

    return ConversationHandler.END
