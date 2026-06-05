import random
from typing import List, Optional, Dict, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, KeyboardButtonRequestUsers, \
    KeyboardButtonRequestChat, ReplyKeyboardMarkup
from telegram.constants import ParseMode

from aimods_bot.src.core.config_accessor import get_value, set_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ChatType
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction, ModerationListsRoute
from aimods_bot.src.helpers.job_queue import send_action_message_after
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.file_utils import make_temp_file
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, chunk_buttons, render_error_panel, \
    create_and_render_panel

BASE_TEXT = "📨 <b>Impostazioni Anti-Spam</b>\n\n↦ 💬 <i>Gestione Whitelist</i>"


class WhitelistManager:
    """Gestione centralizzata delle operazioni sulla whitelist"""

    @staticmethod
    def get_whitelist(context: CustomContext, chat_type: ChatType) -> List[int]:
        """Recupera la whitelist per una categoria"""
        return get_value(context=context, path=f'moderation.antispam.whitelist.{chat_type}') or []

    @staticmethod
    def save_whitelist(context: CustomContext, chat_type: ChatType, whitelist: List[int]) -> None:
        """Salva la whitelist per una categoria"""
        set_value(context=context, path=f"moderation.antispam.whitelist.{chat_type}", value=whitelist)

    @staticmethod
    def add_to_whitelist(context: CustomContext, chat_type: ChatType, items: List[int]) -> List[int]:
        """Aggiunge elementi alla whitelist e restituisce quelli effettivamente aggiunti"""
        whitelist = WhitelistManager.get_whitelist(context, chat_type)
        added = [item for item in items if item not in whitelist]

        if added:
            whitelist.extend(added)
            WhitelistManager.save_whitelist(context=context, chat_type=chat_type, whitelist=whitelist)

        return added

    @staticmethod
    def remove_from_whitelist(context: CustomContext, chat_type: ChatType, items: List[int]) -> List[int]:
        """Rimuove elementi dalla whitelist e restituisce quelli effettivamente rimossi"""
        whitelist = WhitelistManager.get_whitelist(context, chat_type)
        removed = [item for item in items if item in whitelist]

        if removed:
            for item in removed:
                whitelist.remove(item)
            WhitelistManager.save_whitelist(context=context, chat_type=chat_type, whitelist=whitelist)

        return removed


class MessageBuilder:
    """Costruzione centralizzata dei messaggi"""

    @staticmethod
    def build_base_text(subtitle: str) -> str:
        """Costruisce il testo base con sottotitolo"""
        return f"{BASE_TEXT} – <i>{subtitle}</i>\n\n"

    @staticmethod
    def build_success_message(action: str, items: List[str]) -> str:
        """Costruisce messaggio di successo per operazioni"""
        verb = "aggiunti" if action == "add" else "rimossi"
        verb_single = "aggiunto" if action == "add" else "rimosso"
        preposition = "in" if action == "add" else "dalla"

        items_text = ', '.join([f'<code>{item}</code>' for item in items])
        verb_final = verb if len(items) > 1 else verb_single

        return (f"✅ {items_text} "
                f"<b>{verb_final} {preposition} Whitelist</b>.")

    @staticmethod
    def build_empty_list_message(chat_type: ChatType) -> str:
        """Costruisce messaggio per lista vuota"""
        return (MessageBuilder.build_base_text(f"Whitelist Menzione {chat_type.label}") +
                "0️⃣ <b>La Whitelist è attualmente vuota</b>.")

    @staticmethod
    def build_removal_list_message(chat_type: ChatType, whitelist: List[int]) -> str:
        """Costruisce messaggio per la rimozione con lista elementi"""
        text = MessageBuilder.build_base_text(f"Rimuovi da Whitelist {chat_type.label}")

        for item in whitelist:
            text += f"     ▪<code>{item}</code>\n"
        text += "\n➖ Scrivi gli ID da rimuovere dalla Whitelist."

        return text


