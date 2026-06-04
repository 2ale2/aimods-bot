from typing import Optional, Union

from pyrogram.types import User as PyroUser
from telegram import User as PTBUser, Update

from aimods_bot.src.callbacks.panels.admin.requests_management.limit.handle import set_user_requests_limiting_item, \
    get_request_limiting_detail, all_sections_are
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import RequestSectionLimitation
from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS, CATEGORY_DETAILS
from aimods_bot.src.helpers.constants.path_navigation import LimitationsAction, \
    LimitationsFlow as AMRLR, GlobalAction, AdminRoute, LimitationsOp
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, username_to_id, create_and_render_panel, \
    wrong_input_message, chunk_buttons, format_user_mention
from aimods_bot.src.helpers.utils.time_utils import get_duration_text, format_time_as_rome
from aimods_bot.src.helpers.utils.user_utils import get_member_details_text

log = logger.getChild(__name__)


async def render_admin_manage_limitations_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _get_admin_manage_limitations_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]]
    )


def _get_admin_manage_limitations_text():
    text = ("⛔ <b>Gestione Limitazioni</b>\n\n"
            "▪️ Da qui puoi gestire le limitazioni alle richieste di un utente.\n\n"
            "🔹 Indica un ID o uno @username da controllare.")
    return text


async def render_admin_manage_user_limitations_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        pre_resolved_user: Union[int, PTBUser, PyroUser]
):
    message_id = context.pydc.persistent.bot_message_id
    context.pydc.persistent.bot_message_id = None

    text = _get_admin_manage_user_limitations_text(pre_resolved_user=pre_resolved_user)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="👁️‍🗨️ Visiona",
                    callback_key=base_path.add(LimitationsOp.VIEW)
                )
            ],
            [
                ButtonItem(
                    text="➕ Aggiungi",
                    callback_key=base_path.add(LimitationsOp.ADD)
                ),
                ButtonItem(
                    text="➖ Rimuovi",
                    callback_key=base_path.add(LimitationsOp.REMOVE)
                )
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ],
        message_id=message_id
    )


def _get_admin_manage_user_limitations_text(pre_resolved_user: Union[int, PTBUser, PyroUser]):
    text = ("⛔ <b>Gestione Limitazioni</b>\n\n"
            "▪ Da qui puoi gestire le limitazioni sulle richieste dell'utente ")

    if isinstance(pre_resolved_user, int):
        text += format_user_mention(user_id=pre_resolved_user)
    else:
        text += format_user_mention(
            user_id=pre_resolved_user.id,
            username=pre_resolved_user.username,
            first_name=pre_resolved_user.first_name
        )

    text += ".\n\n🔹 Scegli un'opzione."

    return text


async def render_admin_view_user_request_limitations_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        pre_resolved_user: Union[int, PTBUser, PyroUser]
):
    text = await _get_user_request_limitations_text(context=context, pre_resolved_user=pre_resolved_user)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="➕ Aggiungi",
                    callback_key=base_path.back().add(LimitationsOp.ADD)
                ),
                ButtonItem(
                    text="➖ Rimuovi",
                    callback_key=base_path.back().add(LimitationsOp.REMOVE)
                )
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back().back())]
        ]
    )


