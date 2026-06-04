from telegram import Update

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.forward.render import render_antispam_forward_panel, \
    render_antispam_forward_category_panel
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.route import punishment_route
from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ChatType
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import SecurityFiltersRoute, GlobalAction
from aimods_bot.src.helpers.constants.path_navigation.moderation import ForwardRoute
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.telegram_utils import set_moderation_bool_setting, not_implemented_yet


async def antispam_forward_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_antispam_forward_panel(update=update, context=context, base_path=root)
            return PCS.ADMIN_CONVERSATION

        case [chat_type, *rest] if chat_type in ChatType:
            return await antispam_forward_category_route(
                update=update,
                context=context,
                category=chat_type,
                root=root.add(chat_type),
                relative_path=PathBuilder(*rest)
            )


async def antispam_forward_category_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder,
        category: ChatType
):
    setting = 'antispam/forward'

    match relative_path.segments:
        case []:
            await render_antispam_forward_category_panel(
                update=update,
                context=context,
                base_path=root,
                chat_type=category
            )
            return PCS.ADMIN_CONVERSATION

        case [SecurityFiltersRoute.PUNISHMENT, *rest]:
            return await punishment_route(
                update=update,
                context=context,
                setting=f'{setting}/{category}',
                root=root.add(SecurityFiltersRoute.PUNISHMENT),
                relative_path=PathBuilder(*rest)
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
            if_not_member = get_value(context=context, path="moderation.antispam.forward.user.if_not_member")
            await set_moderation_bool_setting(
                update=update,
                context=context,
                setting=setting,
                category=category,
                sub_setting=SecurityFiltersRoute.IF_NOT_MEMBER,
                value=not if_not_member
            )

    await render_antispam_forward_category_panel(update=update, context=context, chat_type=category, base_path=root)
    return PCS.ADMIN_CONVERSATION


# noinspection PyUnusedLocal
async def antispam_forward_rate_limit_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            # await render_antispam_forward_rate_limit_panel(update=update, context=context)
            await not_implemented_yet(update=update, context=context)

        case [ForwardRoute.TIMESPAN]:
            # Impostazione tempo di controllo
            await not_implemented_yet(update=update, context=context)

        case [ForwardRoute.PER_USER]:
            # Numero inoltri da parte di uno stesso utente nel timespan impostato
            await not_implemented_yet(update=update, context=context)

        case [ForwardRoute.PER_SOURCE]:
            # Numero inoltri dalla stessa fonte nel timespan impostato
            await not_implemented_yet(update=update, context=context)

        case [ForwardRoute.PER_CONTENT]:
            # Numero inoltri dello stesso messaggio (anche da fonti diverse) nel timespan impostato
            await not_implemented_yet(update=update, context=context)

    return PCS.ADMIN_CONVERSATION
