import asyncio
from typing import Callable, Awaitable

from telegram import Update

from aimods_bot.src.callbacks.panels.user.request.handle import RequestDataManager, InputHandler
from aimods_bot.src.callbacks.panels.user.request.render import render_user_request_panel
from aimods_bot.src.core.customcontext import CustomContext, ChatData
from aimods_bot.src.core.exceptions import WrongFlowException
from aimods_bot.src.core.pydantic import Request
from aimods_bot.src.helpers.constants.constants import RequestField, Platform, Category
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.scheduler import schedule_request_cooldown_removal
from aimods_bot.src.helpers.utils.bulk_sender import send_new_request_admin_notification, \
    send_section_closing_admin_notification
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json, save_yaml_configuration
from aimods_bot.src.helpers.utils.telegram_utils import get_config

log = logger.getChild("request")

RETURN_CONVERSATION_STATES = {
    "name": RCS.REQUEST_NAME,
    "link": RCS.REQUEST_LINK,
    "version": RCS.REQUEST_VERSION,
    "functionalities": RCS.REQUEST_FUNCTIONALITIES,
    "steamtools": RCS.REQUEST_STEAMTOOLS,
    "arch": RCS.REQUEST_ARCH
}

_REQUEST_FLOWS_CACHE = None


async def get_request_flows():
    global _REQUEST_FLOWS_CACHE
    if _REQUEST_FLOWS_CACHE is None:
        _REQUEST_FLOWS_CACHE = await get_data_from_json('request_conversation_flows')
    return _REQUEST_FLOWS_CACHE


# --- HELPERS ---

async def _notify_admins_generic(
        context: CustomContext,
        filter_predicate: Callable[[ChatData], bool],
        send_coroutine: Callable[[int], Awaitable[None]]
):
    """
    Funzione generica per iterare sugli admin e inviare notifiche.
    Riduce la duplicazione del codice di loop e sleep.
    """
    for admin_id in context.pydb.admins:
        admin_data = context.application.chat_data.get(admin_id)
        # Type narrowing sicuro
        if not isinstance(admin_data, ChatData):
            continue

        if filter_predicate(admin_data):
            await send_coroutine(admin_id)
            # Sleep per evitare flood limits se ci sono molti admin
            await asyncio.sleep(0.2)


async def _notify_new_request(update: Update, context: CustomContext, request: Request):
    pl_val = str(request.platform.value)
    ca_val = str(request.category.value)

    def should_notify(data: ChatData) -> bool:
        return data.persistent.admin_notifications.new_requests_notifications.get(pl_val, {}).get(ca_val, False)

    async def sender(admin_id: int):
        await send_new_request_admin_notification(update, context, admin_id, request)

    await _notify_admins_generic(context, should_notify, sender)


async def _notify_section_closing(update: Update, context: CustomContext, platform: Platform, category: Category):
    pl_val = platform.value
    ca_val = str(category.value)
    section_str = f"{pl_val}:{category.value}"

    def should_notify(data: ChatData) -> bool:
        return data.persistent.admin_notifications.section_closing_notifications.get(pl_val, {}).get(ca_val, False)

    async def sender(admin_id: int):
        await send_section_closing_admin_notification(update, context, admin_id, section_str)

    await _notify_admins_generic(context, should_notify, sender)


# --- CORE HANDLERS ---

async def _get_next_step_in_flow(platform: Platform, category: Category, current_step: str) -> RequestField:
    """Helper isolato per calcolare il prossimo step."""
    flows = await get_request_flows()
    try:
        # Accesso sicuro al dizionario
        flow_list: list[str] = flows[platform.value][category.value]["flow"]
        current_index = flow_list.index(current_step)

        if current_index + 1 < len(flow_list):
            return RequestField(flow_list[current_index + 1])

    except (KeyError, ValueError, IndexError):

        raise WrongFlowException(f"Errore nel calcolo del prossimo step per {current_step}")

    raise WrongFlowException("L'ultimo elemento richiesto dovrebbe essere gestito dal metodo 'recheck_request'.")