async def _get_user_request_limitations_text(context: CustomContext, pre_resolved_user: Union[int, PTBUser, PyroUser]):
    if isinstance(pre_resolved_user, int):
        user_id = pre_resolved_user
        user = None
    else:
        user_id = pre_resolved_user.id
        user = pre_resolved_user

    text = ("⛔ <b>Limitazioni Richieste Utente</b>\n\n"
            "▪️ Qui le informazioni sulle limitazioni imposte ad un utente nel fare le richieste.\n\n"
            "👤 <b>Dettagli Utente</b>\n\n")

    text += await get_member_details_text(
        context=context,
        user=user,
        user_identifier=user_id
    )
    text += "\n🔎 <b>Dettaglio Limitazioni</b>\n"
    limitations = context.get_user_request_limitations(user_id=user_id)
    if limitations is None or len(limitations) == 0:
        text += "\n<blockquote>ℹ L'utente non ha limitazioni attive per le richieste.</blockquote>\n"
    else:
        for n, l in enumerate(limitations):
            pl, ca = l.section.split(":")  # es. section: "windows:software"
            until_str = l.until.strftime('%d %b %Y %H:%M:%S') if l.until else "♾ A tempo indeterminato"
            reasons_str = "\n".join([f"            – {r}" for r in l.reasons]) or "<code>Not Provided</code>"

            pl_label = PLATFORM_DETAILS[pl]["label"]
            ca_label = CATEGORY_DETAILS[pl][ca]["label"]

            created_str = f"Aggiunta da {l.created_by} {format_time_as_rome(l.created_at)}"

            text += (f"\n    {n + 1}.  <b>{pl_label}</b> – <b>{ca_label}</b>\n"
                     f"        🔸 <u>Scadenza</u> – <i>{until_str}</i>\n"
                     f"        🔸 <u>Motivazioni</u>\n"
                     f"<i>{reasons_str}</i>\n"
                     f"        👤 <i>{created_str}</i>\n")

            if l.updated_at:
                updated_str = f"Aggiornata da {await username_to_id(l.updated_by)} {format_time_as_rome(l.updated_at)}"
                text += f"        🔄 <i>{updated_str}</i>\n"

    text += "\n🔹 Scegli un'opzione."

    return text


async def render_admin_add_user_request_limitation_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        pre_resolved_user: Union[int, PyroUser, PTBUser],
        message_id: Optional[int] = None
):
    user_id = pre_resolved_user if isinstance(pre_resolved_user, int) else pre_resolved_user.id

    item = context.pydc.persistent.limiting_user_requests
    if not item or item.user_id != user_id:
        set_user_requests_limiting_item(context=context)
        context.pydc.persistent.limiting_user_requests.user_id = user_id

    text = await _get_admin_limit_user_text(context=context, pre_resolved_user=pre_resolved_user)

    keyboard = [
        [
            ButtonItem(text="⏳ Durata", callback_key=base_path.add(AMRLR.DURATION)),
            ButtonItem(text="🗄 Sezioni", callback_key=base_path.add(AMRLR.SECTIONS))
        ],
        [
            ButtonItem(text="✅ Conferma", callback_key=base_path.add(GlobalAction.CONFIRM)),
            ButtonItem(text="🔙 Annulla", callback_key=base_path.back())
        ]
    ]

    if context.get_user_request_limitations(user_id=user_id):
        keyboard.insert(0, [ButtonItem(
            text="👁‍🗨 Visiona Limitazioni",
            callback_key=base_path.back().add(LimitationsOp.VIEW))
        ])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard,
        message_id=message_id
    )


async def _get_header(
        context: CustomContext,
        pre_resolved_user: Union[int, PyroUser, PTBUser]
):
    if isinstance(pre_resolved_user, int):
        user_id = pre_resolved_user
        user = None
    else:
        user_id = pre_resolved_user.id
        user = pre_resolved_user

    text = ("⛔ <b>Limita Richieste Utente</b>\n\n"
            f"▪️ Da qui puoi impostare le limitazioni alle richieste dell'utente <code>{user_id}</code>.\n\n"
            "👤 <b>Dettagli Utente</b>\n\n")

    text += await get_member_details_text(user=user, user_identifier=user_id)

    item = context.pydc.persistent.limiting_user_requests
    if not item:
        set_user_requests_limiting_item(context=context)
        item.user_id = user_id

    total_sec = item.duration
    if total_sec is not None and total_sec == 0:
        duration_text = "♾ A Tempo Indeterminato"
    else:
        duration_text = get_duration_text(seconds=total_sec)

    sections = item.sections
    section_text = ""
    for platform, categories in sections.items():
        pl_item = PLATFORM_DETAILS[platform]
        pl_icon, pl_label = pl_item["icon"], pl_item["label"]
        section_text += f"           {pl_icon} <b>{pl_label}</b>\n"
        for category in categories:
            ct_item = CATEGORY_DETAILS[platform][category]
            ct_icon, ct_label = ct_item["icon"], ct_item["label"]
            value = categories[category]
            section_text += f"                 🔸 <i>{ct_label}</i> – {'🔐' if value else '🔓'}\n"

    text += f"\n     🗄 <b>Sezioni</b>\n{section_text}"
    text += f"\n     ⏳ <b>Durata</b> – {f'<i>{duration_text}</i>' if duration_text else '<code>None</code>'}\n"

    return text


