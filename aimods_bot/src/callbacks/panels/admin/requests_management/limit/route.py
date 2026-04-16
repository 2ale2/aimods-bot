from typing import Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.handle import handle_request_limitation_topic, \
    handle_limitation_user, handle_request_limitation_duration
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.render import \
    (render_admin_add_user_request_limitation_panel, render_admin_limit_user_request_duration_panel,
     render_admin_limit_user_request_sections_panel,
     render_admin_user_limitation_reason_panel, render_admin_manage_limitations_panel,
     render_admin_manage_user_limitations_panel,
     render_admin_remove_limitations_panel, render_admin_remove_user_limitation_confirmation_panel,
     render_admin_user_limitation_removed_panel, render_admin_remove_user_limitation_panel,
     render_admin_view_user_request_limitations_panel)
from aimods_bot.src.callbacks.panels.admin.requests_management.sections_management.handle import \
    handle_remove_user_request_limitation
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_paths.navigation import AdminManageRequestLimitationsUtils, \
    AdminManageRequestLimitationsRoute, GlobalAction
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import wrong_input_message
from aimods_bot.src.helpers.utils.user_utils import is_admin


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
            match PathBuilder(*rest).segments:
                case []:
                    resolved_user = await handle_limitation_user(identifier=identifier)

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

                    limiting_user.user_id = user_id

                    if not isinstance(resolved_user, int):
                        limiting_user.username = resolved_user.username
                        context.pydc.ephemeral.resolved_users[resolved_user.id] = resolved_user

                    await render_admin_manage_user_limitations_panel(
                        update=update,
                        context=context,
                        base_path=root.add(user_id),
                        resolved_user=resolved_user
                    )

                    return PCS.ADMIN_CONVERSATION

                case [AdminManageRequestLimitationsUtils.LIMIT, *rest]:
                    return await route_admin_limit_user_request(
                        update=update,
                        context=context,
                        root=root.add(AdminManageRequestLimitationsUtils.LIMIT),
                        relative_path=PathBuilder(*rest),
                        user_id=identifier
                    )

                case [AdminManageRequestLimitationsUtils.VIEW]:
                    pre_resolved_user = context.pydc.ephemeral.resolved_users.get(
                        identifier, None
                    ) or identifier

                    await render_admin_manage_user_limitations_panel(
                        update=update,
                        context=context,
                        base_path=root.add(AdminManageRequestLimitationsUtils.VIEW),
                        resolved_user=pre_resolved_user
                    )
                    return PCS.ADMIN_CONVERSATION

        case [identifier, AdminManageRequestLimitationsUtils.REMOVE]:
            context.pydc.ephemeral.action = "remove"
            context.pydc.persistent.bot_message_id = update.effective_message.id
            await render_admin_remove_limitations_panel(update=update, context=context)
            return PCS.SET_VIEW_REQUEST_LIMITATION_USER

        case ["remove_limitations", user_id_str]:
            await render_admin_remove_user_limitation_panel(
                update=update, context=context, user_id=int(user_id_str)
            )
            return PCS.ADMIN_CONVERSATION

        case ["remove_limitations", user_id_str, target]:
            user_id = int(user_id_str)
            if target == "remove_all":
                await render_admin_remove_user_limitation_confirmation_panel(
                    update=update,
                    context=context,
                    user_id=user_id,
                    limitation=None,
                    remove_all=True
                )
                return PCS.ADMIN_CONVERSATION

            target_list = target.split(":")
            limitation = next((
                lim for lim in context.get_user_request_limitations(user_id=user_id)
                if lim.section.split(":") == target_list),
                None
            )

            if limitation:
                await render_admin_remove_user_limitation_confirmation_panel(
                    update=update, context=context, user_id=user_id, limitation=limitation
                )
            else:
                await update.effective_message.edit_text(
                    text="⚠️ Limitazione non trovata.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            text="🔙 Indietro",
                            callback_data=f"admin/manage_requests/manage_limitations/remove_limitations/{user_id}"
                        )
                    ]])
                )
            return PCS.ADMIN_CONVERSATION

        case ["remove_limitations", user_id_str, section, "yes"]:
            user_id = int(user_id_str)
            remove_all = (section == "remove_all")
            await handle_remove_user_request_limitation(
                context=context,
                user_id=user_id,
                selected_section=section if not remove_all else None,
                remove_all=remove_all
            )
            await render_admin_user_limitation_removed_panel(
                update=update,
                context=context,
                user_id=user_id,
                section=section if not remove_all else None,
                remove_all=remove_all
            )
            return PCS.ADMIN_CONVERSATION


