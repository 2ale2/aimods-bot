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
from aimods_bot.src.helpers.constants.constants import CATEGORY_DETAILS
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, wrong_input_message
from aimods_bot.src.helpers.utils.user_utils import get_or_resolve_user


async def route_admin_manage_limitations(
        update: Update,
        context: CustomContext,
        path: list[str]
):
    if not path:
        await render_admin_manage_limitations_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path:
        case ["limit_user_request", *rest]:
            return await route_admin_limit_user_request(update=update, context=context, path=rest, user_id=None)

        case ["view_limitations"]:
            context.pydc.ephemeral.action = "view"
            context.pydc.persistent.bot_message_id = update.effective_message.id
            await render_admin_view_limitations_panel(update=update, context=context)
            return PCS.SET_VIEW_REQUEST_LIMITATION_USER

        case ["remove_limitations"]:
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
                    l=None,
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
                    update=update, context=context, user_id=user_id, l=limitation
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
                section=section if not remove_all else None,
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
        path: Optional[list[str]] = None,
        user_id: Optional[int] = None
):
    if not context.pydc.persistent.base_path and update.callback_query:
        context.set_base_path(base_path=update.callback_query.data.rsplit("/", 1)[0])

    path = path or []
    if path and path[0].startswith("limit_"):
        user_id = path[0].split("_")[1]
        path = path[1:]

    if user_id is None:
        if not update.message:
            context.pydc.persistent.bot_message_id = update.effective_message.id
            await render_admin_limit_user_request_panel(update=update, context=context)
            return PCS.SET_REQUEST_LIMITATION_USER

        await safe_delete(update=update, context=context)
        user_id = update.message.text
        if not user_id.isnumeric() and not user_id.startswith("@"):
            await wrong_input_message(
                update=update,
                context=context,
                correct_format="un <b>ID numerico</b> o uno <b>@username</b>"
            )
            return PCS.SET_REQUEST_LIMITATION_USER

    user_obj = await get_or_resolve_user(context=context, identifier=user_id)

    if not user_obj:
        await wrong_input_message(
            update=update,
            context=context,
            correct_format="un <b>identificatore esistente</b> (Username o ID numerico)"
        )
        return PCS.SET_REQUEST_LIMITATION_USER

    if int(user_id) in context.pydb.admins:
        await wrong_input_message(
            update=update,
            context=context,
            correct_format="uno <b>username</b> o un <b>ID numerico</b> che <b>non appartengano</b> agli admin"
        )
        return PCS.SET_REQUEST_LIMITATION_USER

    user_id = int(user_id)

    base_path = context.pydc.persistent.base_path
    set_true_section = next(
        (f"{pl}:{ca}" for pl, cats in CATEGORY_DETAILS.items()
         for ca in cats if pl in base_path and ca in base_path),
        None
    )

    limiting_item = set_user_requests_limiting_item(context=context, set_true_section=set_true_section)
    if not limiting_item.user_id:
        limiting_item.user_id = user_id

    if not path:
        await render_admin_limit_user_panel(
            update=update,
            context=context,
            user_id=user_id,
            back_button_callback_key=context.pydc.persistent.base_path  # se torno indietro, torno al percorso principale
        )
        return PCS.ADMIN_CONVERSATION

    match path:
        case ["info"]:
            await render_user_requests_limitations_info_panel(update=update, context=context, user_id=user_id)
            return PCS.ADMIN_CONVERSATION

        case ["duration"]:
            await render_admin_limit_user_request_duration_panel(
                update=update, context=context, user_id=user_id, pre_resolved_user=user_obj
            )
            return PCS.SET_REQUEST_LIMITATION_DURATION

        case ["duration", "endless"]:
            return await render_handled_request_limitation_duration_panel(update=update, context=context)

        case ["sections"]:
            await render_admin_limit_user_request_sections_panel(update=update, context=context, user_id=user_id)
            return PCS.ADMIN_CONVERSATION

        case ["sections", _]:  # Gestisce click su topic specifico
            await handle_request_limitation_topic(update=update, context=context)
            await render_admin_limit_user_request_sections_panel(update=update, context=context, user_id=user_id)
            return PCS.ADMIN_CONVERSATION

        case ["confirm"]:
            if not await render_admin_user_limitation_reason_panel(update=update, context=context, user_id=user_id):
                # Reset ephemeral data if reason panel fails/resets
                context.pydc.ephemeral.resolved_users = {}
                context.pydc.ephemeral.resolved_members = {}
                return PCS.SET_REQUEST_LIMITATION_REASON
            return PCS.ADMIN_CONVERSATION
