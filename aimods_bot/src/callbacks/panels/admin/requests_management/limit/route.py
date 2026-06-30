import os
from typing import Union

from pyrogram.types import User as PyroUser
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, User as PTBUser
from telegram.constants import ParseMode

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.handle import (
    handle_request_limitation_topic,
    handle_limitation_confirmation,
    handle_remove_user_request_limitation
)
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.render import (
    render_admin_add_user_request_limitation_panel, render_admin_limit_user_request_duration_panel,
    render_admin_limit_user_request_sections_panel,
    render_admin_user_limitation_reason_panel, render_admin_manage_limitations_panel,
    render_admin_manage_user_limitations_panel,
    render_admin_remove_user_limitation_confirmation_panel,
    render_admin_user_limitation_removed_panel, render_admin_remove_user_limitation_panel,
    render_admin_user_limitation_confirmed_panel, render_admin_view_user_request_limitations_panel)
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import LimitationsOp, LimitationsFlow, GlobalAction
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import wrong_input_message, is_user_id, safe_delete
from aimods_bot.src.helpers.utils.time_utils import parse_duration, timedelta_to_seconds
from aimods_bot.src.helpers.utils.user_utils import is_admin, resolve_user_from_identifier

log = logger.getChild(__name__)


async def route_admin_manage_limitations(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            context.pydc.persistent.bot_message_id = update.effective_message.id
            context.pydc.persistent.root_path = root.build()
            await render_admin_manage_limitations_panel(update=update, context=context, base_path=root)
            return PCS.SET_REQUEST_LIMITATION_USER

        case [identifier, *rest]:
            pre_resolved_user = None

            if is_user_id(identifier):
                pre_resolved_user = int(identifier)

            match PathBuilder(*rest).segments:
                case []:
                    resolved_user = await resolve_user_from_identifier(identifier=identifier)

                    if resolved_user is None:
                        # utente non trovato
                        await wrong_input_message(
                            update=update,
                            context=context,
                            correct_message="Manda un <b>identificatore esistente</b> (Username o ID numerico)."
                        )

                        return PCS.SET_REQUEST_LIMITATION_USER

                    limiting_user = context.get_or_create_limitation_wizard()

                    if isinstance(resolved_user, str) and is_user_id(resolved_user):
                        resolved_user = int(resolved_user)

                    user_id = resolved_user if isinstance(resolved_user, int) else resolved_user.id

                    if await is_admin(context=context, user_id=user_id):
                        await wrong_input_message(
                            update=update,
                            context=context,
                            correct_message="Manda uno <b>username</b> o un <b>ID numerico</b> che "
                                            "<b>non appartengano</b> agli admin."
                        )
                        return PCS.SET_REQUEST_LIMITATION_USER

                    limiting_user.user_id = user_id

                    if not isinstance(resolved_user, int):
                        limiting_user.username = resolved_user.username
                        context.pydc.ephemeral.resolved_users[resolved_user.id] = resolved_user

                    root = root + relative_path.change(str(identifier), str(user_id))

                    await render_admin_manage_user_limitations_panel(
                        update=update,
                        context=context,
                        base_path=root,
                        pre_resolved_user=resolved_user
                    )

                    return PCS.ADMIN_CONVERSATION

                case [LimitationsOp.VIEW]:
                    await render_admin_view_user_request_limitations_panel(
                        update=update,
                        context=context,
                        base_path=root + relative_path,
                        pre_resolved_user=pre_resolved_user
                    )
                    return PCS.ADMIN_CONVERSATION

                case [LimitationsOp.ADD, *rest]:
                    return await route_admin_add_request_limitation(
                        update=update,
                        context=context,
                        root=root.add(identifier, LimitationsOp.ADD),
                        relative_path=PathBuilder(*rest),
                        pre_resolved_user=pre_resolved_user
                    )

                case [LimitationsOp.REMOVE, *rest]:
                    return await route_admin_remove_request_limitation_route(
                        update=update,
                        context=context,
                        root=root.add(identifier, LimitationsOp.REMOVE),
                        relative_path=PathBuilder(*rest),
                        pre_resolved_user=pre_resolved_user
                    )


async def handle_limitation_user_input(update: Update, context: CustomContext):
    await safe_delete(update=update, context=context, message_id=update.message.message_id)

    identifier = update.message.text
    base = PathBuilder.from_string(context.pydc.persistent.root_path)
    context.clear_saved_path(clear_relative=False)

    return await route_admin_manage_limitations(
        update=update,
        context=context,
        root=base,
        relative_path=PathBuilder(identifier)
    )


async def route_admin_add_request_limitation(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder,
        pre_resolved_user: int | PTBUser | PyroUser
):
    limitation_wizard = context.get_or_create_limitation_wizard()
    match relative_path.segments:
        case []:
            await render_admin_add_user_request_limitation_panel(
                update=update,
                context=context,
                base_path=root,
                pre_resolved_user=pre_resolved_user,
                limitation_wizard=limitation_wizard
            )
            return PCS.ADMIN_CONVERSATION

        case [LimitationsFlow.DURATION, *rest]:
            match PathBuilder(*rest).segments:
                case []:
                    context.pydc.persistent.bot_message_id = update.effective_message.id
                    context.pydc.persistent.root_path = root.build()
                    # Non cambio root e non salvo relative perché dopo l'input torno al pannello precedente

                    await render_admin_limit_user_request_duration_panel(
                        update=update,
                        context=context,
                        base_path=root.add(LimitationsFlow.DURATION),
                        pre_resolved_user=pre_resolved_user,
                        limitation_wizard=limitation_wizard
                    )
                    return PCS.SET_REQUEST_LIMITATION_DURATION

                case [LimitationsFlow.DURATION_ENDLESS]:
                    limitation_wizard.duration = 0

                    await render_admin_add_user_request_limitation_panel(
                        update=update,
                        context=context,
                        base_path=root,
                        pre_resolved_user=pre_resolved_user,
                        limitation_wizard=limitation_wizard
                    )

                    return PCS.ADMIN_CONVERSATION

        case [LimitationsFlow.SECTIONS, *rest]:
            root = root.add(LimitationsFlow.SECTIONS)
            match PathBuilder(*rest).segments:
                case []:
                    await render_admin_limit_user_request_sections_panel(
                        update=update,
                        context=context,
                        base_path=root,
                        pre_resolved_user=pre_resolved_user,
                        limitation_wizard=limitation_wizard
                    )
                    return PCS.ADMIN_CONVERSATION

                case [section_input]:
                    selected = _parse_section_segment(section_input)
                    if selected is None:
                        log.warning(f"Unhandled SECTIONS subpath: {relative_path.build()}")
                        return PCS.ADMIN_CONVERSATION
                    await handle_request_limitation_topic(context=context, section_input=selected)
                    await render_admin_limit_user_request_sections_panel(
                        update=update,
                        context=context,
                        base_path=root,
                        pre_resolved_user=pre_resolved_user,
                        limitation_wizard=limitation_wizard,
                    )
                    return PCS.ADMIN_CONVERSATION

        case [GlobalAction.CONFIRM, *rest]:
            match PathBuilder(*rest).segments:
                case []:
                    if await render_admin_user_limitation_reason_panel(
                            update=update,
                            context=context,
                            base_path=root.add(GlobalAction.CONFIRM),
                            pre_resolved_user=pre_resolved_user,
                            limitation_wizard=limitation_wizard
                    ):
                        context.pydc.persistent.root_path = root.build()
                        return PCS.SET_REQUEST_LIMITATION_REASON
                    return PCS.ADMIN_CONVERSATION

                case [LimitationsFlow.REASON]:
                    await handle_limitation_confirmation(
                        update=update,
                        context=context,
                        user_id=limitation_wizard.user_id
                    )
                    await render_admin_user_limitation_confirmed_panel(
                        update=update,
                        context=context
                    )
                    return PCS.ADMIN_CONVERSATION

                case _:
                    log.warning(f"Unhandled path in {os.path.realpath(__file__)}: {relative_path.build()}")


async def handle_limitation_duration(update: Update, context: CustomContext):
    duration_input = update.effective_message.text
    wizard = context.get_or_create_limitation_wizard()

    root = PathBuilder.from_string(context.pydc.persistent.root_path)
    context.clear_saved_path(clear_relative=False)

    await safe_delete(update=update, context=context)

    parsed = parse_duration(duration_string=duration_input)
    effective_message = update.effective_message

    if not effective_message:
        raise ValueError("Attribute Update.effective_message cannot be None!")

    if not parsed:
        await effective_message.reply_text(
            text="⚠️ Indica una durata del tipo: <code>1 giorno 50 ore 2 minuti 10 secondi</code>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="🚮 Chiudi", callback_data=GlobalAction.CLOSE_MENU)]
            ]),
            parse_mode=ParseMode.HTML
        )
        return PCS.SET_REQUEST_LIMITATION_DURATION

    wizard.duration = timedelta_to_seconds(parsed)
    return await route_admin_add_request_limitation(
        update=update,
        context=context,
        root=root,
        relative_path=PathBuilder(),
        pre_resolved_user=wizard.user_id
    )


