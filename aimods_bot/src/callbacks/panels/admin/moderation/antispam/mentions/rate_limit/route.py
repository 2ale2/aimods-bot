from typing import Literal

from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.rate_limit.handle import \
    set_antispam_mention_rate_limit
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.rate_limit.render import \
    render_antispam_mentions_rate_limit_panel, render_antispam_mentions_rate_limit_setting_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def antispam_mentions_rate_limit_route(update: Update, context: CustomContext, path: list[str]):
    if len(path) == 0:
        await render_antispam_mentions_rate_limit_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "time":
            return await antispam_mentions_rate_limit_setting_route(
                update=update,
                context=context,
                setting="time",
                path=path[1:]
            )
        case "mention":
            return await antispam_mentions_rate_limit_setting_route(
                update=update,
                context=context,
                setting="mention",
                path=path[1:]
            )

    # L'utente ha premuto il toggle
    toggle = True if path[0] == "on" else False
    await set_antispam_mention_rate_limit(update=update, context=context, setting="toggle", value=toggle)
    await render_antispam_mentions_rate_limit_panel(update=update, context=context)
    return PCS.ADMIN_CONVERSATION


async def antispam_mentions_rate_limit_setting_route(
        update: Update,
        context: CustomContext,
        setting: Literal['time', 'mention'],
        path: list[str]
):
    if len(path) == 0:
        await render_antispam_mentions_rate_limit_setting_panel(update=update, context=context, setting=setting)
        return PCS.ADMIN_CONVERSATION

    await set_antispam_mention_rate_limit(update=update, context=context, setting=setting, value=int(path[0]))
    await render_antispam_mentions_rate_limit_panel(update=update, context=context)
    return PCS.ADMIN_CONVERSATION