class KeyboardBuilder:
    """Costruzione centralizzata delle tastiere"""

    @staticmethod
    def build_category_inline_keyboard(base_path: PathBuilder, back_callback: PathBuilder) -> list[list[ButtonItem]]:
        """Costruisce tastiera inline per selezione categoria"""
        buttons = [
            ButtonItem(
                text=f"{chat_type.icon} {chat_type.label}",
                callback_key=base_path.add(chat_type)) for chat_type in ChatType
        ]
        buttons.append(ButtonItem(text="🔙 Indietro", callback_key=back_callback))
        return chunk_buttons(buttons=buttons, size=2)

    @staticmethod
    def build_add_keyboard() -> tuple[ReplyKeyboardMarkup, dict]:
        """Costruisce tastiera per aggiunta elementi"""
        rid_mapping = {
            random.randint(100, 200): ChatType.USER,
            random.randint(201, 300): ChatType.GROUP,
            random.randint(301, 400): ChatType.CHANNEL,
            random.randint(401, 500): ChatType.BOT
        }

        rids = list(rid_mapping.keys())
        keyboard = [
            [
                KeyboardButton(text=f"{ChatType.USER.icon} {ChatType.USER.label}",
                               request_users=KeyboardButtonRequestUsers(request_id=rids[0])),
                KeyboardButton(text=f"{ChatType.GROUP.icon} {ChatType.GROUP.label}",
                               request_chat=KeyboardButtonRequestChat(request_id=rids[1], chat_is_channel=False))
            ],
            [
                KeyboardButton(text=f"{ChatType.CHANNEL.icon} {ChatType.CHANNEL.label}",
                               request_chat=KeyboardButtonRequestChat(request_id=rids[2], chat_is_channel=True)),
                KeyboardButton(text=f"{ChatType.BOT.icon} {ChatType.BOT.label}",
                               request_users=KeyboardButtonRequestUsers(request_id=rids[3], user_is_bot=True))
            ],
            [KeyboardButton(text="🔙 Indietro")]
        ]

        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True), rid_mapping


# Funzioni principali refactored
async def view_whitelist(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        chat_type: ChatType,
        from_category: bool = False
):
    """Visualizza la whitelist per una categoria"""
    whitelist = WhitelistManager.get_whitelist(context=context, chat_type=chat_type)

    if not whitelist:
        await _send_empty_list_message(
            update=update,
            chat_type=chat_type,
            base_path=base_path,
            from_category=from_category
        )
        return PCS.ADMIN_CONVERSATION

    filename = await make_temp_file(whitelist, filename=f"whitelist_{chat_type}")
    if not filename:
        await render_error_panel(
            update=update,
            context=context,
            text="❌ Errore durante la creazione del file di testo. Contatta l'admin."
        )
        return PCS.ADMIN_CONVERSATION

    await send_action_message_after(
        update=update,
        context=context,
        text=f"📄 Ecco la lista di identificativi aggiunti alla Whitelist per "
             f"{chat_type.label_with_article}.",
        files=[str(filename)],
        send_as_document=True,
        delete_after_sending=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🚮 Chiudi", callback_data=GlobalAction.CLOSE)]])
    )

    return PCS.ADMIN_CONVERSATION


async def edit_whitelist_pre_step(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        action: ModerationListsRoute
):
    """Preparazione per aggiunta o rimozione dalla whitelist"""
    if action == ModerationListsRoute.VIEW:
        raise ValueError(f"Whitelist edit action cannot be {action}!")
    sub_text = 'Aggiungi ad una' if action == ModerationListsRoute.ADD else 'Rimuovi da una'
    text = MessageBuilder.build_base_text(f"{sub_text} Whitelist")

    if action == ModerationListsRoute.ADD:
        return await _handle_add_preparation(update=update, context=context, text=text)
    else:
        return await _handle_remove_preparation(update=update, context=context, base_path=base_path, text=text)


