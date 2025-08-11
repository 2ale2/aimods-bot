from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.forward.render import render_antispam_forward_panel, \
    render_antispam_forward_category_panel
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.route import punishment_route
from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import set_moderation_bool_setting


async def antispam_forward_route(update: Update, context: CallbackContext, path: list[str]):
    if len(path) == 0:
        await render_antispam_forward_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "rate_limit":
            pass

    # Categoria: 'user', 'group', 'channel' o 'bot'
    return await antispam_forward_category_route(update=update, context=context, category=path[0], path=path[1:])



async def antispam_forward_category_route(update: Update, context: CallbackContext, category: str, path: list[str]):
    if len(path) == 0:
        await render_antispam_forward_category_panel(update=update, context=context, category=category)
        return PCS.ADMIN_CONVERSATION

    setting = 'antispam/forward'

    match path[0]:
        case "punishment":
            return await punishment_route(update=update, context=context, setting=f'antispam/forward/{category}', path=path[1:])
        case "on":
            await set_moderation_bool_setting(
                update=update,
                context=context,
                setting=setting,
                category=category,
                sub_setting='toggle',
                value=True
            )
        case "off":
            await set_moderation_bool_setting(
                update=update,
                context=context,
                setting=setting,
                category=category,
                sub_setting='toggle',
                value=False
            )
        case "if_not_member":
            if_not_member = get_value(context=context, path="moderation.antispam.forward.user.if_not_member")
            await set_moderation_bool_setting(
                update=update,
                context=context,
                setting=setting,
                category=category,
                sub_setting='if_not_member',
                value=not if_not_member
            )

    await render_antispam_forward_category_panel(update=update, context=context, category=category)
    return PCS.ADMIN_CONVERSATION
