from typing import Optional
from telegram import Update
from telegram.ext import CallbackContext, ContextTypes

from aimods_bot.src.callbacks.panels.user.request.handle import RequestDataManager, InputHandler, \
    RequestField, can_user_request
from aimods_bot.src.helpers.constants.models import RequestData
from aimods_bot.src.callbacks.panels.user.request.render import render_user_request_panel, \
    render_user_cant_request_panel
from aimods_bot.src.core.exceptions import WrongFlowException
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS, \
    PrivateConversationState as PCS
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json

log = logger.getChild("request")

RETURN_CONVERSATION_STATES = {
    "name": RCS.REQUEST_NAME,
    "link": RCS.REQUEST_LINK,
    "version": RCS.REQUEST_VERSION,
    "functionalities": RCS.REQUEST_FUNCTIONALITIES,
    "steamtools": RCS.REQUEST_STEAMTOOLS
}

REQUEST_FLOWS = get_data_from_json('request_conversation_flows')


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

    flow = REQUEST_FLOWS[platform.value][category.value]["flow"]
    ix = flow.index(requesting.value)
    if len(flow) >= ix + 1:
        return RequestField(flow[ix + 1])

    raise WrongFlowException("L'ultimo elemento richiesto dovrebbe essere gestito dal metodo 'recheck_request'.")


async def recheck_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chiede all'utente di ricontrollare e confermare la richiesta."""
    await InputHandler.handle_input(update=update, context=context)

    try:
        return await RequestDataManager.recheck_request(update=update, context=context)
    finally:
        RequestDataManager.update_field(context=context, field="requesting", value=None)


async def edit_request_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """L'utente ha chiesto di modificare un dettaglio della propria richiesta."""
    if update.callback_query:
        data = update.callback_query.data
        if data in ("steamtools_yes", "steamtools_no"):
            RequestDataManager.update_field(context=context, field="editing", value=RequestField.STEAMTOOLS)
            return await RequestDataManager.recheck_request(update=update, context=context)

    return await RequestDataManager.request_detail_to_edit(update=update, context=context)


async def edited_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce l'input dell'utente succesivamente a una richiesta di modifica."""
    await InputHandler.handle_input(update=update, context=context)

    try:
        return await recheck_request(update=update, context=context)
    finally:
        RequestDataManager.update_field(context=context, field="editing", value=None)


async def confirm_request(update: Update, context: CallbackContext):
    """Conferma la richiesta e la elabora."""
    return await RequestDataManager.confirm_request(update=update, context=context)


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


async def route_back_to_main(update: Update, context: CallbackContext):
    """Gestisce il ritorno al menu principale"""
    RequestDataManager.cleanup_request(context=context)
    await user_request_check(update=update, context=context, path=[])
    return RCS.MAIN_BACKER


async def user_request_check(update: Update, context: CallbackContext, path=Optional[list[str]]):
    if path is not None and len(path) == 0:
        answer = await can_user_request(update=update, context=context)
        if answer.yn:
            await render_user_request_panel(update=update, context=context)
            return PCS.NEW_REQUEST
        else:
            await render_user_cant_request_panel(update=update, context=context, reason=answer.reason)
            return PCS.USER_CONVERSATION