async def _get_admin_limit_user_text(
        context: CustomContext,
        pre_resolved_user: Union[int, PyroUser, PTBUser]
):
    text = await _get_header(context=context, pre_resolved_user=pre_resolved_user)
    user_id = pre_resolved_user if isinstance(pre_resolved_user, int) else pre_resolved_user.id

    if context.get_user_request_limitations(user_id=user_id):
        text += ("\n<blockquote>ℹ Questo utente possiede già delle limitazioni sulle richieste. "
                 "<b>Le durate in comune si sommeranno</b>. <b>Le permanenti prevalgono</b>.</blockquote>\n")

    text += "\n🔹 Scegli un'opzione."

    return text


async def render_admin_limit_user_request_duration_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        pre_resolved_user: Union[int, PyroUser, PTBUser]
):
    text = await _get_admin_limit_user_request_duration_text(
        context=context,
        pre_resolved_user=pre_resolved_user
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [ButtonItem(text="♾ A tempo indeterminato", callback_key=base_path.add(AMRLR.DURATION_ENDLESS))],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


async def _get_admin_limit_user_request_duration_text(
        context: CustomContext,
        pre_resolved_user: Union[int, PyroUser, PTBUser]
):
    text = await _get_header(context=context, pre_resolved_user=pre_resolved_user)
    text += ("\n🔹 Indica la durata della limitazione.\n\n"
             "<blockquote><b>Esempio</b> – <i>100 giorni 24 ore 1 minuto 1 secondo</i></blockquote>")

    return text


async def render_admin_limit_user_request_sections_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        pre_resolved_user: Union[int, PyroUser, PTBUser]
):
    user_id = pre_resolved_user if isinstance(pre_resolved_user, int) else pre_resolved_user.id

    text = await _get_admin_limit_user_request_sections_text(
        context=context,
        pre_resolved_user=pre_resolved_user
    )
    keyboard = _get_admin_limit_user_request_sections_keyboard(context=context, base_path=base_path)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


async def _get_admin_limit_user_request_sections_text(
        context: CustomContext,
        pre_resolved_user: Union[int, PyroUser, PTBUser]
):
    text = await _get_header(context=context, pre_resolved_user=pre_resolved_user)

    text += "\n🔹 Scegli i topic da bloccare per l'utente."

    return text


def _get_admin_limit_user_request_sections_keyboard(context: CustomContext, base_path: PathBuilder):
    buttons = []
    for platform, categories in CATEGORY_DETAILS.items():
        pl_item = PLATFORM_DETAILS[platform]
        for category in categories:
            ct_label = CATEGORY_DETAILS[platform][category]["label"]
            buttons.append(ButtonItem(
                text=f"{pl_item['icon']} – {ct_label}",
                callback_key=base_path.add(f"{platform}-{category}")
            ))

    keyboard = chunk_buttons(buttons, 3)
    is_all_blocked = all_sections_are(context=context, what=True)

    callback_key = base_path.add(AMRLR.UNBLOCK_ALL) if is_all_blocked else base_path.add(AMRLR.BLOCK_ALL)

    toggle_all_btn = ButtonItem(text="🆓 Sblocca Tutti" if is_all_blocked else "🚫 Blocca Tutti",
                                callback_key=callback_key)

    keyboard.extend([
        [toggle_all_btn],
        [ButtonItem(text="🔙 Fine", callback_key=base_path.back())]
    ])
    return keyboard


async def render_admin_user_limitation_reason_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        pre_resolved_user: Union[int, PyroUser, PTBUser]
) -> bool:
    """Torna un booleano che indica se l'utente ha scelto almeno una sezione da limitare."""
    context.pydc.persistent.bot_message_id = update.effective_message.id

    all_sections_false = all_sections_are(context=context, what=False)

    text = await _get_admin_user_limitation_reason_text(
        context=context,
        pre_resolved_user=pre_resolved_user,
        all_sections_false=all_sections_false
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[[ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]]
    )

    return not all_sections_false


