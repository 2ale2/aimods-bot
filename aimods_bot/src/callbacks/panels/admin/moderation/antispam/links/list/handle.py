from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, Message
from telegram.constants import ParseMode

from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.render import \
    render_antispam_edit_link_list_panel
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.render import render_empty_list_panel
from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ModerationList
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction, ModerationListsRoute
from aimods_bot.src.helpers.job_queue import send_action_message_after
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.utils.file_utils import make_temp_file
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, render_error_panel

log = logger.getChild(__name__)


async def view_list(update: Update, context: CustomContext, base_path: PathBuilder, list_type: ModerationList):
    if _check_list_empty(context=context, list_type=list_type):
        await render_empty_list_panel(
            update=update,
            context=context,
            base_path=base_path,
            list_type=list_type
        )
        return PCS.ADMIN_CONVERSATION

    l_conf = _get_list(context=context, list_type=list_type)
    filename = await make_temp_file(content=l_conf, filename=list_type.lower())
    if not filename:
        await render_error_panel(
            update=update,
            context=context,
            text="❌ Errore durante la creazione del file di testo. Contatta l'admin."
        )
        return PCS.ADMIN_CONVERSATION

    text = f"{list_type} Ecco la lista di {list_type.item_label_plural} aggiunti alla <b>{list_type.capitalize()}</b>."

    await send_action_message_after(
        update=update,
        context=context,
        text=text,
        files=filename,
        send_as_document=True,
        delete_after_sending=True,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="🚮 Chiudi", callback_data=GlobalAction.CLOSE_MENU)]]
        )
    )

    return PCS.ADMIN_CONVERSATION


# TODO: da rivedere la gestione totale della modifica delle liste
async def edit_list(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        list_type: ModerationList,
        action: ModerationListsRoute
):
    message = update.effective_message
    l_conf = _get_list(context=context, list_type=list_type)
    text = _get_text_header(list_type) + f"ℹ {list_type.description}\n\n"

    if action == ModerationListsRoute.REMOVE:
        if _check_list_empty(context=context, list_type=list_type):
            await render_empty_list_panel(
                update=update,
                context=context,
                base_path=base_path,
                list_type=list_type
            )
            return PCS.ADMIN_CONVERSATION

        text += "🔍 Ecco gli elementi presenti:\n\n"
        for el in l_conf:
            text += f"     ▪<code>{el}</code>\n"
        text += f"\n🔸 Scrivi i <b>{list_type.item_label_plural} da rimuovere</b> dalla {list_type.value.capitalize()}."
    elif action == ModerationListsRoute.ADD:
        text += f"➕ Scrivi i <b>{list_type.item_label_plural} da aggiungere</b> alla {list_type.value.capitalize()}."
    else:
        raise ValueError(f"Invalid list action: {action}!")

    await render_antispam_edit_link_list_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text
    )

    # TODO: da tipizzare
    context.chat_data['list_info'] = {
        "action": action,
        "message_id": message.id,
        "list": list_type
    }

    return PCS.EDIT_ANTISPAM_LINK_LIST


