from typing import Optional
from telegram import Update

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.handle import set_user_requests_limiting_item, \
    handle_request_limitation_topic
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.render import \
    render_admin_limit_user_panel, render_admin_limit_user_request_duration_panel, \
    render_handled_request_limitation_duration_panel, render_admin_limit_user_request_topics_panel, \
    render_admin_user_limitation_reason_panel, render_user_requests_limitations_info_panel, \
    render_admin_limit_user_request_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, wrong_input_message, resolve_chat_member


async def route_admin_limit_user_request(
        update: Update,
        context: CustomContext,
        path: Optional[list[str]] = None,
        user_id: Optional[int] = None
):
    if not context.pyd.base_path:
        context.set_base_path(base_path="/".join(update.callback_query.data.split("/")[:-1]))

    if path and len(path) > 0 and path[0].startswith("limit_"):
        # expected: limit_<user_id>/...
        user_id = user_id or path[0].split("_")[1]
        if not user_id.isdigit():
            member_responses = context.chat_data.setdefault("resolved_users", {})
            member_response = member_responses.get(str(user_id), None)
            if not member_response:
                member_response = await resolve_chat_member(
                    context=context,
                    user_identifier=user_id
                )
                member_responses[str(user_id)] = member_response
            if member_response["status"] == "success":
                user_id = member_response["member"].user.id

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

    limiting_item = set_user_requests_limiting_item(context=context)

    if not limiting_item["user_id"]:
        limiting_item["user_id"] = user_id

    if not path or len(path) == 0:
        context.chat_data.setdefault("resolved_users", {})
        await render_admin_limit_user_panel(
            update=update,
            context=context,
            user_id=user_id,
            back_button_callback_key=context.pyd.base_path  # se torno indietro, torno al percorso principale
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
            case "topics":
                await render_admin_limit_user_request_topics_panel(
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
                    return PCS.SET_REQUEST_LIMITATION_REASON
                else:
                    return PCS.ADMIN_CONVERSATION

    if len(path) == 2:
        if path[0] == "duration" and path[1] == "endless":
            return await render_handled_request_limitation_duration_panel(
                update=update,
                context=context
            )
        elif path[0] == "topics":
            await handle_request_limitation_topic(update=update, context=context)
            await render_admin_limit_user_request_topics_panel(update=update, context=context, user_id=user_id)
            return PCS.ADMIN_CONVERSATION