async def _get_admin_user_limitation_reason_text(
        context: CustomContext,
        all_sections_false: bool,
        pre_resolved_user: Union[int, PyroUser, PTBUser]
):
    text = await _get_header(context=context, pre_resolved_user=pre_resolved_user)

    if all_sections_false:
        text += "\n<blockquote>⚠️ <b>Non hai selezionato alcuna sezione da limitare</b>.</blockquote>"
    else:
        text += "\n✍ <b>Fornisci una motivazione</b>."

    return text


async def render_admin_user_limitation_confirmed_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    await safe_delete(update=update, context=context)
    message_id = context.pydc.persistent.bot_message_id
    context.pydc.persistent.bot_message_id = None

    user_id = get_request_limiting_detail(context=context, what=LimitationsOp.USER_ID)
    duration = get_request_limiting_detail(context=context, what=AMRLR.DURATION)
    sections = get_request_limiting_detail(context=context, what=AMRLR.SECTIONS)

    text = _get_admin_user_limitation_confirmed_text(user_id=user_id, duration=duration, sections=sections)

    context.pydc.persistent.limiting_user_requests = None

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(
                    text="❔ Gestione Richieste",
                    callback_key=PathBuilder(AdminRoute.ROOT, AdminRoute.MANAGE_REQUESTS)
                ),
                ButtonItem(
                    text="🏠 Home",
                    callback_key=PathBuilder(AdminRoute.ROOT)
                )
            ]
        ],
        message_id=message_id
    )


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

# ==== DA QUI IN AVANTI DA CORREGGERE ====

async def render_admin_view_user_limitations_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        user_id: int
):
    text = await _get_user_request_limitations_text(context=context, user_id=user_id)

    keyboard = [
        [ButtonItem(text="➕ Aggiungi", callback_key=base_path.add(user_id, LimitationsOp.ADD))],
    ]

    limitations = context.get_user_request_limitations(user_id=user_id)

    if limitations is not None and len(limitations) > 0:
        keyboard[0].append(
            ButtonItem(
                text="➖ Rimuovi",
                callback_key=base_path.back().add(LimitationsAction.REMOVE_LIMITATIONS)
            )
        )

    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=base_path.back())])

    message_id = context.pydc.persistent.bot_message_id
    context.pydc.persistent.bot_message_id = None

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard,
        message_id=message_id
    )


async def render_admin_remove_limitations_panel(update: Update, context: CustomContext, base_path: PathBuilder):
    text = _get_admin_manage_limitations_text()

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


async def render_admin_remove_user_limitation_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        pre_resolved_user: Union[int, PTBUser, PyroUser]
):
    user_id = pre_resolved_user if isinstance(pre_resolved_user, int) else pre_resolved_user.id

    limits = context.get_user_request_limitations(user_id=user_id)
    text, keyboard = await _get_admin_remove_user_limitation_text_and_keyboard(
        context=context,
        limits=limits,
        base_path=base_path,
        pre_resolved_user=pre_resolved_user
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard
    )


async def _get_admin_remove_user_limitation_text_and_keyboard(
        context: CustomContext,
        limits: Optional[list[RequestSectionLimitation]],
        base_path: PathBuilder,
        pre_resolved_user: Union[int, PTBUser, PyroUser]
):
    pre_resolved_user_is_int = isinstance(pre_resolved_user, int)

    text = ("➖ <b>Rimuovi Limitazioni</b>\n\n"
            "▪ Da qui puoi rimuovere le limitazioni sulle richieste agli utenti.\n\n")

    text += await get_member_details_text(
        context=context,
        user=pre_resolved_user if pre_resolved_user_is_int else None,
        user_identifier=pre_resolved_user if pre_resolved_user_is_int else pre_resolved_user.id
    ) + "\n"

    if limits is not None and len(limits):
        buttons = []
        for n, l in enumerate(limits):
            pl, ca = l.section.split(":")
            ca_icon = CATEGORY_DETAILS[pl][ca]["icon"]
            ca_label = CATEGORY_DETAILS[pl][ca]["label"]
            pl_label = PLATFORM_DETAILS[pl]["label"]

            until_text = l.until.strftime('%d %B %Y %H:%M:%S') if l.until else "♾ A tempo indeterminato"

            text += (f"      {n + 1}. {ca_icon} <i>{pl_label} – {ca_label}</i>\n"
                     f"          🔸 <u>Scadenza</u> – <i>{until_text}</i>\n\n")

            buttons.append(ButtonItem(text=f"{n + 1}", callback_key=base_path.add(f"{pl}:{ca}")))

        keyboard = chunk_buttons(buttons, 4)
        keyboard.extend([
            [ButtonItem(text="🆓 Rimuovi Tutte", callback_key=AMRLR.REMOVE_ALL)],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ])

        text += "🔹 Scegli la limitazione da rimuovere."
    else:
        keyboard = [[
            ButtonItem(text="🔙 Indietro", callback_key=base_path.back()),
            ButtonItem(text="🏠 Home", callback_key=PathBuilder(AdminRoute.ROOT))
        ]]
        text += ("<blockquote>ℹ L'utente non ha limitazioni attive per le richieste.</blockquote>\n\n"
                 "🔹 Scegli un'opzione.")

    return text, keyboard


