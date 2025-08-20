from telegram import Update
from telegram.ext import CallbackContext, ContextTypes, ConversationHandler

from aimods_bot.src.callbacks.panels.user.request_management.request.windows.handle import (
    InputHandler, MessageBuilder, KeyboardBuilder, RequestDataManager, handle_back_to_main)
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import edit_message_safely

log = logger.getChild("windows_adobe_request")
WRCS = RCS.WindowsRequest
ADRCS = WRCS.AdobeRequest


async def request_adobe_name(update: Update, context: CallbackContext) -> int:
    """Richiede il nome del software Adobe."""
    context.chat_data["bot_message_id"] = update.effective_message.id

    await RequestDataManager.request_detail(
        update=update,
        context=context,
        detail="name",
        back_data="back_category"
    )

    return ADRCS.ADOBE_NAME


async def request_adobe_version(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Richiede la versione del software Adobe."""
    if not update.callback_query:
        await InputHandler.handle_input(update=update, context=context, detail="name")

    await RequestDataManager.request_detail(
        update=update,
        context=context,
        detail="version",
        back_data="back_name"
    )

    return ADRCS.ADOBE_VERSION


async def request_adobe_functionalities(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Richiede le funzionalità del software Adobe"""
    if not update.callback_query:
        await InputHandler.handle_input(update=update, context=context, detail="version")

    await RequestDataManager.request_detail(
        update=update,
        context=context,
        detail="functionalities",
        back_data="back_version"
    )

    return ADRCS.ADOBE_FUNCTIONALITIES


async def recheck_adobe_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra il riepilogo finale per la conferma"""
    if not update.callback_query:
        await InputHandler.handle_input(update=update, context=context, detail="functionalities")

    request_data = RequestDataManager.get_request_data(context=context)
    text = MessageBuilder.build_request_summary(request_data)
    text += ("\n🔹 Verifica i dettagli della tua richiesta. "
             "<b>Premi uno dei tasti per modificare un elemento</b>, oppure <b>conferma per inviarla</b>.\n\n"
             "<blockquote>⚠️ Assicurati che i dettagli siano <b>chiari</b>, "
             "altrimenti <b>la tua richiesta sarà bocciata</b>.</blockquote>")

    keyboard = KeyboardBuilder.get_review_keyboard(context=context)

    await edit_message_safely(
        context=context,
        message_id=context.chat_data["bot_message_id"],
        chat_id=update.effective_chat.id,
        text=text,
        keyboard=keyboard)

    return RCS.CHECK_REQUEST


async def edit_game_request_detail(update: Update, context: CallbackContext) -> int:
    """Gestisce la pressione per modificare un dettaglio della richiesta"""
    data = update.callback_query.data

    return await RequestDataManager.request_detail_to_edit(update=update, context=context)


async def edited_game_detail(update: Update, context: CallbackContext) -> int:
    """Gestisce l'aggiornamento di un campo editato"""
    await InputHandler.handle_input(update=update, context=context, detail=context.chat_data["new_request"].editing)

    try:
        return await recheck_game_request(update=update, context=context)
    finally:
        RequestDataManager.update_field(context, "editing", None)


async def adobe_backer(update: Update, context: CallbackContext) -> int:
    data = update.callback_query.data
    detail = data.split("_")[1]

    back_actions = {
        "no_edit": lambda: recheck_game_request(update=update, context=context),
        "back_main": lambda: handle_back_to_main(update, context),
        "back_name": lambda: request_game_name(update=update, context=context),
        "back_version": lambda: request_game_version(update=update, context=context),
        "back_functionalities": lambda: request_game_functionalities(update=update, context=context)
    }

    action = back_actions.get(data)
    try:
        if action:
            if detail in ("name", "version", "functionalities"):
                request_data = context.chat_data["new_request"]
                setattr(request_data, detail, None)
            return await action()

        if data.endswith("main"):
            RequestDataManager.cleanup_request(context)
            return await handle_back_to_main(update, context)

        raise Exception(f"Ma che cazzo di callback query hai messo? ({data})")
    finally:
        await update.callback_query.answer()


async def confirm_adobe_request(update: Update, context: CallbackContext) -> int:
    """Conferma la richiesta salvandola nel db e avvisa l'utente."""
    try:
        await RequestDataManager.confirm_request(update=update, context=context, platform='windows')
        text = ("✅ <b>Richiesta Inviata</b>\n\n"
                "▫️ Puoi visionare lo stato delle tue richieste dal pannello di controllo.")

        keyboard = KeyboardBuilder.get_confirmation_keyboard()
    except Exception as e:
        text = ("❌ <b>Errore</b>\n\n"
                      "Si è verificato un errore durante l'invio della richiesta. "
                      "Riprova più tardi.")

        keyboard = KeyboardBuilder.get_back_keyboard("back_main")

        log.error(f"Errore durante conferma richiesta: {e}")
    finally:
        # noinspection PyUnboundLocalVariable
        await edit_message_safely(
            context=context,
			message_id=context.chat_data["bot_message_id"],
            chat_id=update.effective_chat.id,
            text=text,
            keyboard=keyboard)
        RequestDataManager.cleanup_request(context)

    return ConversationHandler.END