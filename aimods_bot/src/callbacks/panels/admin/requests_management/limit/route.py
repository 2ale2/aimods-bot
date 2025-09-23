from typing import Optional
from telegram import Update

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.handle import set_user_requests_limiting_item, \
    handle_request_limitation_topic
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.render import \
    render_admin_limit_user_request_panel, render_admin_limit_user_request_duration_panel, \
    render_handled_request_limitation_duration_panel, render_admin_limit_user_request_topics_panel, \
    render_admin_user_limitation_reason_panel, render_user_requests_limitations_info_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def route_admin_limit_user_request(
        update: Update,
        context: CustomContext,
        path: list[str],
        user_id: Optional[int]
):
    if not context.pyd.base_path:
        context.set_base_path(base_path="/".join(update.callback_query.data.split("/")[:-1]))

    if len(path) > 0 and path[0].startswith("limit_"):
        # expected: limit_<user_id>/...
        user_id = user_id or int(path[0].split("_")[1])
        path = path[1:]

    if user_id is None:
        if not update.message:
            pass
            # ask user for userid
        else:
            pass
            # attempt parsing, if no results i warn but i proceed anyway

    limiting_item = set_user_requests_limiting_item(context=context)

    if not limiting_item["user_id"]:
        limiting_item["user_id"] = user_id

    if len(path) == 0:
        await render_admin_limit_user_request_panel(
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
