import asyncio

from telegram import Update
from telegram.ext import ConversationHandler

from aimods_bot.src.callbacks.panels.user.request.handle import RequestDataManager, InputHandler
from aimods_bot.src.callbacks.panels.user.request.render import render_user_request_panel
from aimods_bot.src.helpers.utils.bulk_sender import send_new_request_admin_notification, \
    send_section_closing_admin_notification
from aimods_bot.src.core.customcontext import CustomContext, ChatData
from aimods_bot.src.core.exceptions import WrongFlowException
from aimods_bot.src.core.pydantic import Request, CategorySetting
from aimods_bot.src.helpers.constants.constants import RequestField
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.scheduler import schedule_request_cooldown_removal
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json, save_yaml_configuration

log = logger.getChild("request")

RETURN_CONVERSATION_STATES = {
    "name": RCS.REQUEST_NAME,
    "link": RCS.REQUEST_LINK,
    "version": RCS.REQUEST_VERSION,
    "functionalities": RCS.REQUEST_FUNCTIONALITIES,
    "steamtools": RCS.REQUEST_STEAMTOOLS,
    "arch": RCS.REQUEST_ARCH
}

REQUEST_FLOWS = get_data_from_json('request_conversation_flows')


async def request_detail(update: Update, context: CustomContext) -> int:
    """Gestisce l'input utente se necessario e richiede il dettaglio successivo."""
    if not context.pydc.persistent.bot_message_id:
        context.pydc.persistent.bot_message_id = update.effective_message.id

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

    return RETURN_CONVERSATION_STATES[str(detail.value)]


def prepare_next_detail(request_data: Request) -> RequestField:
    """Deduce il prossimo dettaglio da chiedere all'utente in base allo step attuale.
    Lo step è valutato basandosi sul flow della conversazione, che è determinato dalla categoria
    dell'elemento richiesto."""
    platform = request_data.platform
    category = request_data.category
    requesting = request_data.requesting

    flow = REQUEST_FLOWS[platform.value][category.value]["flow"]
    ix = flow.index(requesting.value)
    """
    name (0) -> link (1)
    link (1) -> version (2)
    version (2) -> functionalities (3)
    """
    if len(flow) >= ix + 1:
        return RequestField(flow[ix + 1])

    raise WrongFlowException("L'ultimo elemento richiesto dovrebbe essere gestito dal metodo 'recheck_request'.")


async def recheck_request(update: Update, context: CustomContext):
    """Chiede all'utente di ricontrollare e confermare la richiesta."""
    await InputHandler.handle_input(update=update, context=context)

    try:
        return await RequestDataManager.recheck_request(update=update, context=context)
    finally:
        RequestDataManager.update_field(context=context, field="requesting", value=None)


async def edit_request_detail(update: Update, context: CustomContext):
    """L'utente ha chiesto di modificare un dettaglio della propria richiesta."""
    if update.callback_query:
        await update.callback_query.answer()
        data = update.callback_query.data
        if data.endswith(("steamtools", "arch")):
            value = data.split(":", 1)[1]
            RequestDataManager.update_field(context=context, field="editing", value=RequestField(value))
            return await RequestDataManager.recheck_request(update=update, context=context)

    return await RequestDataManager.request_detail_to_edit(update=update, context=context)


async def edited_detail(update: Update, context: CustomContext):
    """Gestisce l'input dell'utente successivamente a una richiesta di modifica."""
    await InputHandler.handle_input(update=update, context=context)

    try:
        return await recheck_request(update=update, context=context)
    finally:
        RequestDataManager.update_field(context=context, field="editing", value=None)


async def confirm_request(update: Update, context: CustomContext):
    """Elabora la richiesta, setta e programma il cooldown."""
    ix = await RequestDataManager.confirm_request(update=update, context=context)
    request = context.get_active_request_by_id(ix=ix)

    platform = request.platform
    category = request.category

    # Setta il cooldown richieste
    rc = context.set_user_request_cooldown(user_id=update.effective_user.id)
    # Programma la rimozione del cooldown
    await schedule_request_cooldown_removal(context=context, user_id=rc.user_id, until=rc.until)

    # Invia le notifiche
    for admin_id in context.pydb.admins:
        admin_data = context.application.chat_data.get(admin_id, None)
        if admin_data:
            assert isinstance(admin_data, ChatData)
            admin_settings = admin_data.persistent.admin_notifications.new_requests_notifications
            if admin_settings[platform.value][category.value]:
                await send_new_request_admin_notification(
                    update=update,
                    context=context,
                    admin_id=admin_id,
                    request=request
                )
                await asyncio.sleep(0.5)

    config = getattr(getattr(context.pydb.configuration.settings.request, platform.value), category.value)
    assert isinstance(config, CategorySetting)

    if config is not None:
        n_active_requests = len(context.get_active_category_requests(platform=platform, category=category))
        if config.limit and n_active_requests >= config.limit:
            log.info(f"Section {platform.value} - {category.value} reached requests limit ({config.limit}): "
                     f"closing it...")
            config.toggle = False
            await save_yaml_configuration(context=context)

            # Invio notifiche
            for admin_id in context.pydb.admins:
                admin_data = context.application.chat_data.get(admin_id, None)
                if admin_data:
                    assert isinstance(admin_data, ChatData)
                    admin_settings = admin_data.persistent.admin_notifications.section_closing_notifications
                    if admin_settings[platform.value][category.value]:
                        await send_section_closing_admin_notification(
                            update=update,
                            context=context,
                            section=f"{platform.value}:{category.value}",
                            admin_id=admin_id
                        )
                        await asyncio.sleep(0.5)


    return RCS.REQUEST_SUBMITTED


async def backer(update: Update, context: CustomContext):
    """Gestisce la pressione del tasto indietro o annulla."""
    await update.callback_query.answer()
    request_data = RequestDataManager.get_request_data(context=context)

    data = update.callback_query.data
    detail = data.split("_", maxsplit=1)[1]

    if detail == "main":
        return await route_back_to_main(update=update, context=context)
    if data == "no_edit":
        setattr(request_data, "editing", None)
        return await RequestDataManager.recheck_request(update=update, context=context)

    setattr(request_data, detail, None)
    await RequestDataManager.request_detail(update=update, context=context, detail=RequestField(detail))

    return RETURN_CONVERSATION_STATES[detail]


async def route_back_to_main(update: Update, context: CustomContext):
    """Gestisce il ritorno al menu principale"""
    RequestDataManager.initialize_request(context=context)
    await render_user_request_panel(update=update, context=context)
    return RCS.MAIN_BACKER
