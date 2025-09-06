from telegram import Update
from telegram.ext import ContextTypes
from pyrogram.types import ChatMember as PyroChatMember
from telegram import ChatMember as PTBChatMember

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.handle import set_user_requests_limiting_item, \
    handle_request_limitation_duration, get_limited_user, all_topics_are
from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS, CATEGORY_DETAILS
from aimods_bot.src.helpers.constants.models import PanelConfig, Panel, ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import resolve_chat_member, safe_delete
from aimods_bot.src.helpers.utils.time_utils import get_duration_text
from aimods_bot.src.helpers.utils.user_utils import get_member_details_text
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def render_admin_limit_user_request_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int
):
    set_user_requests_limiting_item(context=context)
    context.chat_data["limit_user_requests"]["user_id"] = user_id

    member_response = await resolve_chat_member(
        context=context,
        user_identifier=user_id
    )
    text = await _get_admin_limit_user_request_text(member=member_response["member"], user_id=user_id, context=context)

    admin_limit_user_request_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/limit_user_request/limit_{user_id}",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="⏳ Durata", callback_key="duration"),
                    ButtonItem(text="🗄 Topic", callback_key="topics")
                ],
                [ButtonItem(text="🔙 Annulla", callback_key=None)]
            ]
        )
    )

    message_id = context.chat_data.pop("update_message", None)

    await admin_limit_user_request_panel.render(update=update, context=context, message_id=message_id)


async def _get_header(context: ContextTypes.DEFAULT_TYPE, member: PyroChatMember | PTBChatMember, user_id: int):
    text = ("⛔ <b>Limita Richieste Utente</b>\n\n"
            "▪️ Da qui puoi impostare le limitazioni alle richieste di un utente.\n\n"
            "👤 <b>Dettagli Utente</b>\n\n")

    text += get_member_details_text(user=member, user_identifier=user_id)

    if "limit_user_requests" not in context.chat_data:
        set_user_requests_limiting_item(context=context)
        context.chat_data["limit_user_requests"]["user_id"] = user_id

    total_sec = int(context.chat_data["limit_user_requests"]["duration"])
    if total_sec is not None and total_sec == 0:
        duration_text = "♾ A Tempo Indeterminato"
    else:
        duration_text = await get_duration_text(seconds=total_sec)

    topics = context.chat_data["limit_user_requests"]["topics"]
    topics_text = ""
    for platform, categories in topics.items():
        pl_item = PLATFORM_DETAILS[platform]
        pl_icon, pl_label = pl_item["icon"], pl_item["label"]
        topics_text += f"           {pl_icon} <b>{pl_label}</b>\n"
        for category in categories:
            ct_item = CATEGORY_DETAILS[platform][category]
            ct_icon, ct_label = ct_item["icon"], ct_item["label"]
            value = categories[category]
            topics_text += f"                 🔸 <i>{ct_label}</i> – <code>{value}</code>\n"

    text += f"\n     🗄 <b>Topics</b>\n{topics_text}"
    text += f"\n     ⏳ <b>Durata</b> – {f'<i>{duration_text}</i>' if duration_text else '<code>None</code>'}\n"

    return text


async def _get_admin_limit_user_request_text(
        context: ContextTypes.DEFAULT_TYPE,
        member: PyroChatMember | PTBChatMember,
        user_id: int
):
    text = await _get_header(context=context, member=member, user_id=user_id)
    text += "\n🔹 Scegli un'opzione."

    return text


async def render_admin_limit_user_request_duration_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int
):
    context.chat_data["update_message"] = update.effective_message.id
    member_response = await resolve_chat_member(
        context=context,
        user_identifier=user_id
    )
    text = await _get_admin_limit_user_request_duration_text(context=context, member=member_response["member"], user_id=user_id)

    admin_limit_user_request_duration_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/limit_user_request/limit_{user_id}/duration",
            text=text,
            keyboard=[
                [ButtonItem(text="♾ A tempo indeterminato", callback_key="endless")],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await admin_limit_user_request_duration_panel.render(update=update, context=context)


async def _get_admin_limit_user_request_duration_text(
        context: ContextTypes.DEFAULT_TYPE,
        member: PyroChatMember | PTBChatMember,
        user_id: int
):
    text = await _get_header(context=context, member=member, user_id=user_id)

    text += ("\n🔹 Indica la durata della limitazione.\n\n"
             "<blockquote><b>Esempio</b> – <i>100 giorni 24 ore 1 minuto 1 secondo</i></blockquote>")

    return text


async def render_handled_request_limitation_duration_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    if not update.callback_query:
        await safe_delete(update=update, context=context)

    user_id = get_limited_user(context=context)
    if not await handle_request_limitation_duration(update=update, context=context):
        return PCS.SET_REQUEST_LIMITATION_DURATION

    await render_admin_limit_user_request_panel(update=update, context=context, user_id=user_id)
    return PCS.ADMIN_CONVERSATION


async def render_admin_limit_user_request_topics_panel(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int
):
    member_response = await resolve_chat_member(
        context=context,
        user_identifier=user_id
    )
    text = await _get_admin_limit_user_request_topics_text(
        context=context,
        member=member_response["member"],
        user_id=user_id
    )
    keyboard = _get_admin_limit_user_request_topics_keyboard(context=context)

    admin_limit_user_request_topics_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/limit_user_request/limit_{user_id}/topics",
            text=text,
            keyboard=keyboard,
        )
    )

    await admin_limit_user_request_topics_panel.render(update=update, context=context)


async def _get_admin_limit_user_request_topics_text(
        context: ContextTypes.DEFAULT_TYPE,
        member: PyroChatMember | PTBChatMember,
        user_id: int
):
    text = await _get_header(context=context, member=member, user_id=user_id)

    text += "\n🔹 Scegli i topic da bloccare per l'utente."

    return text


def _get_admin_limit_user_request_topics_keyboard(context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[]]
    for platform, categories in CATEGORY_DETAILS.items():
        pl_item = PLATFORM_DETAILS[platform]
        pl_icon, pl_label = pl_item["icon"], pl_item["label"]
        for category in categories:
            ct_label = CATEGORY_DETAILS[platform][category]["label"]
            if len(keyboard[-1]) >= 3:
                keyboard.append([])
            keyboard[-1].append(ButtonItem(
                text=f"{pl_icon} – {ct_label}",
                callback_key=f"{platform}-{category}")
            )

    if all_topics_are(context=context, what=True):
        all_button = ButtonItem(text="🆓 Sblocca Tutti", callback_key="unblock_all")
    else:
        all_button = ButtonItem(text="🚫 Blocca Tutti", callback_key="block_all")

    keyboard.extend([
        [all_button],
        [ButtonItem(text="🔙 Fine", callback_key="confirm")]
    ])

    return keyboard