async def request_detail(update: Update, context: CustomContext) -> int:
    """Gestisce l'input utente se necessario e richiede il dettaglio successivo."""
    if not context.pydc.persistent.bot_message_id:
        context.pydc.persistent.bot_message_id = update.effective_message.id

    request_data = RequestDataManager.get_request_data(context)

    next_detail = RequestField.NAME

    if request_data.requesting:
        await InputHandler.handle_input(update=update, context=context)
        next_detail = await _get_next_step_in_flow(
            request_data.platform,
            request_data.category,
            request_data.requesting.value
        )

    RequestDataManager.update_field(context=context, field="requesting", value=next_detail)
    await RequestDataManager.request_detail(update=update, context=context, detail=next_detail)

    return RETURN_CONVERSATION_STATES[str(next_detail.value)]


async def recheck_request(update: Update, context: CustomContext):
    """Chiede all'utente di ricontrollare e confermare la richiesta."""
    await InputHandler.handle_input(update=update, context=context)

    try:
        return await RequestDataManager.recheck_request(update=update, context=context)
    finally:
        RequestDataManager.update_field(context=context, field="requesting", value=None)


async def edit_request_detail(update: Update, context: CustomContext):
    """L'utente ha chiesto di modificare un dettaglio."""
    query = update.callback_query
    if query and query.data:
        await query.answer()
        data = query.data

        if data.endswith(("steamtools", "arch")):
            _, value_str = data.split(":", 1)
            try:
                field_enum = RequestField(value_str)
                RequestDataManager.update_field(context=context, field="editing", value=field_enum)
                return await RequestDataManager.recheck_request(update=update, context=context)
            except ValueError:
                pass

        return await RequestDataManager.request_detail_to_edit(update=update, context=context)


async def edited_detail(update: Update, context: CustomContext):
    """Gestisce l'input dopo una modifica e torna al recheck."""
    await InputHandler.handle_input(update=update, context=context)

    try:
        return await recheck_request(update=update, context=context)
    finally:
        RequestDataManager.update_field(context=context, field="editing", value=None)


async def confirm_request(update: Update, context: CustomContext):
    """Elabora la richiesta, cooldown, notifiche e controllo limiti."""
    ix = await RequestDataManager.confirm_request(update=update, context=context)
    request = context.get_active_request_by_id(ix=ix)

    rc = context.set_user_request_cooldown(user_id=update.effective_user.id)
    await schedule_request_cooldown_removal(context=context, user_id=rc.user_id, until=rc.until)

    await _notify_new_request(update, context, request)

    platform = request.platform
    category = request.category
    config = get_config(context, platform, category)

    if config and config.limit:
        active_requests = context.get_active_category_requests(platform=platform, category=category)

        if len(active_requests) >= config.limit:
            log.info(f"Section {platform.value}:{category.value} reached limit ({config.limit}). Closing.")

            config.toggle = False
            await save_yaml_configuration(context=context)
            await _notify_section_closing(update, context, platform, category)

    return RCS.REQUEST_SUBMITTED


async def backer(update: Update, context: CustomContext):
    """Gestisce la navigazione all'indietro."""
    query = update.callback_query
    await query.answer()

    data = query.data
    # data format atteso: "back_<field>" o "no_edit"

    match data:
        case "no_edit":
            RequestDataManager.update_field(context=context, field="editing", value=None)
            return await RequestDataManager.recheck_request(update=update, context=context)

        case _ if data.startswith("back_"):
            detail_str = data.split("_", 1)[1]

            if detail_str == "main":
                return await route_back_to_main(update=update, context=context)

            request_data = RequestDataManager.get_request_data(context=context)
            setattr(request_data, detail_str, None)

            detail_enum = RequestField(detail_str)
            await RequestDataManager.request_detail(update=update, context=context, detail=detail_enum)

            return RETURN_CONVERSATION_STATES.get(detail_str)

    # Fallback sicuro
    return await route_back_to_main(update=update, context=context)


async def route_back_to_main(update: Update, context: CustomContext):
    """Reset e ritorno alla home."""
    RequestDataManager.initialize_request(context=context)
    await render_user_request_panel(update=update, context=context)
    return RCS.MAIN_BACKER