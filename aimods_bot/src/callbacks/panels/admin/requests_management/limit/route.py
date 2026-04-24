from typing import Union

from pyrogram.types import User as PyroUser
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, User as PTBUser

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.handle import handle_request_limitation_topic, \
    handle_request_limitation_duration, handle_limitation_confirmation
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.render import (
    render_admin_add_user_request_limitation_panel, render_admin_limit_user_request_duration_panel,
    render_admin_limit_user_request_sections_panel,
    render_admin_user_limitation_reason_panel, render_admin_manage_limitations_panel,
    render_admin_manage_user_limitations_panel,
    render_admin_remove_user_limitation_confirmation_panel,
    render_admin_user_limitation_removed_panel, render_admin_remove_user_limitation_panel,
    render_admin_user_limitation_confirmed_panel)
from aimods_bot.src.callbacks.panels.admin.requests_management.sections_management.handle import \
    handle_remove_user_request_limitation
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_paths.navigation import AdminManageRequestLimitationsUtils, \
    AdminManageRequestLimitationsRoute, GlobalAction
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import wrong_input_message, is_user_id
from aimods_bot.src.helpers.utils.user_utils import is_admin, resolve_user_from_identifier


async def route_admin_manage_limitations(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_admin_manage_limitations_panel(update=update, context=context, base_path=root)
            return PCS.SET_REQUEST_LIMITATION_USER

        case [identifier, *rest]:
            pre_resolved_user = context.pydc.ephemeral.resolved_users.get(identifier, None)

            if pre_resolved_user is None and is_user_id(identifier):
                pre_resolved_user = int(identifier)

            match PathBuilder(*rest).segments:
                case []:
                    resolved_user = await resolve_user_from_identifier(identifier=identifier)

                    if resolved_user is None:
                        # utente non trovato
                        await wrong_input_message(
                            update=update,
                            context=context,
                            correct_format="un <b>identificatore esistente</b> (Username o ID numerico)"
                        )

                        return PCS.SET_REQUEST_LIMITATION_USER

                    limiting_user = context.pydu.persistent.limiting_user_requests

                    user_id = resolved_user if isinstance(resolved_user, int) else resolved_user.id

                    if await is_admin(context=context, user_id=user_id):
                        await wrong_input_message(
                            update=update,
                            context=context,
                            correct_format="uno <b>username</b> o un <b>ID numerico</b> che <b>non appartengano</b> "
                                           "agli admin"
                        )
                        return PCS.SET_REQUEST_LIMITATION_USER

                    # nel path sempre uno user id
                    relative_path.change(identifier, str(user_id))

                    limiting_user.user_id = user_id

                    if not isinstance(resolved_user, int):
                        limiting_user.username = resolved_user.username
                        context.pydc.ephemeral.resolved_users[resolved_user.id] = resolved_user

                    await render_admin_manage_user_limitations_panel(
                        update=update,
                        context=context,
                        base_path=root,
                        pre_resolved_user=resolved_user
                    )

                    return PCS.ADMIN_CONVERSATION

                case [AdminManageRequestLimitationsUtils.VIEW]:
                    await render_admin_manage_user_limitations_panel(
                        update=update,
                        context=context,
                        base_path=root.add(AdminManageRequestLimitationsUtils.VIEW),
                        pre_resolved_user=pre_resolved_user
                    )
                    return PCS.ADMIN_CONVERSATION

                case [AdminManageRequestLimitationsUtils.ADD, *rest]:
                    return await route_admin_add_request_limitation_route(
                        update=update,
                        context=context,
                        root=root.add(AdminManageRequestLimitationsUtils.ADD),
                        relative_path=PathBuilder(*rest),
                        pre_resolved_user=pre_resolved_user
                    )

                case [AdminManageRequestLimitationsUtils.REMOVE, *rest]:
                    return await route_admin_remove_request_limitation_route(
                        update=update,
                        context=context,
                        root=root.add(AdminManageRequestLimitationsUtils.REMOVE),
                        relative_path=PathBuilder(*rest),
                        pre_resolved_user=pre_resolved_user
                    )


async def route_admin_add_request_limitation_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder,
        pre_resolved_user: Union[int, PTBUser, PyroUser]
):
    match relative_path.segments:
        case []:
            await render_admin_add_user_request_limitation_panel(
                update=update,
                context=context,
                base_path=root,
                pre_resolved_user=pre_resolved_user
            )
            return PCS.ADMIN_CONVERSATION

        case [AdminManageRequestLimitationsRoute.DURATION]:
            context.pydc.persistent.bot_message_id = update.effective_message.id

            await render_admin_limit_user_request_duration_panel(
                update=update,
                context=context,
                base_path=root.add(AdminManageRequestLimitationsRoute.DURATION),
                pre_resolved_user=pre_resolved_user
            )
            return PCS.SET_REQUEST_LIMITATION_DURATION

        case [AdminManageRequestLimitationsRoute.DURATION, duration_input]:
            if not await handle_request_limitation_duration(
                    update=update,
                    context=context,
                    duration_input=duration_input
            ):
                return PCS.SET_REQUEST_LIMITATION_DURATION

            message_id = context.pydc.persistent.bot_message_id
            context.pydc.persistent.bot_message_id = None

            await render_admin_add_user_request_limitation_panel(
                update=update,
                context=context,
                base_path=root,
                pre_resolved_user=pre_resolved_user,
                message_id=message_id
            )
            return PCS.ADMIN_CONVERSATION

        case [AdminManageRequestLimitationsRoute.SECTIONS]:
            await render_admin_limit_user_request_sections_panel(
                update=update,
                context=context,
                base_path=root.add(AdminManageRequestLimitationsRoute.SECTIONS),
                pre_resolved_user=pre_resolved_user
            )
            return PCS.ADMIN_CONVERSATION

        case [AdminManageRequestLimitationsRoute.SECTIONS, section_input]:
            await handle_request_limitation_topic(update=update, context=context, section_input=section_input)
            await render_admin_add_user_request_limitation_panel(
                update=update,
                context=context,
                base_path=root,
                pre_resolved_user=pre_resolved_user
            )
            return PCS.ADMIN_CONVERSATION

        case [GlobalAction.CONFIRM]:
            if await render_admin_user_limitation_reason_panel(
                    update=update,
                    context=context,
                    base_path=root.add(GlobalAction.CONFIRM),
                    pre_resolved_user=pre_resolved_user
            ):
                return PCS.ADMIN_CONVERSATION
            return PCS.SET_REQUEST_LIMITATION_REASON

        case [GlobalAction.CONFIRM, reason_input]:
            await handle_limitation_confirmation(
                update=update,
                context=context,
                user_id=pre_resolved_user if isinstance(pre_resolved_user, int) else pre_resolved_user.id,
                reason=reason_input
            )
            await render_admin_user_limitation_confirmed_panel(
                update=update,
                context=context,
                base_path=root
            )
            return PCS.ADMIN_CONVERSATION


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

        case [selected_section]:
            remove_all_selected = (selected_section == AdminManageRequestLimitationsRoute.REMOVE_ALL)
            limitation = None

            if not remove_all_selected:
                user_id = pre_resolved_user if isinstance(pre_resolved_user, int) else pre_resolved_user.id

                selected_section_list = selected_section.split(":")
                limitation = next((
                    lim for lim in context.get_user_request_limitations(user_id=user_id)
                    if lim.section.split(":") == selected_section_list),
                    None
                )

                if not limitation:
                    await update.effective_message.edit_text(
                        text="⚠️ Limitazione non trovata.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                text="🔙 Indietro",
                                callback_data=relative_path.back()
                            )
                        ]])
                    )

            await render_admin_remove_user_limitation_confirmation_panel(
                update=update,
                context=context,
                base_path=root.add(selected_section),
                pre_resolved_user=pre_resolved_user,
                limitation=limitation,
                remove_all=remove_all_selected
            )

        case [selected_section, GlobalAction.CONFIRM]:
            await handle_remove_user_request_limitation(
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
