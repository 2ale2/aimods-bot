from typing import Optional
from telegram import Update
from telegram.ext import CallbackContext, ContextTypes

from aimods_bot.src.callbacks.panels.user.request_management.handle import RequestDataManager, InputHandler, \
    RequestField, RequestData
from aimods_bot.src.callbacks.panels.user.request_management.utils import route_back_to_main
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.constants.constants import REQUEST_FLOWS
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("request")

RETURN_CONVERSATION_STATES = {
    "name": RCS.REQUEST_NAME,
    "link": RCS.REQUEST_LINK,
    "version": RCS.REQUEST_VERSION,
    "functionalities": RCS.REQUEST_FUNCTIONALITIES,
    "steamtools": RCS.REQUEST_STEAMTOOLS
}


async def request_detail(update: Update, context: CallbackContext) -> int:
    """Gestisce l'input utente se necessario e richiede il dettaglio successivo."""
    if "bot_message_id" not in context.chat_data:
        context.chat_data["bot_message_id"] = update.effective_message.id

    request_data = RequestDataManager.get_request_data(context)
    if request_data.requesting:
        await InputHandler.handle_input(update=update, context=context)
        detail = prepare_next_detail(request_data=request_data)
        RequestDataManager.update_field(context=context, field="requesting", value=detail)
    else:
        detail = RequestField.NAME
        RequestDataManager.update_field(context=context, field="requesting", value=detail)

    await RequestDataManager.request_detail(
        update=update,
        context=context,
        detail=detail
    )

    return RETURN_CONVERSATION_STATES[detail.value]


def prepare_next_detail(request_data: RequestData) -> Optional[RequestField]:
    """Deduce il prossimo dettaglio da chiedere all'utente in base allo step attuale.
    Lo step è valutato basandosi sul flow della conversazione, che è determinato dalla categoria
    dell'elemento richiesto."""
    platform = request_data.get_platform()
    category = request_data.get_category()
    requesting = request_data.requesting

    flow = REQUEST_FLOWS[platform.value][category.value]
    ix = flow.index(requesting.value)
    if len(flow) >= ix + 1:
        return RequestField(flow[ix + 1])
    return None


async def recheck_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chiede all'utente di ricontrollare e confermare la richiesta."""
    return await RequestDataManager.recheck_request(update=update, context=context)


async def edit_request_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """L'utente ha chiesto di modificare un dettaglio della propria richiesta."""
    return await RequestDataManager.request_detail_to_edit(update=update, context=context)


async def edited_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce l'input dell'utente succesivamente a una richiesta di modifica."""
    await InputHandler.handle_input(update=update, context=context)

    RequestDataManager.update_field(context=context, field="editing", value=None)

    return await recheck_request(update=update, context=context)


async def confirm_request(update: Update, context: CallbackContext):
    """Conferma la richiesta e la elabora."""
    request_data = RequestDataManager.get_request_data(context=context)
    platform = request_data.get_platform()

    return await RequestDataManager.confirm_request(update=update, context=context, platform=platform)


async def backer(update: Update, context: CallbackContext):
    """Gestisce la pressione del tasto indietro o annulla."""
    request_data = RequestDataManager.get_request_data(context=context)

    data = update.callback_query.data
    detail = data.split("_", maxsplit=1)[1]

    if detail == "main":
        return await route_back_to_main(update=update, context=context)
    if data == "no_edit":
        setattr(request_data, "editing", None)
        return await RequestDataManager.recheck_request(update=update, context=context)

    setattr(request_data, detail, None)

    return await RequestDataManager.request_detail(update=update, context=context, detail=detail)
