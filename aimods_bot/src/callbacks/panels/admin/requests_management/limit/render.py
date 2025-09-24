from typing import Optional, Union

import pytz
from pyrogram.types import ChatMember as PyroChatMember
from telegram import ChatMember as PTBChatMember
from telegram import Update

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.handle import set_user_requests_limiting_item, \
    handle_request_limitation_duration, get_request_limiting_detail, all_topics_are, handle_limitation_confirmation, \
    set_request_limiting_detail
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS, CATEGORY_DETAILS, LOCAL_TZ
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.models import PanelConfig, Panel, ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import resolve_chat_member, safe_delete, is_user_id, \
    add_fucking_at
from aimods_bot.src.helpers.utils.time_utils import get_duration_text
from aimods_bot.src.helpers.utils.user_utils import get_member_details_text, id_to_username

BASE_PATH = "admin/manage_requests/limit_user_request/limit_{}"  # .format(user id da limitare)


async def render_admin_limit_user_request_panel(update: Update, context: CustomContext):
    text = _get_admin_limit_user_request_text()

    admin_limit_user_request_panel = Panel(
        PanelConfig(
            base_path="admin/manage_requests/limit_user_request",
            text=text,
            keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=None)]]
        )
    )

    await admin_limit_user_request_panel.render(update=update, context=context)


def _get_admin_limit_user_request_text():
    text = ("⛔ <b>Limita Richieste Utente</b>\n\n"
            "▪️ Da qui puoi impostare le limitazioni alle richieste di un utente.\n\n"
            "🔹 Indica uno UserID o uno username da limitare.")
    return text


async def render_admin_limit_user_panel(
        update: Update,
        context: CustomContext,
        user_id: Union[int, str],
        back_button_callback_key: Optional[str] = None
):
    member_responses = context.chat_data.setdefault("resolved_users", {})
    member_response = member_responses.get(str(user_id), None)

    if not member_response:
        member_response = await resolve_chat_member(
            context=context,
            user_identifier=user_id
        )
        member_responses[str(user_id)] = member_response

    if limiting_user := get_request_limiting_detail(context=context, what="user_id"):
        user_id = limiting_user
    else:
        if not is_user_id(str(user_id)):
            if member_response["status"] == "success":
                user_id = member_response["member"].user.id
        set_user_requests_limiting_item(context=context)
        set_request_limiting_detail(context=context, what="user_id", value=user_id)

    text = await _get_admin_limit_user_text(member=member_response["member"], user_id=user_id, context=context)

    keyboard = [
        [
            ButtonItem(text="⏳ Durata", callback_key="duration"),
            ButtonItem(text="🗄 Topic", callback_key="topics")
        ],
        [
            ButtonItem(text="✅ Conferma", callback_key="confirm"),
            ButtonItem(
                text="🔙 Annulla",
                callback_key=back_button_callback_key,
                override_path_generation=back_button_callback_key is not None
            )
        ]
    ]

    if context.get_user_request_limitations(user_id=user_id):
        keyboard.insert(0, [ButtonItem(text="👁‍🗨 Visiona Limitazioni", callback_key="info")])

    admin_limit_user_request_panel = Panel(
        PanelConfig(
            base_path=BASE_PATH.format(user_id),
            text=text,
            keyboard=keyboard
        )
    )

    message_id = context.chat_data.pop("update_message", None)

    await admin_limit_user_request_panel.render(update=update, context=context, message_id=message_id)


