from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.category.handle import set_category_toggle, \
    view_whitelist, edit_whitelist
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.category.render import \
    render_antispam_mention_category_panel, render_antispam_mention_category_whitelist_panel
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import not_implemented_yet


async def antispam_mention_category_route(update: Update, context: CallbackContext, category: str, path: list[str]):
    if len(path) == 0:
        await render_antispam_mention_category_panel(update=update, context=context, category=category)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "on":
            await set_category_toggle(update=update, context=context, category=category, value=True)
            await render_antispam_mention_category_panel(update=update, context=context, category=category)
            return PCS.ADMIN_CONVERSATION
        case "off":
            await set_category_toggle(update=update, context=context, category=category, value=False)
            await render_antispam_mention_category_panel(update=update, context=context, category=category)
            return PCS.ADMIN_CONVERSATION
        case "whitelist":
            if len(path) > 1:
                match path[1]:
                    case "view":
                        return await view_whitelist(update=update, context=context, category=category)
                    case "add":
                        return await edit_whitelist(update=update, context=context, category=category, action="add")
                    case "remove":
                        pass
            await render_antispam_mention_category_whitelist_panel(update=update, context=context, category=category)
            return PCS.ADMIN_CONVERSATION
