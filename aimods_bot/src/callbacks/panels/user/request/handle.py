from typing import get_args

from pydantic import ValidationError
from telegram import Update

from aimods_bot.src.callbacks.panels.user.request.render import render_global_request_wizard_panel, \
    render_request_wizard_confirmation_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import RequestField
from aimods_bot.src.helpers.constants.conversation_paths.navigation import GlobalAction
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.loggers import logger
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

    await render_global_request_wizard_panel(
        update=update,
        context=context,
        base_path=context.pydc.persistent.base_path
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

    await render_global_request_wizard_panel(
        update=update,
        context=context,
        base_path=context.pydc.persistent.base_path
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

    await render_global_request_wizard_panel(
        update=update,
        context=context,
        base_path=context.pydc.persistent.base_path
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

    params = [
        draft.platform.value,
        draft.category.value,
        update.effective_user.id,
        request_for_db_str
    ]

    result = await fetch_query(query=query_sql, params=params)

    if not result:
        log.error(f"Error while submitting request from user {update.effective_user.id}. See previous logs.")
        await query.answer("❌ Errore nell'invio della richiesta. Riprova o contatta gli admin.")
        return PCS.USER_REQUEST_WIZARD_SESSION

    await query.answer()
    log.info(f"Request formulated by {update.effective_user.id} submitted")

    await render_request_wizard_confirmation_panel(
        update=update,
        context=context,
        base_path=context.pydc.persistent.base_path,
        from_notification=wizard.from_notification
    )

    context.pydc.persistent.active_request_wizard = None

    return PCS.USER_CONVERSATION
