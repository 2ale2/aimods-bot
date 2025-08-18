from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.helpers.constants.models import PanelConfig, Panel, ButtonItem


async def render_user_request_management_panel(update: Update, context: CallbackContext):
    text = _get_text()

    user_request_management_panel = Panel(
        PanelConfig(
            base_path="user/manage_requests",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="👁 Visiona Richieste", callback_key="view_requests"),
                    ButtonItem(text="❔ Formula Richiesta", callback_key="add_request")
                ],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await user_request_management_panel.render(update, context)


def _get_text():
    text = ("♟ <b>Gestione Richieste</b>\n\n"
            "▫️ Da qui puoi:\n\n"
            "     🔸 <b>Visionare lo stato</b> delle tue richieste\n"
            "     🔸 Formulare una <b>nuova richiesta</b>\n\n"
            "🔹 Scegli un'opzione.")

    return text
