from telegram import Update

from aimods_bot.src.features.moderation.panels.allow_after.handle import set_antispam_link_allow_after
from aimods_bot.src.features.moderation.panels.allow_after.render import render_allow_after_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.ui.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.ui.routing import PathBuilder


async def antispam_link_allow_after_route(
        update: Update,
        context: CustomContext,
        setting: str,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_allow_after_panel(update=update, context=context, setting=setting, base_path=root)
        case [raw_value]:
            # TODO: il tipo di raw_type deve essere AllowafterDurationRoute: da implementare un modo per verificarlo
            # TODO: dov'è il render del pannello?
            await set_antispam_link_allow_after(context=context, setting=setting, raw_value=raw_value)

    return PCS.ADMIN_CONVERSATION
