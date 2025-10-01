from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.allow_after.route import antispam_link_allow_after_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.handle import set_per_message
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.rate_limit.route import \
    antispam_mentions_rate_limit_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.render import render_antispam_mention_panel, \
    render_antispam_mention_per_message_panel, render_antispam_mention_category_panel
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.route import punishment_route
from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import set_moderation_bool_setting


async def antispam_mention_route(update: Update, context: CustomContext, path: list[str]):
    if len(path) == 0:
        await render_antispam_mention_panel(update=update, context=context)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "allow_after":
            if len(path) == 1:
                return await antispam_link_allow_after_route(
                    update=update,
                    context=context,
                    setting="antispam/mention",
                    path=path[1:]
                )
            else:
                await antispam_link_allow_after_route(
                    update=update,
                    context=context,
                    setting="antispam/mention",
                    path=path[1:]
                )
                await render_antispam_mention_panel(update=update, context=context)
                return PCS.ADMIN_CONVERSATION
        case "rate_limit":
            return await antispam_mentions_rate_limit_route(update=update, context=context, path=path[1:])
        case "per_message":
            if len(path) > 1:
                await set_per_message(update=update, context=context, value=int(path[1]))
                await render_antispam_mention_panel(update=update, context=context)
            else:
                await render_antispam_mention_per_message_panel(update=update, context=context)
            return PCS.ADMIN_CONVERSATION
        case "user":
            return await antispam_mention_category_route(update=update, context=context, category="user", path=path[1:])
        case "group":
            return await antispam_mention_category_route(update=update, context=context, category="group", path=path[1:])
        case "channel":
            return await antispam_mention_category_route(update=update, context=context, category="channel", path=path[1:])
        case "bot":
            return await antispam_mention_category_route(update=update, context=context, category="bot", path=path[1:])

    return PCS.ADMIN_CONVERSATION


async def antispam_mention_category_route(update: Update, context: CustomContext, category: str, path: list[str]):
    if len(path) == 0:
        await render_antispam_mention_category_panel(update=update, context=context, category=category)
        return PCS.ADMIN_CONVERSATION

    match path[0]:
        case "punishment":
            return await punishment_route(update=update, context=context, setting=f"antispam/mention/{category}", path=path[1:])
        case "on":
            await set_moderation_bool_setting(
                update=update,
                context=context,
                setting="antispam/mention",
                category=category,
                sub_setting='toggle',
                value=True
            )
        case "off":
            await set_moderation_bool_setting(
                update=update,
                context=context,
                setting="antispam/mention",
                category=category,
                sub_setting='toggle',
                value=False
            )
        case "if_not_member":
            if_not_member = get_value(context=context, path="moderation.antispam.mention.user.if_not_member")
            await set_moderation_bool_setting(
                update=update,
                context=context,
                setting="antispam/mention",
                category=category,
                sub_setting='if_not_member',
                value=not if_not_member
            )

    await render_antispam_mention_category_panel(update=update, context=context, category=category)
    return PCS.ADMIN_CONVERSATION