async def _get_header(context: CustomContext, member: PyroChatMember | PTBChatMember, user_id: int):
    text = ("⛔ <b>Limita Richieste Utente</b>\n\n"
            "▪️ Da qui puoi impostare le limitazioni alle richieste di un utente.\n\n"
            "👤 <b>Dettagli Utente</b>\n\n")

    text += await get_member_details_text(user=member, user_identifier=user_id)

    if "limit_user_requests" not in context.chat_data:
        set_user_requests_limiting_item(context=context)
        context.chat_data["limit_user_requests"]["user_id"] = user_id

    total_sec = int(context.chat_data["limit_user_requests"]["duration"])
    if total_sec is not None and total_sec == 0:
        duration_text = "♾ A Tempo Indeterminato"
    else:
        duration_text = get_duration_text(seconds=total_sec)

    sections = context.chat_data["limit_user_requests"]["sections"]
    section_text = ""
    for platform, categories in sections.items():
        pl_item = PLATFORM_DETAILS[platform]
        pl_icon, pl_label = pl_item["icon"], pl_item["label"]
        section_text += f"           {pl_icon} <b>{pl_label}</b>\n"
        for category in categories:
            ct_item = CATEGORY_DETAILS[platform][category]
            ct_icon, ct_label = ct_item["icon"], ct_item["label"]
            value = categories[category]
            section_text += f"                 🔸 <i>{ct_label}</i> – <code>{value}</code>\n"

    text += f"\n     🗄 <b>Topics</b>\n{section_text}"
    text += f"\n     ⏳ <b>Durata</b> – {f'<i>{duration_text}</i>' if duration_text else '<code>None</code>'}\n"

    return text


async def _get_admin_limit_user_text(
        context: CustomContext,
        member: PyroChatMember | PTBChatMember,
        user_id: int
):
    text = await _get_header(context=context, member=member, user_id=user_id)

    if context.get_user_request_limitations(user_id=user_id):
        text += ("\n<blockquote>ℹ Questo utente possiede già delle limitazioni sulle richieste. "
                 "<b>Le durate in comune si sommeranno</b>. <b>Le permanenti prevalgono</b>.</blockquote>\n")

    text += "\n🔹 Scegli un'opzione."

    return text