async def render_admin_remove_user_limitation_confirmation_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        pre_resolved_user: Union[int, PTBUser, PyroUser],
        limitation: Optional[RequestSectionLimitation],
        remove_all: bool
):
    text = await _get_admin_remove_user_limitation_confirmation(
        context=context,
        pre_resolved_user=pre_resolved_user,
        limitation=limitation,
        remove_all=remove_all
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[[
            ButtonItem(text="✅ Confermo", callback_key=base_path.add(GlobalAction.CONFIRM)),
            ButtonItem(text="🔙 Annulla", callback_key=base_path.back())
        ]]
    )


async def _get_admin_remove_user_limitation_confirmation(
        context: CustomContext,
        pre_resolved_user: Union[int, PTBUser, PyroUser],
        limitation: Optional[RequestSectionLimitation],
        remove_all: bool = False
):
    pre_resolved_user_is_int = isinstance(pre_resolved_user, int)

    text = ("➖ <b>Rimuovi Limitazioni</b>\n\n"
            "▪ Da qui puoi rimuovere le limitazioni sulle richieste agli utenti.\n\n")

    text += await get_member_details_text(
        context=context,
        user=pre_resolved_user if pre_resolved_user_is_int else None,
        user_identifier=pre_resolved_user if pre_resolved_user_is_int else pre_resolved_user.id
    ) + "\n"

    if remove_all:
        text += ("<blockquote>⚠️ <b>Attenzione</b> – Stai rimuovendo tutte le limitazioni dell'utente; tornerà a "
                 "poter fare richieste come un utente normale.</blockquote>\n\n"
                 "🔹 Confermi?")
        return text

    assert (limitation is not None)

    pl, ca = limitation.section.split(":")
    pl_icon = PLATFORM_DETAILS[pl]["icon"]
    ca_label = CATEGORY_DETAILS[pl][ca]["label"]
    until_text = limitation.until.strftime('%d %B %Y %H:%M:%S') if limitation.until else "♾ A tempo indeterminato"

    reasons_text = ""
    for r in limitation.reasons:
        reasons_text += f"            – {r}\n"

    created_str = f"Aggiunta da {f'<code>{limitation.created_by}</code>'} {format_time_as_rome(limitation.created_at)}"

    text += ("🔎 <b>Dettaglio Limitazione</b>\n\n"
             f"      🔸 <u>Sezione</u> – {pl_icon} {ca_label}\n"
             f"      🔸 <u>Scadenza</u> – {until_text}\n"
             f"      🔸 <u>Motivazioni</u>\n"
             f"{f'<i>{reasons_text}</i>' if reasons_text else '<code>Not Provided</code>'}\n"
             f"        👤 <i>{created_str}</i>\n")

    if limitation.updated_at:
        updated_str = (f"Aggiornata da {f'<code>{limitation.updated_by}</code>'} "
                       f"{format_time_as_rome(limitation.updated_at)}")
        text += f"        🔄 <i>{updated_str}</i>\n"

    text += ("\n<blockquote>ℹ Se togli questa limitazione, l'utente <b>potrà nuovamente "
             "formulare delle richieste</b> in questa sezione.</blockquote>\n\n"
             "🔹 Confermi?")

    return text


