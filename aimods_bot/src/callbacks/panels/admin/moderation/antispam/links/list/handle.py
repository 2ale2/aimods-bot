from typing import Literal
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, Message
from telegram.constants import ParseMode

from aimods_bot.src.core.config_accessor import get_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import LIST_DETAILS
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.models import JobData
from aimods_bot.src.helpers.job_queue import send_action_message_after
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import make_temp_file
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, handle_if_not_file

log = logger.getChild("antispam_link_list")

domain_types = {
    "greylist": {"singular": "link", "plural": "link"},
    "default": {"singular": "dominio", "plural": "domini"}
}


async def view_list(update: Update, context: CustomContext, l: str):
    l_item = LIST_DETAILS[l]
    domain_type = domain_types.get(l, domain_types["default"])

    if await _handle_if_list_empty(update=update, context=context, l=l):
        return PCS.ADMIN_CONVERSATION

    l_conf = _get_list(context=context, l=l)
    filename = await make_temp_file(content=l_conf, filename=l.lower())
    if await handle_if_not_file(
        update=update,
        context=context,
        filename=filename,
        callback_data=f"moderation/security_filters/antispam/link/{l}"
    ):
        return PCS.ADMIN_CONVERSATION

    await send_action_message_after(
        update=update,
        context=context,
        text=f"{l_item['icon']} Ecco la lista di {domain_type['plural']} aggiunti alla <b>{l.capitalize()}</b>.",
        additional_job_data=JobData(
            files=filename,
            send_as_document=True,
            delete_after_sending=True,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🚮 Chiudi", callback_data="close")]])
        )
    )

    return PCS.ADMIN_CONVERSATION


async def edit_list(update: Update, context: CustomContext, l: str, action: Literal["add", "remove"]):
    l_item = LIST_DETAILS[l]
    domain_type = domain_types.get(l, domain_types["default"])
    message = update.effective_message
    l_conf = _get_list(context=context, l=l)

    if action == "remove" and await _handle_if_list_empty(update=update, context=context, l=l):
        return PCS.ADMIN_CONVERSATION

    header = _get_text_header(l)

    text = header + f"ℹ {l_item['desc']}\n\n"

    if action == "add":
        text += f"➕ Scrivi i <b>{domain_type['plural']} da aggiungere</b> alla {l.capitalize()}."
    else:  # Remove
        text += "🔍 Ecco gli elementi presenti:\n\n"
        for el in l_conf:
            text += f"     ▪<code>{el}</code>\n"
        text += f"\n➖ Scrivi i <b>{domain_type['plural']} da rimuovere</b> dalla {l.capitalize()}."

    keyboard = [[InlineKeyboardButton(
        text="🔙 Indietro",
        callback_data=f"moderation/security_filters/antispam/links/{l}")
    ]]

    await message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

    context.chat_data['list_info'] = {
        "action": action,
        "message_id": message.id,
        "list": l
    }

    return PCS.EDIT_ANTISPAM_LINK_LIST


async def handle_user_input(update: Update, context: CustomContext):
    await safe_delete(update=update, context=context)

    d = context.chat_data["list_info"]
    l = d['list']
    action = d['action']
    message_id = d['message_id']

    l_conf = _get_list(context=context, l=l)
    domain_type = domain_types.get(l, domain_types["default"])

    uin = update.effective_message
    if not await _validate_input(uin):
        await _send_validation_error(update, context, domain_type)
        return PCS.EDIT_ANTISPAM_LINK_LIST

    links = _extract_links(uin, l)
    if not links:
        await _send_validation_error(update, context, domain_type)
        return PCS.EDIT_ANTISPAM_LINK_LIST

    text = _get_text_header(l=l)
    new_items = _process_links(links, l_conf, action)

    text += _generate_response_message(new_items, domain_type, action, l)

    keyboard = _create_response_keyboard(action, domain_type, l, _get_list(context=context, l=l))

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


async def _send_validation_error(update: Update, context: CustomContext, domain_type: dict):
    """Invia messaggio di errore per validazione fallita"""
    text = f"⚠ Il messaggio non contiene link. Invia uno o più {domain_type['plural']}."
    keyboard = [[InlineKeyboardButton(text="🚮 Chiudi", callback_data="close")]]

    await send_action_message_after(
        update=update,
        context=context,
        text=text,
        additional_job_data=JobData(reply_markup=InlineKeyboardMarkup(keyboard))
    )


async def _validate_input(uin: Message) -> bool:
    return any(x.type in MessageEntity.URL for x in uin.entities)


def _get_list(context: CustomContext, l: str) -> list:
    return get_value(context=context, path=f"moderation.antispam.link.{l}")


def _check_list_empty(context: CustomContext, l: str) -> bool:
    l_conf = _get_list(context=context, l=l)
    return len(l_conf) == 0


async def _handle_if_list_empty(update: Update, context: CustomContext, l: str) -> bool:
    l_item = LIST_DETAILS[l]

    if _check_list_empty(context=context, l=l):
        text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
                f"↦ {l_item['icon']} <i>Blocco Link – {l.capitalize()}</i>\n\n"
                f"0️⃣ <b>La {l.capitalize()} è attualmente vuota</b>.")
        keyboard = [
            [InlineKeyboardButton(text="🔙 Indietro", callback_data=f"moderation/security_filters/antispam/link/{l}")]
        ]

        await update.effective_message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

        return True
    return False


def _get_text_header(l: str) -> str:
    l_item = LIST_DETAILS[l]
    return ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ {l_item['icon']} <i>Blocco Link – {l.capitalize()}</i>\n\n")
