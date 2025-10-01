from typing import Literal, Optional

from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import CategorySetting
from aimods_bot.src.helpers.constants.constants import PLATFORM_DETAILS, CATEGORY_DETAILS, Platform, Category
from aimods_bot.src.helpers.constants.models import PanelConfig, Panel, ButtonItem
from aimods_bot.src.helpers.utils.time_utils import pluralize


async def render_admin_request_section_configure_panel(update: Update, context: CustomContext):
    text = _get_admin_request_section_configure_text()

    keyboard = [[]]
    for pl in PLATFORM_DETAILS:
        pl_item = PLATFORM_DETAILS[pl]
        if len(keyboard[-1]) >= 2:
            keyboard.append([])
        keyboard[-1].append(
            ButtonItem(text=f"{pl_item['icon']} {pl_item['label']}", callback_key=pl)
        )

    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=None)])

    admin_request_section_configure_panel = Panel(
        PanelConfig(
            base_path="admin/manage_requests/manage_sections",
            text=text,
            keyboard=keyboard
        )
    )

    await admin_request_section_configure_panel.render(update=update, context=context)


def _get_header(subheader: Optional[str] = None) -> str:
    header = "⏯️ <b>Gestione Sezioni</b>\n\n"

    if subheader:
        header += subheader + "\n\n"

    header += "▪ Da qui puoi impostare i parametri di apertura e chiusura delle sezioni per le richieste.\n\n"

    return header


def _get_admin_request_section_configure_text():
    text = _get_header()
    text += "🔹 Scegli una piattaforma."

    return text


async def render_admin_request_section_configure_platform_panel(
        update: Update,
        context: CustomContext,
        platform: Platform
):
    text = _get_admin_request_section_configure_platform_text()

    keyboard = [[]]
    for ca in CATEGORY_DETAILS[platform.value]:
        ca_item = CATEGORY_DETAILS[platform.value][ca]
        if len(keyboard[-1]) >= 2:
            keyboard.append([])
        keyboard[-1].append(ButtonItem(text=f"{ca_item['icon']} {ca_item['label']}", callback_key=ca))
    keyboard.append([ButtonItem(text="🔙 Indietro", callback_key=None)])

    admin_request_section_configure_platform_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/manage_sections/{platform.value}",
            text=text,
            keyboard=keyboard
        )
    )

    await admin_request_section_configure_platform_panel.render(update=update, context=context)


def _get_admin_request_section_configure_platform_text():
    text = _get_header()
    text += "🔹 Scegli una categoria."

    return text


async def render_admin_request_section_configure_category_panel(
        update: Update,
        context: CustomContext,
        platform: Platform,
        category: Category
):
    config = getattr(getattr(context.pydb.configuration.settings.request, platform.value), category.value)
    assert isinstance(config, CategorySetting)

    text = _get_admin_request_section_configure_category_text(config=config, platform=platform, category=category)
    toggle_text = f"{'📬 Apri' if not config.toggle else '📪 Chiudi'}"
    toggle_callback = "open" if not config.toggle else "close"

    admin_request_section_configure_category_panel = Panel(
        PanelConfig(
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
    )

    await admin_request_section_configure_category_panel.render(update=update, context=context)


def _get_admin_request_section_configure_category_text(config: CategorySetting, platform: Platform, category: Category):
    ca_item = CATEGORY_DETAILS[platform.value][category.value]

    if config.limit is not None:
        l_text = f"{pluralize(config.limit, 'richiesta', 'richieste')}"
    else:
        l_text = "🆓 <b>Nessun Limite</b>"

    text = _get_header()
    text += (f"      {ca_item['icon']} <b>{ca_item['label']}</b>\n"
             f"          🔸 <u>Stato</u> – {'📬 <i>Aperto</i>' if config.toggle else '📪 <i>Chiuso</i>'}\n"
             f"          🔸 <u>Limite Richieste</u> – <i>{l_text}</i>\n\n"
             "🔹 Scegli un'opzione.")

    return text


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
        action=action
    )

    admin_request_section_toggle_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/manage_sections/{platform.value}/{category.value}/{action}",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="📬 Apri" if opening else "📪 Chiudi", callback_key='yes'),
                    ButtonItem(text="🔙 Indietro", callback_key=None)
                ]
            ]
        )
    )

    await admin_request_section_toggle_panel.render(update=update, context=context)


def _get_admin_request_section_toggle_panel_text(
        context: CustomContext,
        platform: Platform,
        category: Category,
        action: Literal["open", "close"]
):
    opens = action == "open"

    config = getattr(getattr(context.pydb.configuration.settings.request, platform.value), category.value)
    assert isinstance(config, CategorySetting)

    text = _get_header(subheader=f"  → <i>{'📬 Apertura' if opens else '📪 Chiusura'} Manuale</i>")
    text += (f"<blockquote>ℹ <b>Info</b> – Se {'apri' if opens else 'chiudi'} questa sezione, "
             f"gli utenti {'non ' if not opens else ''}potranno formulare altre richieste.</blockquote>\n\n")

    r = len(context.get_active_category_requests(platform=platform, category=category))
    if opens and config.limit is not None and r >= config.limit:
        text += ("<blockquote>⚠️ <b>Attenzione</b> – Hai un numero di richieste attive <b>pari o superiore al limite</b>"
                 f" impostato per questa sezione (<b>{pluralize(r, 'richiesta', 'richieste')} su "
                 f"{config.limit}</b>); se la riapri, il <b>limite verrà automaticamente impostato a "
                 f"0 (nessun limite)</b>.</blockquote>\n\n")

    text += "🔹 <b>Confermi</b>?"

    return text