async def remove_from_whitelist(update: Update, context: CustomContext, base_path: PathBuilder, chat_type: ChatType):
    """Gestisce la rimozione da una categoria specifica"""
    whitelist = WhitelistManager.get_whitelist(context, chat_type)

    if not whitelist:
        await _send_empty_list_message(update=update, chat_type=chat_type, base_path=base_path)
        return PCS.ADMIN_CONVERSATION

    text = MessageBuilder.build_removal_list_message(chat_type=chat_type, whitelist=whitelist)

    await update.effective_message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            text="🔙 Indietro",
            callback_data=base_path.back()
        )]]),
        parse_mode=ParseMode.HTML
    )

    context.chat_data["editing_antispam_whitelist"] = {
        "action": ModerationListsRoute.REMOVE,
        "message_id": update.effective_message.id,
        "chat_type": chat_type
    }

    return PCS.REMOVE_ANTISPAM_MENTION_WHITELIST


async def handle_user_input_antispam_whitelist(update: Update, context: CustomContext, base_path: PathBuilder):
    """Gestisce l'input dell'utente per aggiunta/rimozione"""
    data = context.chat_data.get("editing_antispam_whitelist", {})
    action = data.get("action")
    message_id = data.get("message_id")
    chat_type = data.get("chat_type")

    if not all([action, message_id, chat_type]):
        return PCS.ADMIN_CONVERSATION

    await safe_delete(update=update, context=context, message_id=message_id)
    await safe_delete(update=update, context=context)

    if action == ModerationListsRoute.REMOVE:
        return await _handle_add_action(update=update, context=context, base_path=base_path, data=data)
    else:
        return await _handle_remove_action(update=update, context=context, base_path=base_path, data=data)


async def _send_empty_list_message(
        update: Update,
        chat_type: ChatType,
        base_path: PathBuilder,
        from_category: bool = False
):
    """Invia messaggio per lista vuota"""
    text = MessageBuilder.build_empty_list_message(chat_type)
    if not from_category:
        callback_data = base_path.back()
    else:
        callback_data = base_path.back(2)

    keyboard = [[InlineKeyboardButton(
        text="🔙 Indietro",
        callback_data=callback_data
    )]]

    await update.effective_message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def _handle_add_preparation(update: Update, context: CustomContext, text: str):
    """Gestisce la preparazione per l'aggiunta"""
    await safe_delete(update=update, context=context)

    keyboard, rid_mapping = KeyboardBuilder.build_add_keyboard()

    message = await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=text + "🔹 <b>Seleziona una categoria, quindi seleziona l'elemento da aggiungere</b>.",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

    context.chat_data["editing_antispam_whitelist"] = {
        "action": ModerationListsRoute.ADD,
        "message_id": message.id,
        "chat_type": rid_mapping
    }

    return PCS.ADD_ANTISPAM_MENTION_WHITELIST


async def _handle_remove_preparation(update: Update, context: CustomContext, base_path: PathBuilder, text: str):
    """Gestisce la preparazione per la rimozione"""
    keyboard = KeyboardBuilder.build_category_inline_keyboard(
        base_path=base_path,
        back_callback=base_path.back()
    )

    await create_and_render_panel(
        update=update,
        context=context,
        text=text + "🔹 Scegli la categoria da cui rimuovere gli elementi.",
        keyboard=keyboard,
        base_path=base_path
    )

    return PCS.ADMIN_CONVERSATION


