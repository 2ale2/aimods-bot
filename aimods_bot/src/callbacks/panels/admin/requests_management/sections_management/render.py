from typing import Literal, Optional

from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import CategorySetting
from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS, CATEGORY_DETAILS, Platform, Category
from aimods_bot.src.helpers.constants.models import ButtonItem
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel, chunk_buttons, get_config
from aimods_bot.src.helpers.utils.time_utils import pluralize


def _get_header(subheader: Optional[str] = None) -> str:
    base = "⏯️ <b>Gestione Sezioni</b>\n\n"
    if subheader:
        base += f"{subheader}\n\n"
    return f"{base}▪ Da qui puoi impostare i parametri di apertura e chiusura delle sezioni per le richieste.\n\n"


def _format_limit_text(limit: Optional[int]) -> str:
    """Formatta il testo del limite."""
    return f"{pluralize(limit, 'richiesta', 'richieste')}" if limit is not None else "🆓 <b>Nessun Limite</b>"


async def render_admin_request_section_configure_panel(update: Update, context: CustomContext):
    text = _get_admin_request_section_configure_text()

    buttons = [
        ButtonItem(text=f"{item['icon']} {item['label']}", callback_key=key)
        for key, item in PLATFORM_DETAILS.items()
    ]
    keyboard = chunk_buttons(buttons=buttons, size=2)
    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=None)])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="admin/manage_requests/manage_sections",
        text=text,
        keyboard=keyboard
    )


def _get_admin_request_section_configure_text():
    return _get_header() + "🔹 Scegli una piattaforma."


async def render_admin_request_section_configure_platform_panel(
        update: Update,
        context: CustomContext,
        platform: Platform
):
    text = _get_admin_request_section_configure_platform_text()

    buttons = [
        ButtonItem(text=f"{item['icon']} {item['label']}", callback_key=key)
        for key, item in CATEGORY_DETAILS[platform.value].items()
    ]
    keyboard = chunk_buttons(buttons=buttons, size=2)
    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=None)])

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/manage_sections/{platform.value}",
        text=text,
        keyboard=keyboard
    )


def _get_admin_request_section_configure_platform_text():
    return _get_header() + "🔹 Scegli una categoria."


async def render_admin_request_section_configure_category_panel(
        update: Update,
        context: CustomContext,
        platform: Platform,
        category: Category
):
    config = get_config(context=context, platform=platform, category=category)

    text = _get_admin_request_section_configure_category_text(config=config, platform=platform, category=category)
    toggle_text = f"{'📬 Apri' if not config.toggle else '📪 Chiudi'}"
    toggle_callback = "open" if not config.toggle else "close"

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/manage_sections/{platform.value}/{category.value}",
        text=text,
        keyboard=[
            [
                ButtonItem(text=toggle_text, callback_key=toggle_callback),
                ButtonItem(text="🗂 Limite", callback_key="limit")
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    )


def _get_admin_request_section_configure_category_text(config: CategorySetting, platform: Platform, category: Category):
    ca_item = CATEGORY_DETAILS[platform.value][category.value]
    status_text = '📬 <i>Aperto</i>' if config.toggle else '📪 <i>Chiuso</i>'

    return (
        f"{_get_header()}"
        f"      {ca_item['icon']} <b>{ca_item['label']}</b>\n"
        f"          🔸 <u>Stato</u> – {status_text}\n"
        f"          🔸 <u>Limite Richieste</u> – <i>{_format_limit_text(config.limit)}</i>\n\n"
        f"🔹 Scegli un'opzione."
    )


async def render_admin_request_section_toggle_panel(
        update: Update,
        context: CustomContext,
        platform: Platform,
        category: Category,
        action: Literal["open", "close"]
):
    opening = action == "open"

    text = _get_admin_request_section_toggle_panel_text(
        context=context,
        platform=platform,
        category=category,
        is_opening=opening
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/manage_sections/{platform.value}/{category.value}/{action}",
        text=text,
        keyboard=[
            [
                ButtonItem(text="📬 Apri" if opening else "📪 Chiudi", callback_key='yes'),
                ButtonItem(text="🔙 Indietro", callback_key=None)
            ]
        ]
    )


def _get_admin_request_section_toggle_panel_text(
        context: CustomContext,
        platform: Platform,
        category: Category,
        is_opening: bool
):
    config = get_config(context=context, platform=platform, category=category)

    text = _get_header(subheader=f"  → <i>{'📬 Apertura' if is_opening else '📪 Chiusura'} Manuale</i>")
    text += (f"<blockquote>ℹ <b>Info</b> – Se {'apri' if is_opening else 'chiudi'} questa sezione, "
             f"gli utenti {'non ' if not is_opening else ''}potranno formulare altre richieste.</blockquote>\n\n")

    if is_opening and config.limit is not None:
        active_requests = len(context.get_active_category_requests(platform=platform, category=category))
        if active_requests >= config.limit:
            text += (
                f"<blockquote>⚠️ <b>Attenzione</b> – Hai un numero di richieste attive <b>pari o superiore al limite</b> "
                f"impostato (<b>{pluralize(active_requests, 'richiesta', 'richieste')} su {config.limit}</b>); "
                f"se la riapri, il <b>limite verrà automaticamente rimosso (0)</b>.</blockquote>\n\n"
            )

    return text + "🔹 <b>Confermi</b>?"


async def render_admin_request_section_toggled_panel(
        update: Update,
        context: CustomContext,
        platform: Platform,
        category: Category,
        action: Literal["open", "close"]
):
    text = _get_admin_request_section_toggled_text(platform=platform, category=category, is_opening=(action == "open"))

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/manage_sections/{platform.value}/{category.value}/{action}",
        text=text,
        keyboard=[[
            ButtonItem(text="🔙 Indietro", callback_key=None),
            ButtonItem(text="🏠 Home", callback_key="admin", override_path_generation=True)
        ]]
    )


