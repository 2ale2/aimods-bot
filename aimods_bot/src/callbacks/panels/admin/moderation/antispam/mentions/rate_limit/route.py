from typing import Literal

from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.rate_limit.handle import \
    set_antispam_mention_rate_limit
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.rate_limit.render import \
    render_antispam_mentions_rate_limit_panel, render_antispam_mentions_rate_limit_setting_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction
from aimods_bot.src.helpers.constants.path_navigation.moderation import ModerationSettingRoute, RateLimitTimeRoute
from aimods_bot.src.helpers.models.routing import PathBuilder


async def antispam_mentions_rate_limit_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_antispam_mentions_rate_limit_panel(update=update, context=context, base_path=root)
            return PCS.ADMIN_CONVERSATION

        case [toggle] if toggle in (GlobalAction.TOGGLE_ON, GlobalAction.TOGGLE_OFF):
            setting = ModerationSettingRoute.TOGGLE
            value = (toggle == GlobalAction.TOGGLE_ON)
            await set_antispam_mention_rate_limit(update=update, context=context, setting=setting, value=value)
            await render_antispam_mentions_rate_limit_panel(update=update, context=context, base_path=root)
            return PCS.ADMIN_CONVERSATION

        case [moderation_setting] if moderation_setting in (
            ModerationSettingRoute.TIME, ModerationSettingRoute.MENTION
        ):
            root = root.add(ModerationSettingRoute.TIME)
            return await antispam_mentions_rate_limit_setting_route(
                update=update,
                context=context,
                setting=moderation_setting,
                root=root,
                value=None
            )

        case [moderation_setting, value] if moderation_setting in (
            ModerationSettingRoute.TIME, ModerationSettingRoute.MENTION
        ) and value in RateLimitTimeRoute:
            root = root.add(moderation_setting)
            if not isinstance(value, int):
                raise ValueError(f"Invalid setting value type: {value}! ({root.build()})")
            return await antispam_mentions_rate_limit_setting_route(
                update=update,
                context=context,
                setting=ModerationSettingRoute.TIME,
                root=root,
                value=int(value)
            )


async def antispam_mentions_rate_limit_setting_route(
        update: Update,
        context: CustomContext,
        setting: Literal[ModerationSettingRoute.TIME, ModerationSettingRoute.MENTION],
        root: PathBuilder,
        value: int | None = None
):
    if not value:
        await render_antispam_mentions_rate_limit_setting_panel(
            update=update,
            context=context,
            setting=setting,
            base_path=root
        )
        return PCS.ADMIN_CONVERSATION

    await set_antispam_mention_rate_limit(update=update, context=context, setting=setting, value=value)
    await render_antispam_mentions_rate_limit_panel(update=update, context=context, base_path=root)
    return PCS.ADMIN_CONVERSATION
