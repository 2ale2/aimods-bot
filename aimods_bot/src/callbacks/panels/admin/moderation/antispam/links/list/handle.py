from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, Message

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
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.file_utils import make_temp_file
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, render_error_panel, create_and_render_panel

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
        files=[str(filename)],
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


# noinspection PyTypeChecker
async def handle_user_input(update: Update, context: CustomContext, base_path: PathBuilder):
    await safe_delete(update=update, context=context)

    # TODO: da tipizzare
    d = context.chat_data["list_info"]
    list_type = d['list']
    action = d['action']
    message_id = d['message_id']

    l_conf = _get_list(context=context, list_type=list_type)

    uin = update.effective_message
    if not await _validate_input(uin=uin):
        await _send_validation_error(update=update, context=context, list_type=list_type)
        return PCS.EDIT_ANTISPAM_LINK_LIST

    links = _extract_links(message=uin, list_type=list_type)
    if not links:
        await _send_validation_error(update=update, context=context, list_type=list_type)
        return PCS.EDIT_ANTISPAM_LINK_LIST

    text = _get_text_header(list_type=list_type)
    new_items = _process_links(links=links, l_conf=l_conf, action=action)

    text += _generate_response_message(new_items=new_items, action=action, list_type=list_type)

    keyboard = _create_response_keyboard(
        base_path=base_path,
        action=action,
        list_type=list_type,
        l_conf=_get_list(context=context, list_type=list_type)
    )

    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=keyboard,
        base_path=base_path,
        message_id=message_id
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


def _generate_response_message(new_items: list, action: ModerationListsRoute, list_type: ModerationList):
    """Genera il messaggio di risposta basato sui risultati"""
    if len(new_items) == 0:
        if action == ModerationListsRoute.ADD:
            return (f"❕ Tutti i {list_type.item_label_plural} indicati "
                    f"sono <b>già presenti</b> nella {list_type.value.capitalize()}.")
        else:  # ModerationListsRoute.REMOVE
            return (f"❕ Tutti i {list_type.item_label_plural} indicati "
                    f"<b>non sono presenti</b> nella {list_type.value.capitalize()}.")

    action_text = "aggiunto" if action == ModerationListsRoute.ADD else "rimosso"
    action_text_plural = "aggiunti" if action == ModerationListsRoute.ADD else "rimossi"

    if len(new_items) == 1:
        return (f"✅ {list_type.item_label_singular.capitalize()} "
                f"<code>{new_items[0]}</code> <b>{action_text} correttamente</b>.")
    else:
        items_formatted = ', '.join(f'<code>{item}</code>' for item in new_items)
        return (f"✅ {list_type.item_label_plural.capitalize()} {items_formatted} "
                f"<b>{action_text_plural} correttamente</b>.")


def _create_response_keyboard(
        base_path: PathBuilder,
        action: ModerationListsRoute,
        list_type: ModerationList,
        l_conf: list[str]
):
    """Crea la keyboard per la risposta"""
    keyboard = [[ButtonItem(text="🔙 Indietro", callback_key=base_path.back(2))]]

    if len(l_conf) != 0:
        button_text = (f"{'➖ Rimuovi Altro' if action == ModerationListsRoute.REMOVE else '➕ Aggiungi Altro'} "
                       f"{list_type.item_label_singular}")
        keyboard.insert(0, [ButtonItem(
            text=button_text,
            callback_key=base_path.back()
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


def _check_list_empty(context: CustomContext, list_type: ModerationList) -> bool:
    l_conf = _get_list(context=context, list_type=list_type)
    return not len(l_conf)


def _get_text_header(list_type: ModerationList) -> str:
    return ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
            f"↦ {list_type.icon} <i>Blocco Link – {list_type.value.capitalize()}</i>\n\n")
