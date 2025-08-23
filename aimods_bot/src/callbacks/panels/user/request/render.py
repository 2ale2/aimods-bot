from telegram import Update
from telegram.ext import CallbackContext

from aimods_bot.src.helpers.constants.models import PanelConfig, Panel, ButtonItem


async def render_user_request_management_main_panel(update: Update, context: CallbackContext):
    text = _get_user_request_management_panel_text()

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


def _get_user_request_management_panel_text():
    text = ("♟ <b>Gestione Richieste</b>\n\n"
            "▫️ Da qui puoi:\n\n"
            "     🔸 <b>Visionare lo stato</b> delle tue richieste\n"
            "     🔸 Formulare una <b>nuova richiesta</b>\n\n"
            "🔹 Scegli un'opzione.")

    return text


async def render_user_request_panel(update: Update, context: CallbackContext):
    text = _get_user_request_panel_text()
    user_request_panel = Panel(
        PanelConfig(
            base_path="user/manage_requests/add_request",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="🤖 Android", callback_key="android"),
                    ButtonItem(text="💻 Windows", callback_key="windows")
                ],
                [
                    ButtonItem(text="🍏 iOS", callback_key="ios"),
                    ButtonItem(text="🖥 MacOS", callback_key="macos")
                ],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await user_request_panel.render(update=update, context=context)


def _get_user_request_panel_text():
    text = ("❓ <b>Nuova Richiesta</b>\n\n"
            "🔹 Per <b>quale piattaforma</b> vorresti formulare la richiesta?")
    return text


async def render_user_cant_request_panel(update: Update, context: CallbackContext, reason: str):
    text = _get_user_cant_request_text(reason)
    user_cant_request_panel = Panel(
        PanelConfig(
            base_path="user/manage_requests",
            text=text,
            keyboard=[
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )
    await user_cant_request_panel.render(update=update, context=context)


def _get_user_cant_request_text(reason: str):
    text = ("⚠️ <b>Nuova Richiesta</b>\n\n"
            "❗ Non puoi effettuare una nuova richiesta al momento.\n\n"
            f"▪ <b>Motivo</b> – {reason}")
    return text
