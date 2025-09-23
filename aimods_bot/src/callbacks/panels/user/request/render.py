from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import RequestCooldown
from aimods_bot.src.helpers.constants.constants import LOCAL_TZ
from aimods_bot.src.helpers.constants.models import PanelConfig, Panel, ButtonItem
from aimods_bot.src.helpers.utils.time_utils import get_duration_text


async def render_user_has_cooldown_panel(update: Update, context: CustomContext, rc: RequestCooldown):
    text = _get_user_has_cooldown_text(context=context, rc=rc)

    user_has_cooldown_panel = Panel(
        PanelConfig(
            base_path="user/manage_requests/add_request",
            text=text,
            keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=None)]]
        )
    )

    await user_has_cooldown_panel.render(update=update, context=context)


def _get_user_has_cooldown_text(context: CustomContext, rc: RequestCooldown):
    cooldown_secs = int(context.pyd.configuration.settings.request.cooldown.total_seconds())
    cooldown_text = get_duration_text(cooldown_secs, with_emoji=False)

    text = ("⏳ <b>Hai già formulato una richiesta.</b>\n\n"
            f"<blockquote>❔ Dopo ogni richiesta, ciascun utente deve attendere {cooldown_text}.</blockquote>\n\n"
            f"🔸 <b>Termine Cooldown</b> – <i>{rc.until.astimezone(LOCAL_TZ).strftime('%d %b %Y alle %H:%M:%S')}</i>")

    return text


async def render_user_request_management_main_panel(update: Update, context: CustomContext):
    text = _get_user_request_management_panel_text()

    add_request_icon = "❔" if not context.user_request_cooldown() else "⏳"

    user_request_management_panel = Panel(
        PanelConfig(
            base_path="user/manage_requests",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="👁 Visiona Richieste", callback_key="view_requests"),
                    ButtonItem(text=f"{add_request_icon} Formula Richiesta", callback_key="add_request")
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


async def render_user_request_panel(update: Update, context: CustomContext):
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
    # SIMONE GAYYYYY
    await user_request_panel.render(update=update, context=context)


def _get_user_request_panel_text():
    text = ("❓ <b>Nuova Richiesta</b>\n\n"
            "🔹 Per <b>quale piattaforma</b> vorresti formulare la richiesta?")
    return text


async def render_user_cant_request_panel(update: Update, context: CustomContext, reason: str):
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
