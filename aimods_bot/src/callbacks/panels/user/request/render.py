from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import RequestCooldown, Request
from aimods_bot.src.helpers.constants.constants import LOCAL_TZ, PLATFORM_DETAILS, CATEGORY_DETAILS
from aimods_bot.src.helpers.constants.models import PanelConfig, Panel, ButtonItem
from aimods_bot.src.helpers.utils.time_utils import get_duration_text


async def render_user_has_cooldown_panel(update: Update, context: CustomContext, rc: RequestCooldown):
    text = _get_user_has_cooldown_text(context=context, rc=rc)

    user_has_cooldown_panel = Panel(
        PanelConfig(
            base_path="user/add_request",
            text=text,
            keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=None)]]
        )
    )

    await user_has_cooldown_panel.render(update=update, context=context)


def _get_user_has_cooldown_text(context: CustomContext, rc: RequestCooldown):
    cooldown_secs = int(context.pydb.configuration.settings.request.cooldown.total_seconds())
    cooldown_text = get_duration_text(cooldown_secs, with_emoji=False)

    text = ("⏳ <b>Hai già formulato una richiesta.</b>\n\n"
            f"<blockquote>❔ Dopo ogni richiesta, ciascun utente deve attendere {cooldown_text}.</blockquote>\n\n"
            f"🔸 <b>Termine Cooldown</b> – <i>{rc.until.astimezone(LOCAL_TZ).strftime('%d %b %Y alle %H:%M:%S')}</i>")

    return text


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
            base_path="user/add_request",
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


async def render_user_cant_request_panel(update: Update, context: CustomContext, reason: str):
    text = _get_user_cant_request_text(reason)
    user_cant_request_panel = Panel(
        PanelConfig(
            base_path="user/view_requests",
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


async def render_cant_request_panel(update: Update, context: CustomContext, message: str):
    cant_request_panel = Panel(
        PanelConfig(
            base_path="user/add_request",
            text=message,
            keyboard=[
                [ButtonItem(
                    text="🔙 Indietro",
                    callback_key="user/add_request",
                    override_path_generation=True
                )]
            ]
        )
    )

    await cant_request_panel.render(update=update, context=context)


async def send_new_request_admin_notification(
        update: Update,
        context: CustomContext,
        admin_id: int,
        request: Request
):
    pl, ca = request.platform.value, request.category.value
    text = _get_new_request_admin_notification_text(pl=pl, ca=ca)
    request_id = request.id

    new_request_notification = Panel(
        PanelConfig(
            base_path="admin",
            text=text,
            keyboard=[
                [
                    ButtonItem(
                        text="👁 Visiona",
                        callback_key=f"admin/manage_requests/active_requests/{pl}/{ca}/{request_id}",
                        override_path_generation=True
                    ),
                    ButtonItem(
                        text="🗃 Richieste Attive",
                        callback_key=f"admin/manage_requests/active_requests/{pl}/{ca}",
                        override_path_generation=True
                    )
                ],
                [
                    ButtonItem(
                        text="🔕 Disattiva Notifiche",
                        callback_key=f"admin/manage_settings/notifications/new_requests/{pl}:{ca}/from_notification",
                        override_path_generation=True
                    )
                ],
                [ButtonItem(text="🚮 Guarda Dopo", callback_key="close_menu")]
            ]
        )
    )

    await new_request_notification.render(update=update, context=context, user_id=admin_id)


def _get_new_request_admin_notification_text(pl: str, ca: str) -> str:
    pl_label = PLATFORM_DETAILS[pl]["label"]
    ca_icon = CATEGORY_DETAILS[pl][ca]["icon"]
    ca_label = CATEGORY_DETAILS[pl][ca]["label"]

    text = ("🔔 <b>Nuova Richiesta Ricevuta</b>\n\n"
            "▫ È stata appena aggiunta una <b>nuova richiesta</b> per la sezione\n\n"
            f"            {ca_icon} <b>{ca_label}</b> ({pl_label})\n\n"
            "🔹 Scegli un'opzione.")

    return text
