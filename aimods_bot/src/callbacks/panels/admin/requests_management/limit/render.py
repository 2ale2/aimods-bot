from telegram import Update
from telegram.ext import ContextTypes
from pyrogram.types import ChatMember as PyroChatMember
from telegram import ChatMember as PTBChatMember

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.handle import new_user_requests_limiting_item
from aimods_bot.src.helpers.constants.models import PanelConfig, Panel, ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import resolve_chat_member
from aimods_bot.src.helpers.utils.time_utils import get_duration_text
from aimods_bot.src.helpers.utils.user_utils import get_member_details_text


async def render_admin_limit_user_request_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int
):
    if "active_requests" in update.callback_query.data:
        # proveniente dalla gestione di una richiesta
        # expected: admin/active_requests/<platform>/<category>/<id>/limit_<user_id>
        back_callback = update.callback_query.data.removesuffix(f"/limit_{user_id}")
    else:
        user_id = 1234  # Lo cambierò se arriveremo qua non tramite tasto
        back_callback = None

    new_user_requests_limiting_item(context=context)

    member_response = await resolve_chat_member(
        context=context,
        user_identifier=user_id
    )
    text = _get_admin_limit_user_request_text(member=member_response["member"], user_id=user_id)

    admin_limit_user_request_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/limit_user_request/limit_{user_id}",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="⏳ Durata", callback_key="duration"),
                    ButtonItem(text="🗄 Topic", callback_key="topics")
                ],
                [ButtonItem(
                    text="🔙 Annulla",
                    callback_key=back_callback,
                    override_path_generation=(back_callback is not None)
                )]
            ]
        )
    )

    await admin_limit_user_request_panel.render(update=update, context=context)


def _get_header(member: PyroChatMember | PTBChatMember, user_id: int):
    text = ("⛔ <b>Limita Richieste Utente</b>\n\n"
            "▪️ Da qui puoi impostare le limitazioni alle richieste di un utente.\n\n"
            "👤 <b>Dettagli Utente</b>\n\n")

    text += get_member_details_text(user=member, user_identifier=user_id)

    text += "\n     ⏳ <b>Durata</b> – <code>None</code>\n"
    text += "     🗄 <b>Topic</b> – <code>None</code>\n"

    return text


def _get_admin_limit_user_request_text(
        context: ContextTypes.DEFAULT_TYPE,
        member: PyroChatMember | PTBChatMember,
        user_id: int
):
    text = ("⛔ <b>Limita Richieste Utente</b>\n\n"
            "▪️ Da qui puoi impostare le limitazioni alle richieste di un utente.\n\n"
            "👤 <b>Dettagli Utente</b>\n\n")

    text += get_member_details_text(user=member, user_identifier=user_id)

    if "limit_user_requests" not in context.chat_data:
        new_user_requests_limiting_item(context=context)

    duration_text = get_duration_text(int(context.chat_data["limit_user_requests"]["duration"]))

    text += f"\n     ⏳ <b>Durata</b> – {f'<i>{duration_text}</i>' if duration_text else '<code>None</code>'}\n"
    text += "     🗄 <b>Topic</b> – <code>None</code>\n"

    text += "\n🔹 Scegli un'opzione."

    return text


async def render_admin_limit_user_request_duration_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int
):
    member_response = await resolve_chat_member(
        context=context,
        user_identifier=user_id
    )
    text = _get_admin_limit_user_request_duration_text(member=member_response["member"], user_id=user_id)


def _get_admin_limit_user_request_duration_text(member: PyroChatMember | PTBChatMember, user_id: int):