async def handle_user_input(update: Update, context: CustomContext):
    await safe_delete(update=update, context=context)

    # TODO: da tipizzare
    d = context.chat_data["list_info"]
    list_type = d['list']
    action = d['action']
    message_id = d['message_id']

    l_conf = _get_list(context=context, list_type=list_type)

    uin = update.effective_message
    if not await _validate_input(uin):
        await _send_validation_error(update=update, context=context, list_type=list_type)
        return PCS.EDIT_ANTISPAM_LINK_LIST

    links = _extract_links(uin, l)
    if not links:
        await _send_validation_error(update, context, domain_type)
        return PCS.EDIT_ANTISPAM_LINK_LIST

    text = _get_text_header(list_type=l)
    new_items = _process_links(links, l_conf, action)

    text += _generate_response_message(new_items, domain_type, action, l)

    keyboard = _create_response_keyboard(action, domain_type, l, _get_list(context=context, list_type=l))

    await context.bot.edit_message_text(
        message_id=message_id,
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

    try:
        del context.chat_data["list_info"]
    except KeyError:
        pass

    return PCS.ADMIN_CONVERSATION


def _extract_links(message: Message, list_type: str) -> list[str]:
    """Estrae e processa i link dal messaggio"""
    links = []

    if not message.entities:
        return links

    for entity in message.entities:
        if entity.type != MessageEntity.URL:
            continue

        link = message.text[entity.offset:entity.offset + entity.length]

        if list_type == "greylist":
            links.append(link)
        else:
            parsed = urlparse(link)
            domain = (parsed.netloc or parsed.path.split("/")[0]).removeprefix("www.")
            links.append(domain)

    return links


def _process_links(links: list, l_conf: list, action: str) -> list:
    """Processa i link basandosi sull'azione (add/remove)"""
    new_items = []

    if action == 'add':
        for link in links:
            if link not in l_conf:
                new_items.append(link)
                l_conf.append(link)
    else:  # remove
        for link in links:
            if link in l_conf:
                new_items.append(link)
                l_conf.remove(link)

    return new_items


def _generate_response_message(new_items: list, domain_type: dict, action: str, list_name: str):
    """Genera il messaggio di risposta basato sui risultati"""
    if len(new_items) == 0:
        if action == 'add':
            return f"❕ Tutti i {domain_type['plural']} indicati sono <b>già presenti</b> nella {list_name.capitalize()}."
        else:
            return f"❕ Tutti i {domain_type['plural']} indicati <b>non sono presenti</b> nella {list_name.capitalize()}."

    action_text = "aggiunto" if action == 'add' else "rimosso"
    action_text_plural = "aggiunti" if action == 'add' else "rimossi"

    if len(new_items) == 1:
        return f"✅ {domain_type['singular'].capitalize()} <code>{new_items[0]}</code> <b>{action_text} correttamente</b>."
    else:
        items_formatted = ', '.join(f'<code>{item}</code>' for item in new_items)
        return f"✅ {domain_type['plural'].capitalize()} {items_formatted} <b>{action_text_plural} correttamente</b>."


def _create_response_keyboard(action: str, domain_type: dict, list_name: str, l_conf: list[str]):
    """Crea la keyboard per la risposta"""

    keyboard = [
        [InlineKeyboardButton(
            text="🔙 Indietro",
            callback_data=f"moderation/security_filters/antispam/link/{list_name}"
        )]
    ]

    if len(l_conf) != 0:
        button_text = f"{'➖ Rimuovi Altro' if action == 'remove' else '➕ Aggiungi Altro'} {domain_type['singular']}"
        keyboard.insert(0, [InlineKeyboardButton(
            text=button_text,
            callback_data=f"moderation/security_filters/antispam/link/{list_name}/{action}"
        )])

    return keyboard


async def _send_validation_error(update: Update, context: CustomContext, list_type: ModerationList):
    text = f"⚠ Il messaggio non contiene link. Invia uno o più {list_type.item_label_plural}."
    keyboard = [[InlineKeyboardButton(text="🚮 Chiudi", callback_data=GlobalAction.CLOSE)]]

    await send_action_message_after(
        update=update,
        context=context,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _validate_input(uin: Message) -> bool:
    return any(x.type in MessageEntity.URL for x in uin.entities)


def _get_list(context: CustomContext, list_type: ModerationList) -> list:
    return get_value(context=context, path=f"moderation.antispam.link.{list_type.value}")


def _check_list_empty(context: CustomContext, list_type: str) -> bool:
    l_conf = _get_list(context=context, list_type=list_type)
    return not len(l_conf)


def _get_text_header(list_type: ModerationList) -> str:
    return ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ {list_type.icon} <i>Blocco Link – {list_type.value.capitalize()}</i>\n\n")
