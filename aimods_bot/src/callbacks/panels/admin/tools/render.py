from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.path_navigation.admin import AdminTools
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel


def _get_header():
    return "🔧 <b>Strumenti</b>"


async def render_admin_tools_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _get_admin_tools_panel_text()

    keyboard = [
        [ButtonItem(text="🗓️ Calendario", callback_key=base_path.add(AdminTools.CALENDAR))],
        [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
    ]

    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=keyboard
    )


def _get_admin_tools_panel_text():
    return _get_header() + "\n\n🔹 Scegli lo strumento."
