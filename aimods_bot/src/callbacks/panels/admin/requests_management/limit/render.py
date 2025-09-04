from telegram import Update
from telegram.ext import ContextTypes
from pyrogram.types import ChatMember as PyroChatMember
from telegram import ChatMember as PTBChatMember

from aimods_bot.src.helpers.constants.models import PanelConfig, Panel, ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import resolve_chat_member
from aimods_bot.src.helpers.utils.user_utils import get_member_details_text


async def render_admin_limit_user_request_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "active_requests" in update.callback_query:
        # proveniente dalla gestione di una richiesta
        # expected: admin/active_requests/<platform>/<category>/<id>/limit_<user_id>
        user_id = update.callback_query.data.split("_")[-1]
        back_callback = update.callback_query.data.removesuffix(f"/limit_{user_id}")
    else:
        user_id = 1234  # Lo cambierò se arriveremo qua non tramite tasto
        back_callback = None

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


def _get_admin_limit_user_request_text(member: PyroChatMember | PTBChatMember, user_id: int):
    text = ("⛔ <b>Limita Richieste Utente</b>\n\n"
            "▪️ Da qui puoi impostare le limitazioni alle richieste di un utente.\n\n"
            "👤 <b>Dettagli Utente</b>\n\n")

    text += get_member_details_text(user=member, user_identifier=user_id)

    text += "\n     ⏳ <b>Durata</b> – <code>None</code>\n"
    text += "     🗄 <b>Topic</b> – <code>None</code>\n"

    text += "\n🔹 Scegli un'opzione."

    return text
