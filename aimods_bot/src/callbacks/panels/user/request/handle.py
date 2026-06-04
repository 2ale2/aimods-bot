import asyncio
from typing import get_args, Callable, Awaitable

from pydantic import ValidationError
from telegram import Update

from aimods_bot.src.callbacks.panels.user.request.render import render_global_request_wizard_panel, \
    render_request_wizard_confirmation_panel
from aimods_bot.src.core.config_accessor import get_section_config
from aimods_bot.src.core.customcontext import CustomContext, ChatData
from aimods_bot.src.helpers.constants.constants import RequestField
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction, UserRoute
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.requests import BaseRequest
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.bulk_sender import send_new_request_admin_notification, \
    send_section_closing_admin_notification
from aimods_bot.src.helpers.utils.file_utils import save_yaml_configuration
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, wrong_input_message

log = logger.getChild(__name__)


def _advance_or_finish_wizard(wizard) -> None:
    draft = wizard.draft

    # Se eravamo in modalità modifica, abbiamo finito la correzione. Torniamo al riepilogo.
    if wizard.editing:
        wizard.requesting = None
        wizard.editing = False
        return

    # Flusso normale: cerchiamo la prossima domanda vuota
    draft.requesting = None
    for field in draft.FLOW:
        if field.value not in draft.model_fields_set:
            draft.requesting = field
            break


async def handle_wizard_text_input(update: Update, context: CustomContext):
    if not update.message:
        raise ValueError("No message inside Update!")

    await safe_delete(update=update, context=context, message_id=update.message.message_id)

    wizard = context.pydc.persistent.active_request_wizard
    if not wizard:
        raise ValueError("No wizard to process!")

    if not wizard.requesting:
        log.warning("Requesting no field!")
        return PCS.USER_REQUEST_WIZARD_SESSION

    user_input = update.message.text

    if not user_input:
        await wrong_input_message(update=update, context=context, correct_message="Manda solo testo, senza allegati.")
        return PCS.USER_REQUEST_WIZARD_SESSION

    field_type = wizard.draft.model_fields[wizard.requesting.value].annotation
    is_boolean_expected = (field_type is bool) or (bool in get_args(field_type))

    if is_boolean_expected:
        await wrong_input_message(
            context=context,
            update=update,
            correct_message="Usa i bottoni della tastiera per rispondere Sì o No.",
            reply_to_message_id=wizard.request_msg_id
        )
        return PCS.USER_REQUEST_WIZARD_SESSION

    try:
        setattr(wizard.draft, wizard.requesting.value, user_input)
    except ValidationError as e:
        errors = e.errors()
        if any(err.get("type") == "url_parsing" for err in errors):
            await wrong_input_message(
                update=update,
                context=context,
                correct_message="Manda un link valido."
            )
        else:
            await wrong_input_message(
                update=update,
                context=context,
                correct_message="Input non valido, riprova o contatta un amministratore."
            )
        return PCS.USER_REQUEST_WIZARD_SESSION

    _advance_or_finish_wizard(wizard)

    if context.pydc.persistent.base_path:
        base_path = PathBuilder.from_string(context.pydc.persistent.base_path)
    else:
        base_path = PathBuilder(UserRoute.ROOT)

    await render_global_request_wizard_panel(
        update=update,
        context=context,
        base_path=base_path
    )
    return PCS.USER_REQUEST_WIZARD_SESSION


async def handle_wizard_callback_input(update: Update, context: CustomContext):
    query = update.callback_query
    if not query:
        raise ValueError("No query inside Update!")
    await query.answer()

    wizard = context.pydc.persistent.active_request_wizard
    if not wizard:
        raise ValueError("No wizard to process!")

    if query.data in (GlobalAction.YES, GlobalAction.NO):
        if not wizard.requesting:
            log.warning("Requesting no field!")
            return PCS.USER_REQUEST_WIZARD_SESSION

        bool_value = (query.data == GlobalAction.YES)
        setattr(wizard.draft, wizard.requesting.value, bool_value)

        _advance_or_finish_wizard(wizard)

    elif isinstance(query.data, RequestField):
        wizard.requesting = query.data
        wizard.editing = True

    if context.pydc.persistent.base_path:
        base_path = PathBuilder.from_string(context.pydc.persistent.base_path)
    else:
        base_path = PathBuilder(UserRoute.ROOT)

    await render_global_request_wizard_panel(
        update=update,
        context=context,
        base_path=base_path
    )
    return PCS.USER_REQUEST_WIZARD_SESSION