async def render_admin_user_limitation_removed_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        pre_resolved_user: Union[int, PTBUser, PyroUser],
        section: str
):
    user_id = pre_resolved_user if isinstance(pre_resolved_user, int) else pre_resolved_user.id

    text = _get_admin_user_limitation_removed_text(
        user_id=user_id,
        section=section,
        remove_all=(section == AMRLR.REMOVE_ALL)
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=[
            [
                ButtonItem(text="🔙 Indietro", callback_key=base_path.back()),
                ButtonItem(text="🏠 Home", callback_key=PathBuilder(AdminRoute.ROOT))
            ]
        ]
    )


def _get_admin_user_limitation_removed_text(user_id: int, section: str, remove_all: bool = False) -> str:
    if remove_all:
        text = ("✅ <b>Tutte le Limitazioni Rimosse</b>\n\n"
                f"<blockquote>Ora l'utente <code>{user_id}</code> non ha più limitazioni.</blockquote>\n\n"
                f"🔹 Scegli un'opzione.")
        return text

    pl, ca = section.split(":")
    pl_label = PLATFORM_DETAILS[pl]["label"]
    ca_label = CATEGORY_DETAILS[pl][ca]["label"]

    text = (f"✅ <b>Limitazione per <code>{user_id}</code> Rimossa</b>\n\n"
            "<blockquote>L'utente potrà nuovamente <b>formulare richieste</b> nella sezione "
            f"<b>{ca_label} ({pl_label})</b>.</blockquote>\n\n"
            "🔹 Scegli un'opzione.")

    return text


async def render_request_deleted_panel(update: Update, context: CustomContext):
    text = _get_request_deleted_text()

    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        base_path="admin",
        keyboard=[[ButtonItem(text="🏠 Home", callback_key="admin", override_path_generation=True)]]
    )


def _get_request_deleted_text():
    text = ("⚠️ <b>Problema con la Richiesta</b>\n\n"
            "▫ Questa richiesta non è più tra le richieste attive.\n\n"
            "<blockquote>ℹ <b>Info</b> – È possibile che la richiesta sia stata rimossa da un admin mentre un altro "
            "admin la gestiva, oppure che nello stesso momento l'utente l'abbia cancellata. Prova a verificare se è "
            "ancora presente tra le richieste attive.</blockquote>")
    return text


async def render_request_inactive_panel(update: Update, context: CustomContext):
    text = _get_request_inactive_text()

    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        base_path="admin",
        keyboard=[[ButtonItem(text="🏠 Home", callback_key="admin", override_path_generation=True)]]
    )


def _get_request_inactive_text():
    text = ("⚠️ <b>Richiesta Non Più Attiva</b>\n\n"
            "▫ La richiesta non è più attiva.\n\n"
            "<blockquote>ℹ <b>Info</b> – Un altro admin potrebbe aver completato o rifiutato la richiesta "
            "mentre tu la gestivi. Verifica lo stato attuale nelle richieste attive.</blockquote>")

    return text


async def handle_limitation_identifier(update: Update, context: CustomContext):
    await safe_delete(update=update, context=context)

    action = context.pydc.ephemeral.action
    identifier = update.message.text

    if not identifier.isnumeric():
        identifier = await username_to_id(username=identifier)
        if identifier is None:
            await wrong_input_message(
                update=update,
                context=context,
                correct_message="Manda un ID o uno @username valido."
            )
            return PCS.SET_VIEW_REQUEST_LIMITATION_USER

    if int(identifier) in context.pydb.admins.keys():
        await wrong_input_message(
            update=update,
            context=context,
            correct_message="Manda uno <b>username</b> o un <b>ID numerico</b> che <b>non appartengano</b> agli admin."
        )
        return PCS.SET_VIEW_REQUEST_LIMITATION_USER

    if action == "view":
        await render_admin_view_user_limitations_panel(update=update, context=context, user_id=identifier)
    elif action == "remove":
        await render_admin_remove_user_limitation_panel(update=update, context=context, user_id=int(identifier))
    return PCS.ADMIN_CONVERSATION
