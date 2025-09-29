from typing import Optional
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.handle import set_user_requests_limiting_item, \
    handle_request_limitation_topic
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.render import \
    render_admin_limit_user_panel, render_admin_limit_user_request_duration_panel, \
    render_handled_request_limitation_duration_panel, render_admin_limit_user_request_sections_panel, \
    render_admin_user_limitation_reason_panel, render_user_requests_limitations_info_panel, \
    render_admin_limit_user_request_panel, render_admin_manage_limitations_panel, render_admin_view_limitations_panel, \
    render_admin_remove_limitations_panel, render_admin_remove_user_limitation_confirmation_panel, \
    render_admin_user_limitation_removed_panel, render_admin_remove_user_limitation_panel
from aimods_bot.src.callbacks.panels.admin.requests_management.sections_management.handle import \
    handle_remove_user_request_limitation
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, wrong_input_message, resolve_user


async def route_admin_manage_limitations(
        update: Update,
        context: CustomContext,
        path: list[str]
):
    if len(path) == 0:
        await render_admin_manage_limitations_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    if len(path) >= 1:
        match path[0]:
            case "limit_user_request":
                return await route_admin_limit_user_request(update=update, context=context, path=path[1:], user_id=None)
            case "view_limitations":
                context.chat_data["action"] = "view"
                context.chat_data["update_message"] = update.effective_message.id
                await render_admin_view_limitations_panel(update=update, context=context)
                return PCS.SET_VIEW_REQUEST_LIMITATION_USER
            case "remove_limitations":
                if len(path) == 1:
                    context.chat_data["action"] = "remove"
                    context.chat_data["update_message"] = update.effective_message.id
                    await render_admin_remove_limitations_panel(update=update, context=context)
                    return PCS.SET_VIEW_REQUEST_LIMITATION_USER
                if len(path) == 2:
                    # expected: ../remove_limitations/<user_id>
                    user_id = int(path[1])
                    await render_admin_remove_user_limitation_panel(update=update, context=context, user_id=user_id)
                    return PCS.ADMIN_CONVERSATION
                if len(path) == 3:
                    # expected: ../remove_limitations/<user_id>/platform:category
                    user_id = int(path[-2])
                    pl, ca = path[-1].split(":")
                    for limitation in context.get_user_request_limitations(user_id=user_id):
                        if [pl, ca] == limitation.section.split(":"):
                            await render_admin_remove_user_limitation_confirmation_panel(
                                update=update,
                                context=context,
                                user_id=int(path[-2]),
                                l=limitation
                            )
                            return PCS.ADMIN_CONVERSATION
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
                if len(path) == 4:
                    # expected: ../remove_limitations/<user_id>/platform:category/yes
                    user_id = int(path[-3])
                    section = path[-2]
                    await handle_remove_user_request_limitation(context=context, user_id=user_id, section=section)
                    await render_admin_user_limitation_removed_panel(
                        update=update,
                        context=context,
                        user_id=user_id,
                        section=section
                    )
                    return PCS.ADMIN_CONVERSATION


async def route_admin_limit_user_request(
        update: Update,
        context: CustomContext,
        path: Optional[list[str]] = None,
        user_id: Optional[int] = None
):
    if not context.pydb.base_path:
        context.set_base_path(base_path="/".join(update.callback_query.data.split("/")[:-1]))

    if path and len(path) > 0 and path[0].startswith("limit_"):
        # expected: limit_<user_id>/...
        user_id = user_id or path[0].split("_")[1]
        path = path[1:]

    if user_id is None:
        if not update.message:
            context.chat_data["update_message"] = update.effective_message.id
            await render_admin_limit_user_request_panel(update=update, context=context)
            return PCS.SET_REQUEST_LIMITATION_USER
        else:
            await safe_delete(update=update, context=context)
            user_id = update.message.text
            if not user_id.isnumeric() and not user_id.startswith("@"):
                await wrong_input_message(
                    update=update,
                    context=context,
                    correct_format="un <b>ID numerico</b> o uno <b>@username</b>"
                )
                return PCS.SET_REQUEST_LIMITATION_USER

    if user_id is not None and isinstance(user_id, str) and not user_id.isdigit():
        user_responses = context.chat_data.setdefault("resolved_users", {})
        member_response = user_responses.get(str(user_id), None)
        if not member_response:
            member_response = await resolve_user(identifier=user_id)
            user_responses[str(user_id)] = member_response
        if member_response["status"] == "success":
            user_id = member_response["user"].id

    user_id = int(user_id)

    limiting_item = set_user_requests_limiting_item(context=context)

    if not limiting_item["user_id"]:
        limiting_item["user_id"] = user_id

    if not path or len(path) == 0:
        context.chat_data.setdefault("resolved_users", {})
        context.chat_data.setdefault("resolved_members", {})
        await render_admin_limit_user_panel(
            update=update,
            context=context,
            user_id=user_id,
            back_button_callback_key=context.pydb.base_path  # se torno indietro, torno al percorso principale
        )
        return PCS.ADMIN_CONVERSATION

    if len(path) == 1:  # non mi devo preoccupare del percorso principale
        match path[0]:
            case "info":
                await render_user_requests_limitations_info_panel(
                    update=update,
                    context=context,
                    user_id=user_id
                )
                return PCS.ADMIN_CONVERSATION
            case "duration":
                await render_admin_limit_user_request_duration_panel(
                    update=update,
                    context=context,
                    user_id=user_id
                )
                return PCS.SET_REQUEST_LIMITATION_DURATION
            case "sections":
                await render_admin_limit_user_request_sections_panel(
                    update=update,
                    context=context,
                    user_id=user_id
                )
                return PCS.ADMIN_CONVERSATION
            case "confirm":
                if not await render_admin_user_limitation_reason_panel(
                        update=update,
                        context=context,
                        user_id=user_id
                ):
                    context.chat_data.pop("resolved_users", None)
                    context.chat_data.pop("resolved_members", None)
                    return PCS.SET_REQUEST_LIMITATION_REASON
                else:
                    return PCS.ADMIN_CONVERSATION

    if len(path) == 2:
        if path[0] == "duration" and path[1] == "endless":
            return await render_handled_request_limitation_duration_panel(
                update=update,
                context=context
            )
        elif path[0] == "sections":
            await handle_request_limitation_topic(update=update, context=context)
            await render_admin_limit_user_request_sections_panel(update=update, context=context, user_id=user_id)
            return PCS.ADMIN_CONVERSATION