def _get_admin_request_section_toggled_text(
        platform: Platform,
        category: Category,
        is_opening: bool
):
    pl_label = PLATFORM_DETAILS[platform.value]['label']
    ca_label = CATEGORY_DETAILS[platform.value][category.value]['label']

    return (
        f"✅ <b>Sezione {ca_label} ({pl_label}) {'Aperta' if is_opening else 'Chiusa'}</b>\n\n"
        f"🔹 Scegli un'opzione."
    )


async def render_admin_request_section_limit_panel(
        update: Update,
        context: CustomContext,
        platform: Platform,
        category: Category
):
    text = _get_admin_request_section_limit_text(context=context, platform=platform, category=category)

    keyboard = [
        [ButtonItem(text="🆓 Nessun Limite", callback_key="0")],
        [
            ButtonItem(text="1 Richiesta", callback_key="1"),
            ButtonItem(text="2 Richieste", callback_key="2"),
            ButtonItem(text="3 Richieste", callback_key="3")
        ],
        [
            ButtonItem(text="4 Richieste", callback_key="4"),
            ButtonItem(text="5 Richieste", callback_key="5"),
            ButtonItem(text="6 Richieste", callback_key="6")
        ],
        [
            ButtonItem(text="7 Richieste", callback_key="7"),
            ButtonItem(text="8 Richieste", callback_key="8"),
            ButtonItem(text="9 Richieste", callback_key="9")
        ],
        [
            ButtonItem(text="10 Richieste", callback_key="10"),
            ButtonItem(text="15 Richieste", callback_key="15"),
            ButtonItem(text="20 Richieste", callback_key="20")
        ],
        [ButtonItem(text="🔙 Indietro", callback_key=None)]
    ]

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/manage_sections/{platform.value}/{category.value}/limit",
        text=text,
        keyboard=keyboard
    )


def _get_admin_request_section_limit_text(context: CustomContext, platform: Platform, category: Category):
    ca_item = CATEGORY_DETAILS[platform.value][category.value]
    config = get_config(context=context, platform=platform, category=category)

    return (
        f"{_get_header(subheader='  → 🗂 <i>Imposta Limite</i>')}"
        f"      {ca_item['icon']} <b>{ca_item['label']}</b>\n"
        f"        🔸 <u>Limite Attuale</u> – <i>{_format_limit_text(config.limit)}</i>\n\n"
        f"<blockquote>ℹ Al raggiungimento di questo limite, questa sezione di richieste verrà chiusa automaticamente.</blockquote>\n\n"
        f"🔹 Scegli un'opzione."
    )


async def render_admin_request_section_limit_confirm_panel(
        update: Update,
        context: CustomContext,
        platform: Platform,
        category: Category,
        limit: int
):
    text = _get_admin_request_section_limit_confirm_text(
        context=context,
        platform=platform,
        category=category,
        limit=limit
    )

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/manage_sections/{platform.value}/{category.value}/limit/{limit}",
        text=text,
        keyboard=[
            [
                ButtonItem(text="✅ Conferma", callback_key="yes"),
                ButtonItem(text="🔙 Annulla", callback_key=None)
            ]
        ]
    )


def _get_admin_request_section_limit_confirm_text(
        context: CustomContext,
        platform: Platform,
        category: Category,
        limit: int
):
    config = get_config(context=context, platform=platform, category=category)
    ca_item = CATEGORY_DETAILS[platform.value][category.value]

    r_text = f"↪️ {pluralize(limit, 'richiesta', 'richieste')}" if limit != 0 else "🆓 Nessun Limite"

    warning = ""
    if limit != 0 and config.limit and limit < config.limit:
        warning = (
            "<blockquote>⚠️ <b>Attenzione</b> – Se il limite viene ridotto e le richieste attive "
            "superano il nuovo limite, la sezione verrà automaticamente chiusa.</blockquote>\n\n"
        )

    return (
        f"{_get_header(subheader='  → 🗂 <i>Imposta Limite</i>')}"
        f"      {ca_item['icon']} <b>{ca_item['label']}</b>\n"
        f"            🔸 <u>Limite Attuale</u> – <i>{_format_limit_text(config.limit)}</i>\n\n"
        f"🔹 Stai <b>modificando il limite di richieste</b> per questa sezione a:\n\n"
        f"            <b>{r_text}</b>\n\n"
        f"{warning}"
        f"🔹 <b>Confermi?</b>"
    )


async def render_admin_request_section_limit_confirmed_panel(
        update: Update,
        context: CustomContext,
        platform: Platform,
        category: Category,
        limit: int
):
    text = _get_admin_request_section_limit_confirmed_text(platform=platform, category=category, limit=limit)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=f"admin/manage_requests/manage_sections/{platform.value}/{category.value}/limit",
        text=text,
        keyboard=[
            [
                ButtonItem(text="🔙 Indietro", callback_key=None),
                ButtonItem(text="🏠 Home", callback_key="admin", override_path_generation=True)
            ]
        ]
    )


def _get_admin_request_section_limit_confirmed_text(
        platform: Platform,
        category: Category,
        limit: int
):
    p_label = PLATFORM_DETAILS[platform.value]["label"]
    c_label = CATEGORY_DETAILS[platform.value][category.value]["label"]
    r_text = f"↪️ {pluralize(limit, 'richiesta', 'richieste')}" if limit != 0 else "🆓 Nessun Limite"
    return (
        f"✅ <b>Limite Richieste {c_label} ({p_label}) Impostato a:</b>\n\n"
        f"        <i>{r_text}</i>\n\n"
        "🔹 Scegli un'opzione."
    )