async def handle_limitation_reason(update: Update, context: CustomContext):
    reason_input = update.effective_message.text
    limitation_wizard = context.get_or_create_limitation_wizard()
    limitation_wizard.reason = reason_input

    await safe_delete(update=update, context=context)

    root = PathBuilder.from_string(context.pydc.persistent.root_path)
    context.clear_saved_path(clear_relative=False)

    return await route_admin_add_request_limitation(
        update=update,
        context=context,
        root=root,
        # I add LimitationFlow.REASON to make the router route to the corrrect branch
        relative_path=PathBuilder(GlobalAction.CONFIRM, LimitationsFlow.REASON),
        pre_resolved_user=limitation_wizard.user_id
    )


async def route_admin_remove_request_limitation_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder,
        pre_resolved_user: Union[int, PTBUser, PyroUser]
):
    match relative_path.segments:
        case []:
            await render_admin_remove_user_limitation_panel(
                update=update,
                context=context,
                base_path=root,
                pre_resolved_user=pre_resolved_user
            )

        case [section_obj, *rest]:
            selected_section = _parse_section_segment(section_obj)

            match PathBuilder(*rest).segments:
                case []:
                    remove_all_selected = (selected_section == LimitationsFlow.REMOVE_ALL)
                    limitation = None

                    if not remove_all_selected:
                        user_id = pre_resolved_user if isinstance(pre_resolved_user, int) else pre_resolved_user.id

                        request_limitations = context.get_user_request_limitations(user_id=user_id)
                        limitation = None

                        if request_limitations:
                            limitation = next((
                                lim for lim in request_limitations
                                if lim.section == selected_section),
                                None
                            )

                        if not limitation:
                            await update.effective_message.edit_text(
                                text="⚠️ Limitazione non trovata.",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton(
                                        text="🔙 Indietro",
                                        callback_data=root.build()
                                    )
                                ]])
                            )
                            return PCS.ADMIN_CONVERSATION

                    await render_admin_remove_user_limitation_confirmation_panel(
                        update=update,
                        context=context,
                        base_path=root.add(str(selected_section)),
                        pre_resolved_user=pre_resolved_user,
                        limitation=limitation,
                        remove_all=remove_all_selected
                    )

                case [GlobalAction.CONFIRM]:
                    await handle_remove_user_request_limitation(
                        update=update,
                        context=context,
                        user_id=pre_resolved_user if isinstance(pre_resolved_user, int) else pre_resolved_user.id,
                        selected_section=selected_section
                    )
                    await render_admin_user_limitation_removed_panel(
                        update=update,
                        context=context,
                        base_path=root,
                        pre_resolved_user=pre_resolved_user,
                        section=selected_section
                    )

    return PCS.ADMIN_CONVERSATION


def _parse_section_segment(seg: str) -> LimitationsFlow | RequestSection | None:
    if seg in LimitationsFlow:  # BLOCK_ALL / UNBLOCK_ALL
        return LimitationsFlow(seg)
    try:
        return RequestSection.from_string(seg)
    except (ValueError, KeyError):
        return None