async def route_admin_limit_user_request(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder,
        user_id: Optional[int] = None
):
    if not context.pydc.persistent.base_path and update.callback_query:
        context.set_base_path(base_path=update.callback_query.data.rsplit("/", 1)[0])

    match relative_path.segments:
        case []:
            context.pydc.persistent.bot_message_id = update.effective_message.id
            await render_admin_manage_limitations_panel(
                update=update,
                context=context,
                base_path=root
            )
            return PCS.SET_REQUEST_LIMITATION_USER

        case [identifier, AdminManageRequestLimitationsUtils.VIEW]:
            await render_admin_view_user_request_limitations_panel(
                update=update,
                context=context,
                base_path=root.add(AdminManageRequestLimitationsUtils.VIEW),
                user_id=identifier
            )

            return PCS.ADMIN_CONVERSATION

        case [identifier, AdminManageRequestLimitationsUtils.ADD, *rest]:
            return await route_admin_add_request_limitation_route(
                update=update,
                context=context,
                root=root.add(AdminManageRequestLimitationsUtils.ADD),
                relative_path=PathBuilder(*rest),
                user_id=int(identifier)
            )

        case [identifier, AdminManageRequestLimitationsUtils.REMOVE, *rest]:
            await route_admin_remove_request_limitation_route(
                update=update,
                context=context,
                root=root.add(AdminManageRequestLimitationsUtils.REMOVE),
                relative_path=PathBuilder(*rest),
                user_id=int(identifier)
            )


async def route_admin_add_request_limitation_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder,
        user_id: int
):
    pre_resolved_user = context.pydc.ephemeral.resolved_users.get(user_id, None)

    match relative_path.segments:
        case []:
            await render_admin_add_user_request_limitation_panel(
                update=update,
                context=context,
                base_path=root,
                user_id=user_id,
                pre_resolved_user=pre_resolved_user
            )
            return PCS.ADMIN_CONVERSATION

        case [AdminManageRequestLimitationsRoute.DURATION]:
            context.pydc.persistent.bot_message_id = update.effective_message.id

            await render_admin_limit_user_request_duration_panel(
                update=update,
                context=context,
                base_path=root.add(AdminManageRequestLimitationsRoute.DURATION),
                user_id=user_id,
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

            await render_admin_add_user_request_limitation_panel(
                update=update,
                context=context,
                base_path=root,
                user_id=user_id
            )
            return PCS.ADMIN_CONVERSATION

        case [AdminManageRequestLimitationsRoute.SECTIONS]:
            await render_admin_limit_user_request_sections_panel(
                update=update,
                context=context,
                base_path=root.add(AdminManageRequestLimitationsRoute.SECTIONS),
                user_id=user_id,
                pre_resolved_user=pre_resolved_user
            )
            return PCS.ADMIN_CONVERSATION

        case [AdminManageRequestLimitationsRoute.SECTIONS, section_input]:
            await handle_request_limitation_topic(update=update, context=context, section_input=section_input)
            await render_admin_limit_user_request_sections_panel(
                update=update,
                context=context,
                base_path=root.back(),
                user_id=user_id,
                pre_resolved_user=pre_resolved_user
            )
            return PCS.ADMIN_CONVERSATION

        case [GlobalAction.CONFIRM]:
            if not await render_admin_user_limitation_reason_panel(
                    update=update,
                    context=context,
                    base_path=root.add(GlobalAction.CONFIRM),
                    user_id=user_id,
                    pre_resolved_user=pre_resolved_user
            ):
                if pre_resolved_user:
                    del context.pydc.ephemeral.resolved_users[user_id]
                return PCS.SET_REQUEST_LIMITATION_REASON
            return PCS.ADMIN_CONVERSATION


async def route_admin_remove_request_limitation_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder,
        user_id: int
):
    pre_resolved_user = context.pydc.ephemeral.resolved_users.get(user_id, None)

    match relative_path.segments:
        case []:
            await render_admin_remove_user_limitation_panel(
                update=update,
                context=context,
                base_path=root,
                user_id=user_id
            )
            return PCS.ADMIN_CONVERSATION

        case [selected_section]:
            remove_all_selected = (selected_section == AdminManageRequestLimitationsRoute.REMOVE_ALL)
            limitation = None

            if not remove_all_selected:
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
                    return PCS.ADMIN_CONVERSATION

            await render_admin_remove_user_limitation_confirmation_panel(
                update=update,
                context=context,
                base_path=root.add(selected_section),
                user_id=user_id,
                limitation=limitation,
                remove_all=remove_all_selected
            )
            return PCS.ADMIN_CONVERSATION

        case [selected_section, GlobalAction.CONFIRM]:
            await handle_remove_user_request_limitation(
                context=context,
                user_id=user_id,
                selected_section=selected_section
            )