async def render_admin_limit_user_request_duration_panel(
        update: Update,
        context: CustomContext,
        user_id: int
):
    context.chat_data["update_message"] = update.effective_message.id

    member_responses = context.chat_data.setdefault("resolved_users", {})
    member_response = member_responses.get(str(user_id), None)
    if not member_response:
        member_response = await resolve_chat_member(
            context=context,
            user_identifier=user_id
        )
        member_responses[str(user_id)] = member_response

    text = await _get_admin_limit_user_request_duration_text(context=context, member=member_response["member"], user_id=user_id)

    admin_limit_user_request_duration_panel = Panel(
        PanelConfig(
            base_path=BASE_PATH.format(user_id) + "/duration",
            text=text,
            keyboard=[
                [ButtonItem(text="♾ A tempo indeterminato", callback_key="endless")],
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await admin_limit_user_request_duration_panel.render(update=update, context=context)


async def _get_admin_limit_user_request_duration_text(
        context: CustomContext,
        member: PyroChatMember | PTBChatMember,
        user_id: int
):
    text = await _get_header(context=context, member=member, user_id=user_id)

    text += ("\n🔹 Indica la durata della limitazione.\n\n"
             "<blockquote><b>Esempio</b> – <i>100 giorni 24 ore 1 minuto 1 secondo</i></blockquote>")

    return text


async def render_handled_request_limitation_duration_panel(
        update: Update,
        context: CustomContext
):
    if not update.callback_query:
        await safe_delete(update=update, context=context)

    user_id = get_request_limiting_detail(context=context, what="user_id")
    if not await handle_request_limitation_duration(update=update, context=context):
        return PCS.SET_REQUEST_LIMITATION_DURATION

    await render_admin_limit_user_panel(update=update, context=context, user_id=user_id)
    return PCS.ADMIN_CONVERSATION


async def render_admin_limit_user_request_topics_panel(
        update: Update,
        context: CustomContext,
        user_id: int
):
    member_responses = context.chat_data.setdefault("resolved_users", {})
    member_response = member_responses.get(str(user_id), None)
    if not member_response:
        member_response = await resolve_chat_member(
            context=context,
            user_identifier=user_id
        )
        member_responses[str(user_id)] = member_response

    text = await _get_admin_limit_user_request_topics_text(
        context=context,
        member=member_response["member"],
        user_id=user_id
    )
    keyboard = _get_admin_limit_user_request_topics_keyboard(context=context)

    admin_limit_user_request_topics_panel = Panel(
        PanelConfig(
            base_path=BASE_PATH.format(user_id) + "/topics",
            text=text,
            keyboard=keyboard
        )
    )

    await admin_limit_user_request_topics_panel.render(update=update, context=context)


async def _get_admin_limit_user_request_topics_text(
        context: CustomContext,
        member: PyroChatMember | PTBChatMember,
        user_id: int
):
    text = await _get_header(context=context, member=member, user_id=user_id)

    text += "\n🔹 Scegli i topic da bloccare per l'utente."

    return text


def _get_admin_limit_user_request_topics_keyboard(context: CustomContext):
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
        [ButtonItem(text="🔙 Fine", callback_key=None)]
    ])

    return keyboard


async def render_admin_user_limitation_reason_panel(
        update: Update,
        context: CustomContext,
        user_id: int
) -> bool:
    """Torna un booleano che indica se l'utente ha scelto almeno una sezione da limitare."""

    context.chat_data["update_message"] = update.effective_message.id

    member_responses = context.chat_data.setdefault("resolved_users", {})
    member_response = member_responses.get(str(user_id), None)
    if not member_response:
        member_response = await resolve_chat_member(
            context=context,
            user_identifier=user_id
        )
        member_responses[str(user_id)] = member_response

    all_topics_false = all_topics_are(context=context, what=False)

    text = await _get_admin_user_limitation_reason_text(
        context=context,
        member=member_response["member"],
        user_id=user_id,
        all_topics_false=all_topics_false
    )

    admin_confirm_user_limitation_panel = Panel(
        PanelConfig(
            base_path=BASE_PATH.format(user_id) + "/reason",
            text=text,
            keyboard=[
                [ButtonItem(text="🔙 Indietro", callback_key=None)]
            ]
        )
    )

    await admin_confirm_user_limitation_panel.render(update=update, context=context)

    return all_topics_false


async def _get_admin_user_limitation_reason_text(
        context: CustomContext,
        member: PyroChatMember | PTBChatMember,
        user_id: int,
        all_topics_false: Optional[bool] = False
):
    text = await _get_header(context=context, member=member, user_id=user_id)

    if all_topics_false:
        text += "\n<blockquote>⚠️ <b>Non hai selezionato alcuna sezione da limitare</b>.</blockquote>"
    else:
        text += "\n✍ <b>Fornisci una motivazione</b>."

    return text


async def render_admin_user_limitation_confirmed_panel(update: Update, context: CustomContext):
    await safe_delete(update=update, context=context)

    message_id = context.chat_data["update_message"]
    await handle_limitation_confirmation(update=update, context=context)

    user_id = get_request_limiting_detail(context=context, what="user_id")
    duration = get_request_limiting_detail(context=context, what="duration")
    sections = get_request_limiting_detail(context=context, what="sections")
    text = _get_admin_user_limitation_confirmed_text(user_id=user_id, duration=duration, sections=sections)

    admin_user_limitation_confirmed_panel = Panel(
        PanelConfig(
            base_path=BASE_PATH.removesuffix("/limit_{}/"),  # "admin/manage_requests/limit_user_request",
            text=text,
            keyboard=[
                [
                    ButtonItem(
                        text="❔ Gestione Richieste",
                        callback_key="admin/manage_requests",
                        override_path_generation=True
                    ),
                    ButtonItem(
                        text="🏠 Home",
                        callback_key="admin",
                        override_path_generation=True
                    )
                ]
            ]
        )
    )

    context.chat_data.pop("limit_user_requests", None)
    await admin_user_limitation_confirmed_panel.render(update=update, context=context, message_id=message_id)


def _get_admin_user_limitation_confirmed_text(user_id: int, duration: Optional[int], sections: dict):
    sections_text = "alla sezione " if len(sections) == 1 else "alle sezioni "
    for pl in sections:
        for ca in sections[pl]:
            if sections[pl][ca]:
                pl_label = PLATFORM_DETAILS[pl]["label"]
                ca_label = CATEGORY_DETAILS[pl][ca]["label"]
                sections_text += f"<b>{ca_label}</b> (<b>{pl_label})</b>, "
    text = (f"✅ <b>Utente <code>{user_id}</code> Limitato</b>\n\n"
            f"🔹 Hai aggiunto <b>{get_duration_text(duration) if duration else "♾ tempo illimitato"}</b> "
            f"{sections_text.removesuffix(', ')}.")
    return text


async def render_user_requests_limitations_info_panel(
        update: Update,
        context: CustomContext,
        user_id: int
):
    keyboard = [[ButtonItem(text="🔙 Indietro", callback_key=None)]]

    text = await _get_user_request_limitations_text(context=context, user_id=user_id)

    user_requests_limitations_info_panel = Panel(
        PanelConfig(
            base_path=BASE_PATH.format(user_id) + "/info",
            text=text,
            keyboard=keyboard
        )
    )

    await user_requests_limitations_info_panel.render(update=update, context=context)


async def _get_user_request_limitations_text(context: CustomContext, user_id: int):
    text = ("⛔ <b>Limitazioni Richieste Utente</b>\n\n"
            "▪️ Qui le informazioni sulle limitazioni imposte ad un utente nel fare le richieste.\n\n"
            "👤 <b>Dettagli Utente</b>\n\n")

    text += await get_member_details_text(context=context, user_identifier=user_id)
    text += "\n🔎 <b>Dettaglio Limitazioni</b>\n"
    limitations = context.get_user_request_limitations(user_id=user_id)
    for n, l in enumerate(limitations):
        pl, ca = l.section.split(":")  # es. section: "windows:software"
        if l.until is not None:
            until = l.until.replace(tzinfo=pytz.UTC).astimezone(LOCAL_TZ).strftime("%d %b %Y %H:%M:%S")
        else:
            until = "♾ A tempo indeterminato"

        reasons_text = ""
        for r in l.reasons:
            reasons_text += f"            – {r}\n"

        created_at = l.created_at.replace(tzinfo=pytz.UTC).astimezone(LOCAL_TZ).strftime("il %d %b %Y alle %H:%M:%S")
        created_by = await id_to_username(context=context, user_id=l.created_by)

        if l.updated_at:
            updated_at = l.updated_at.replace(tzinfo=pytz.UTC).astimezone(LOCAL_TZ).strftime("il %d %b %Y alle %H:%M:%S")
            updated_by = await id_to_username(context=context, user_id=l.updated_by)
        else:
            updated_at = updated_by = None

        pl_label = PLATFORM_DETAILS[pl]["label"]
        ca_label = CATEGORY_DETAILS[pl][ca]["label"]

        text += (f"\n    {n + 1}.  <b>{pl_label}</b> – <b>{ca_label}</b>\n"
                 f"        🔸 <u>Scadenza</u> – <i>{until}</i>\n"
                 f"        🔸 <u>Motivazioni</u>\n"
                 f"{f'<i>{reasons_text}</i>' if reasons_text else '<code>Not Provided</code>'}\n"
                 f"        👤 <i>Aggiunta da "
                 f"{add_fucking_at(created_by) if not is_user_id(created_by) else f'<code>{created_by}</code>'}"
                 f" {created_at}</i>\n")

        if updated_at and updated_by:
            text += ("        🔄 <i>Aggiornata da "
                     f"{add_fucking_at(updated_by) if not is_user_id(updated_by) else f'<code>{updated_by}</code>'}"
                     f" {updated_at}</i>\n")

    text += "\n🔹 Scegli un'opzione."

    return text