async def render_admin_request_section_toggled_panel(
        update: Update,
        context: CustomContext,
        platform: Platform,
        category: Category,
        action: Literal["open", "close"]
):
    text = _get_admin_request_section_toggled_text(platform=platform, category=category, action=action)

    admin_request_section_toggled_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/manage_sections/{platform.value}/{category.value}/{action}",
            text=text,
            keyboard=[[
                ButtonItem(text="🔙 Indietro", callback_key=None),
                ButtonItem(text="🏠 Home", callback_key="admin", override_path_generation=True)
            ]]
        )
    )

    await admin_request_section_toggled_panel.render(update=update, context=context)


def _get_admin_request_section_toggled_text(
        platform: Platform,
        category: Category,
        action: Literal["open", "close"]
):
    opening = action == "open"
    pl_label = PLATFORM_DETAILS[platform.value]['label']
    ca_label = CATEGORY_DETAILS[platform.value][category.value]['label']
    text = (f"✅ <b>Sezione {ca_label} ({pl_label}) {'Aperta' if opening else 'Chiusa'}</b>\n\n"
            f"🔹 Scegli un'opzione.")

    return text


async def render_admin_request_section_limit_panel(
        update: Update,
        context: CustomContext,
        platform: Platform,
        category: Category
):
    text = _get_admin_request_section_limit_text(context=context, platform=platform, category=category)

    admin_request_section_limit_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/manage_sections/{platform.value}/{category.value}/limit",
            text=text,
            keyboard=[
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
        )
    )

    await admin_request_section_limit_panel.render(update=update, context=context)


def _get_admin_request_section_limit_text(context: CustomContext, platform: Platform, category: Category):
    text = _get_header(subheader="  → 🗂 <i>Imposta Limite</i>")

    ca_item = CATEGORY_DETAILS[platform.value][category.value]

    config = getattr(getattr(context.pydb.configuration.settings.request, platform.value), category.value)
    assert isinstance(config, CategorySetting)

    if config.limit is not None:
        l_text = f"{pluralize(config.limit, 'richiesta', 'richieste')}"
    else:
        l_text = "🆓 <b>Nessun Limite</b>"

    text += (f"      {ca_item['icon']} <b>{ca_item['label']}</b>\n"
             f"        🔸 <u>Limite Attuale</u> – <i>{l_text}</i>\n\n"
             "<blockquote>ℹ Al raggiungimento di questo limite, questa sezione di richieste verrà chiusa "
             "automaticamente.</blockquote>\n\n"
             "🔹 Scegli un'opzione.")

    return text


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

    admin_request_section_limit_confirm_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/manage_sections/{platform.value}/{category.value}/limit/{limit}",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="✅ Conferma", callback_key="yes"),
                    ButtonItem(text="🔙 Annulla", callback_key=None)
                ]
            ]
        )
    )

    await admin_request_section_limit_confirm_panel.render(update=update, context=context)


def _get_admin_request_section_limit_confirm_text(
        context: CustomContext,
        platform: Platform,
        category: Category,
        limit: int
):
    text = _get_header(subheader="  → 🗂 <i>Imposta Limite</i>")

    ca_item = CATEGORY_DETAILS[platform.value][category.value]

    config = getattr(getattr(context.pydb.configuration.settings.request, platform.value), category.value)
    assert isinstance(config, CategorySetting)

    if limit != 0:
        r_text = f"↪️ {pluralize(limit, 'richiesta', 'richieste')}"
    else:
        r_text = "🆓 Nessun Limite"

    if config.limit is not None:
        l_text = f"{pluralize(config.limit, 'richiesta', 'richieste')}"
    else:
        l_text = "🆓 <b>Nessun Limite</b>"

    warn_text = ("<blockquote>⚠️ <b>Attenzione</b> – Se il limite viene ridotto e il numero di richieste attive "
                 "presenti per questa sezione sono in numero pari o superiore, la sezione verrà automaticamente "
                 "chiusa.</blockquote>\n\n")

    text += (f"      {ca_item['icon']} <b>{ca_item['label']}</b>\n"
             f"            🔸 <u>Limite Attuale</u> – <i>{l_text}</i>\n\n"
             "🔹 Stai <b>modificando il limite di richieste</b> per questa sezione a:\n\n"
             f"            <b>{r_text}</b>\n\n{warn_text if limit and config.limit and limit < config.limit else ''}"
             "🔹 <b>Confermi?</b>")

    return text


async def render_admin_request_section_limit_confirmed_panel(
        update: Update,
        context: CustomContext,
        platform: Platform,
        category: Category,
        limit: int
):
    text = _get_admin_request_section_limit_confirmed_text(platform=platform, category=category, limit=limit)

    admin_request_section_limit_confirmed_panel = Panel(
        PanelConfig(
            base_path=f"admin/manage_requests/manage_sections/{platform.value}/{category.value}/limit",
            text=text,
            keyboard=[
                [
                    ButtonItem(text="🔙 Indietro", callback_key=None),
                    ButtonItem(text="🏠 Home", callback_key="admin", override_path_generation=True)
                ]
            ]
        )
    )

    await admin_request_section_limit_confirmed_panel.render(update=update, context=context)


def _get_admin_request_section_limit_confirmed_text(
        platform: Platform,
        category: Category,
        limit: int
):
    p_label = PLATFORM_DETAILS[platform.value]["label"]
    c_label = CATEGORY_DETAILS[platform.value][category.value]["label"]
    r_text = f"↪️ {pluralize(limit, 'richiesta', 'richieste')}" if limit != 0 else "🆓 Nessun Limite"
    text = (f"✅ <b>Limite Richieste {c_label} ({p_label}) Impostato a:</b>\n\n"
            f"        <i>{r_text}</i>\n\n"
            "🔹 Scegli un'opzione.")
    return text