async def _handle_add_action(update: Update, context: CustomContext, base_path: PathBuilder, data: Dict[str, Any]):
    """Gestisce l'azione di aggiunta"""
    ureq = update.effective_message.users_shared
    creq = update.effective_message.chat_shared

    if not (ureq or creq):
        return PCS.ADMIN_CONVERSATION

    req_id = ureq.request_id if ureq else creq.request_id
    chat_type = data["chat_type"].get(req_id)

    if not chat_type:
        return PCS.ADMIN_CONVERSATION

    text = MessageBuilder.build_base_text(f"Aggiunta ID Whitelist {chat_type.label}")

    if ureq:
        user_ids = [user.user_id for user in ureq.users]
        added = WhitelistManager.add_to_whitelist(context, chat_type, user_ids)

        if not added:
            text += "ℹ Tutti gli elementi indicati sono già presenti in Whitelist."
        else:
            text += MessageBuilder.build_success_message("add", [str(eid) for eid in added])
    else:  # creq
        chat_id = creq.chat_id
        added = WhitelistManager.add_to_whitelist(context, chat_type, [chat_id])

        if not added:
            text += f"ℹ L'elemento <code>{chat_id}</code> è già presente in Whitelist."
        else:
            text += f"✅ L'elemento <code>{chat_id}</code> è stato <b>aggiunto alla Whitelist</b>."

    keyboard = _build_post_action_keyboard(action=ModerationListsRoute.ADD, base_path=base_path, chat_type=None)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=text,
        keyboard=keyboard,
    )

    return PCS.ADMIN_CONVERSATION

# noinspection PyTypeChecker
async def _handle_remove_action(update: Update, context: CustomContext, base_path: PathBuilder, data: Dict[str, Any]):
    """Gestisce l'azione di rimozione"""
    chat_type = data.get("chat_type")
    if not chat_type:
        return PCS.ADMIN_CONVERSATION

    input_ids = _parse_ids_from_input(text=update.effective_message.text)
    removed = WhitelistManager.remove_from_whitelist(context=context, chat_type=chat_type, items=input_ids)

    if not removed:
        text = (MessageBuilder.build_base_text(subtitle=f"Rimozione ID Whitelist {chat_type.label}") +
                "ℹ Nessun elemento indicato è presente in Whitelist.")
    else:
        text = (MessageBuilder.build_base_text(subtitle=f"Rimozione ID Whitelist {chat_type.label}") +
                MessageBuilder.build_success_message(
                    action=ModerationListsRoute.REMOVE,
                    items=[str(eid) for eid in removed])
                )

    keyboard = _build_post_action_keyboard(
        action=ModerationListsRoute.REMOVE,
        chat_type=chat_type,
        base_path=base_path
    )

    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=keyboard,
        base_path=base_path
    )

    return PCS.ADMIN_CONVERSATION


def _parse_ids_from_input(text: str) -> List[int]:
    """Estrae gli ID numerici dal testo di input"""
    if not text:
        return []

    ids = []
    for word in text.split():
        if word.isdigit():
            ids.append(int(word))
    return ids


def _build_post_action_keyboard(
        action: ModerationListsRoute,
        base_path: PathBuilder,
        chat_type: Optional[ChatType]) -> List[List[ButtonItem]]:
    """Costruisce la tastiera post-azione"""
    if action == ModerationListsRoute.ADD:
        return [
            [ButtonItem(
                text="➕ Aggiungi Altri Elementi",
                callback_key=base_path
            )],
            [ButtonItem(
                text="🔙 Indietro",
                callback_key=base_path.back()
            )]
        ]
    elif action == ModerationListsRoute.REMOVE:
        return [
            [ButtonItem(
                text="➖ Rimuovi Altro Elemento",
                callback_key=base_path
            )],
            [ButtonItem(
                text="🔙 Indietro",
                callback_key=base_path.back()
            )]
        ]
    else:
        raise ValueError("Invalid whitelist editing action!")


async def _handle_if_list_empty(update: Update, base_path: PathBuilder, chat_type: str, l: List) -> bool:
    """Funzione di compatibilità - usa _send_empty_list_message"""
    if not l:
        # noinspection PyTypeChecker
        await _send_empty_list_message(update=update, chat_type=chat_type, base_path=base_path)
        return True
    return False
