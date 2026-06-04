from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.allow_after.route import antispam_link_allow_after_route
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.handle import set_per_message
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.mentions.render import render_antispam_mention_panel, \
    render_antispam_mention_per_message_panel, render_antispam_mention_category_panel
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.route import punishment_route
from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ChatType
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import SecurityFiltersRoute, AntispamRoute, GlobalAction
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import set_moderation_bool_setting


async def antispam_mention_route(update: Update, context: CustomContext, root: PathBuilder, relative_path: PathBuilder):
    match relative_path.segments:
        case []:
            await render_antispam_mention_panel(update=update, context=context, base_path=root)
            return PCS.ADMIN_CONVERSATION

        case [SecurityFiltersRoute.ALLOW_AFTER, *rest]:
            root.add(SecurityFiltersRoute.ALLOW_AFTER)
            rest_path = PathBuilder(*rest)

            result = await antispam_link_allow_after_route(
                        update=update,
                        context=context,
                        setting="antispam/mention",
                        root=root,
                        relative_path=rest_path
                    )

            if rest_path.segments:
                return result

            await antispam_link_allow_after_route(
                update=update,
                context=context,
                setting="antispam/mention",
                root=root,
                relative_path=rest_path
            )
            await render_antispam_mention_panel(update=update, context=context, base_path=root + rest_path)
            return PCS.ADMIN_CONVERSATION

        case [AntispamRoute.PER_MESSAGE, *rest]:
            match PathBuilder(*rest).segments:
                case []:
                    await render_antispam_mention_per_message_panel(
                        update=update,
                        context=context,
                        base_path=root.add(AntispamRoute.PER_MESSAGE)
                    )
                case [value] if value.isnumeric():
                    await set_per_message(update=update, context=context, value=int(value))
                    await render_antispam_mention_panel(
                        update=update,
                        context=context,
                        base_path=root
                    )
            return PCS.ADMIN_CONVERSATION

        case [chat_type, *rest] if chat_type in ChatType:
            return await antispam_mention_category_route(
                update=update,
                context=context,
                category=chat_type,
                root=root,
                relative_path=PathBuilder(*rest)
            )

    return PCS.ADMIN_CONVERSATION


async def antispam_mention_category_route(
        update: Update,
        context: CustomContext,
        category: ChatType,
        root: PathBuilder,
        relative_path: PathBuilder
):
    setting = "antispam/mention"
    match relative_path.segments:
        case []:
            await render_antispam_mention_category_panel(
                update=update,
                context=context,
                chat_type=category,
                base_path=root
            )
            return PCS.ADMIN_CONVERSATION

        case [SecurityFiltersRoute.PUNISHMENT, *rest]:
            root.add(SecurityFiltersRoute.PUNISHMENT)
            return await punishment_route(
                update=update,
                context=context,
                setting=f"{setting}/{category}",
                relative_path=PathBuilder(*rest),
                root=root
            )

        case [toggle] if toggle in (GlobalAction.TOGGLE_ON, GlobalAction.TOGGLE_OFF):
            await set_moderation_bool_setting(
                update=update,
                context=context,
                setting=setting,
                category=category,
                sub_setting='toggle',
                value=(toggle == GlobalAction.TOGGLE_ON)
            )

        case [SecurityFiltersRoute.IF_NOT_MEMBER]:
            if_not_member = get_value(context=context, path="moderation.antispam.mention.user.if_not_member")
            await set_moderation_bool_setting(
                update=update,
                context=context,
                setting=setting,
                category=category,
                sub_setting='if_not_member',
                value=not if_not_member
            )

    await render_antispam_mention_category_panel(
        update=update,
        context=context,
        chat_type=category,
        base_path=root
    )
    return PCS.ADMIN_CONVERSATION