async def handle_wizard_back(update: Update, context: CustomContext):
    query = update.callback_query
    if not query:
        raise ValueError("No query inside Update!")
    await query.answer()

    wizard = context.pydc.persistent.active_request_wizard
    if not wizard:
        raise ValueError("No wizard to process!")

    draft = wizard.draft

    if wizard.editing:
        wizard.requesting = None
        wizard.editing = False
    else:
        flow_list = draft.FLOW

        if wizard.requesting is None:
            prev_field = flow_list[-1]
        else:
            current_index = flow_list.index(wizard.requesting)
            if current_index == 0:
                context.pydc.persistent.active_request_wizard = None
                # TODO: await user_main_route, funzione da modificare
                return PCS.USER_CONVERSATION

            prev_field = flow_list[current_index - 1]

        wizard.requesting = prev_field
        setattr(draft, prev_field.value, None)

    if context.pydc.persistent.base_path:
        base_path = PathBuilder.from_string(context.pydc.persistent.base_path)
    else:
        base_path = PathBuilder(UserRoute.ROOT)

    await render_global_request_wizard_panel(
        update=update,
        context=context,
        base_path=base_path
    )
    return PCS.USER_REQUEST_WIZARD_SESSION


async def handle_wizard_confirm(update: Update, context: CustomContext):
    query = update.callback_query
    if not query:
        raise ValueError("No query inside Update!")

    wizard = context.pydc.persistent.active_request_wizard
    if not wizard:
        raise ValueError("No wizard to process!")

    draft = wizard.draft

    request_for_db_str = draft.model_dump_json(
        exclude={"platform", "category", "status", "requesting", "editing", "id", "user_id", "issued_at"}
    )

    query_sql = """
                INSERT INTO requests_test (platform, category, user_id, content)
                VALUES ($1, $2, $3, $4)
                RETURNING id;
                """

    effective_user = update.effective_user

    if not effective_user:
        raise ValueError("Attribute Update.effective_user must not be None!")

    params = [
        draft.platform.value,
        draft.category.value,
        effective_user.id,
        request_for_db_str
    ]

    result = await fetch_query(query=query_sql, params=params)

    if not result:
        log.error(f"Error while submitting request from user {effective_user.id}. See previous logs.")
        await query.answer("❌ Errore nell'invio della richiesta. Riprova o contatta gli admin.")
        return PCS.USER_REQUEST_WIZARD_SESSION

    await query.answer()
    log.info(f"Request formulated by {effective_user.id} submitted")

    await _notify_new_request(update=update, context=context, request=wizard.draft)

    section = RequestSection(platform=wizard.draft.platform, category=wizard.draft.category)
    config = get_section_config(context=context, section=section)

    if config and config.limit:
        active_requests = context.get_active_category_requests(section=section)
        if len(active_requests) >= config.limit:
            config.toggle = False
            await save_yaml_configuration(context=context)
            await _notify_section_closing(update=update, context=context, section=section)

    if context.pydc.persistent.base_path:
        base_path = PathBuilder.from_string(context.pydc.persistent.base_path)
    else:
        base_path = PathBuilder(UserRoute.ROOT)

    await render_request_wizard_confirmation_panel(
        update=update,
        context=context,
        base_path=base_path,
        from_notification=wizard.from_notification
    )

    context.pydc.persistent.active_request_wizard = None

    return PCS.USER_CONVERSATION


async def _notify_admins_generic(
        context: CustomContext,
        filter_predicate: Callable[[ChatData], bool],
        send_coroutine: Callable[[int], Awaitable[None]]
):
    """
    Funzione generica per iterare sugli admin e inviare notifiche.
    """
    for admin_id in context.pydb.admins:
        admin_data = context.application.chat_data.get(admin_id)
        if not isinstance(admin_data, ChatData):
            continue

        if filter_predicate(admin_data):
            await send_coroutine(admin_id)
            await asyncio.sleep(0.2)


async def _notify_new_request(update: Update, context: CustomContext, request: BaseRequest):
    pl_val = str(request.platform.value)
    ca_val = str(request.category.value)

    def should_notify(data: ChatData) -> bool:
        return data.persistent.admin_notifications.new_requests_notifications.get(pl_val, {}).get(ca_val, False)

    async def sender(admin_id: int):
        await send_new_request_admin_notification(update=update, context=context, admin_id=admin_id, request=request)

    await _notify_admins_generic(context, should_notify, sender)


async def _notify_section_closing(update: Update, context: CustomContext, section: RequestSection):
    def should_notify(data: ChatData) -> bool:
        return data.persistent.admin_notifications.section_closing_notifications.get(
            section.platform, {}
        ).get(section.category, False)

    async def sender(admin_id: int):
        await send_section_closing_admin_notification(
            update=update,
            context=context,
            admin_id=admin_id,
            section=section
        )

    await _notify_admins_generic(context, should_notify, sender)
