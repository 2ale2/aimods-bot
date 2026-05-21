import random
from typing import Literal, List, Optional, Dict, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, KeyboardButtonRequestUsers, \
    KeyboardButtonRequestChat, ReplyKeyboardMarkup
from telegram.constants import ParseMode

from aimods_bot.src.core.config_accessor import get_value, set_value
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.models import JobData
from aimods_bot.src.helpers.job_queue import send_action_message_after
from aimods_bot.src.helpers.utils.file_utils import make_temp_file
from aimods_bot.src.helpers.utils.telegram_utils import handle_if_not_file, safe_delete
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS

BASE_TEXT = "📨 <b>Impostazioni Anti-Spam</b>\n\n↦ 💬 <i>Gestione Whitelist</i>"

CategoryType = Literal["user", "group", "channel", "bot"]
ActionType = Literal["add", "remove"]


class WhitelistManager:
    """Gestione centralizzata delle operazioni sulla whitelist"""

    @staticmethod
    def get_whitelist(context: CustomContext, category: CategoryType) -> List[int]:
        """Recupera la whitelist per una categoria"""
        return get_value(context=context, path=f'moderation.antispam.whitelist.{category}') or []

    @staticmethod
    def save_whitelist(context: CustomContext, category: CategoryType, whitelist: List[int]) -> None:
        """Salva la whitelist per una categoria"""
        set_value(context=context, path=f"moderation.antispam.whitelist.{category}", value=whitelist)

    @staticmethod
    def add_to_whitelist(context: CustomContext, category: CategoryType, items: List[int]) -> List[int]:
        """Aggiunge elementi alla whitelist e restituisce quelli effettivamente aggiunti"""
        whitelist = WhitelistManager.get_whitelist(context, category)
        added = [item for item in items if item not in whitelist]

        if added:
            whitelist.extend(added)
            WhitelistManager.save_whitelist(context, category, whitelist)

        return added

    @staticmethod
    def remove_from_whitelist(context: CustomContext, category: CategoryType, items: List[int]) -> List[int]:
        """Rimuove elementi dalla whitelist e restituisce quelli effettivamente rimossi"""
        whitelist = WhitelistManager.get_whitelist(context, category)
        removed = [item for item in items if item in whitelist]

        if removed:
            for item in removed:
                whitelist.remove(item)
            WhitelistManager.save_whitelist(context, category, whitelist)

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
    def build_empty_list_message(category: CategoryType) -> str:
        """Costruisce messaggio per lista vuota"""
        word = CATEGORY_LABELS[category]
        return (MessageBuilder.build_base_text(f"Whitelist Menzione {word}") +
                "0️⃣ <b>La Whitelist è attualmente vuota</b>.")

    @staticmethod
    def build_removal_list_message(category: CategoryType, whitelist: List[int]) -> str:
        """Costruisce messaggio per la rimozione con lista elementi"""
        word = CATEGORY_LABELS[category]
        text = MessageBuilder.build_base_text(f"Rimuovi da Whitelist {word}")

        for item in whitelist:
            text += f"     ▪<code>{item}</code>\n"
        text += "\n➖ Scrivi gli ID da rimuovere dalla Whitelist."

        return text


class KeyboardBuilder:
    """Costruzione centralizzata delle tastiere"""

    @staticmethod
    def build_category_inline_keyboard(base_path: str, back_callback: str) -> InlineKeyboardMarkup:
        """Costruisce tastiera inline per selezione categoria"""
        keyboard = [
            [
                InlineKeyboardButton(text=f"{CATEGORY_EMOJI['user']} {CATEGORY_LABELS['user']}",
                                     callback_data=f"{base_path}user"),
                InlineKeyboardButton(text=f"{CATEGORY_EMOJI['group']} {CATEGORY_LABELS['group']}",
                                     callback_data=f"{base_path}group")
            ],
            [
                InlineKeyboardButton(text=f"{CATEGORY_EMOJI['channel']} {CATEGORY_LABELS['channel']}",
                                     callback_data=f"{base_path}channel"),
                InlineKeyboardButton(text=f"{CATEGORY_EMOJI['bot']} {CATEGORY_LABELS['bot']}",
                                     callback_data=f"{base_path}bot")
            ],
            [InlineKeyboardButton(text="🔙 Indietro", callback_data=back_callback)]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def build_add_keyboard() -> tuple[ReplyKeyboardMarkup, dict]:
        """Costruisce tastiera per aggiunta elementi"""
        rid_mapping = {
            random.randint(100, 200): "user",
            random.randint(201, 300): "group",
            random.randint(301, 400): "channel",
            random.randint(401, 500): "bot"
        }

        rids = list(rid_mapping.keys())
        keyboard = [
            [
                KeyboardButton(text=f"{CATEGORY_EMOJI['user']} {CATEGORY_LABELS['user']}",
                               request_users=KeyboardButtonRequestUsers(request_id=rids[0])),
                KeyboardButton(text=f"{CATEGORY_EMOJI['group']} {CATEGORY_LABELS['group']}",
                               request_chat=KeyboardButtonRequestChat(request_id=rids[1], chat_is_channel=False))
            ],
            [
                KeyboardButton(text=f"{CATEGORY_EMOJI['channel']} {CATEGORY_LABELS['channel']}",
                               request_chat=KeyboardButtonRequestChat(request_id=rids[2], chat_is_channel=True)),
                KeyboardButton(text=f"{CATEGORY_EMOJI['bot']} {CATEGORY_LABELS['bot']}",
                               request_users=KeyboardButtonRequestUsers(request_id=rids[3], user_is_bot=True))
            ],
            [KeyboardButton(text="🔙 Indietro")]
        ]

        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True), rid_mapping


# Funzioni principali refactored
async def view_whitelist(update: Update, context: CustomContext, category: CategoryType, from_category: bool = False):
    """Visualizza la whitelist per una categoria"""
    whitelist = WhitelistManager.get_whitelist(context, category)
    word = CATEGORY_LABELS[category]

    if not whitelist:
        await _send_empty_list_message(update=update, category=category, from_category=from_category)
        return PCS.ADMIN_CONVERSATION

    if not from_category:
        callback_data = "moderation/security_filters/antispam/whitelist/view"
    else:
        callback_data = f"moderation/security_filters/antispam/{category}"

    filename = await make_temp_file(whitelist, filename=f"whitelist_{category}")
    if await handle_if_not_file(
            update=update,
            context=context,
            filename=filename,
            callback_data=callback_data
    ):
        return PCS.ADMIN_CONVERSATION

    await send_action_message_after(
        update=update,
        context=context,
        text=f"📄 Ecco la lista di identificativi aggiunti alla Whitelist per "
             f"{'gli' if category == 'user' else 'i'} {word}.",
        additional_job_data=JobData(
            files=filename,
            send_as_document=True,
            delete_after_sending=True,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🚮 Chiudi", callback_data="close_menu")]])
        )
    )

    return PCS.ADMIN_CONVERSATION


async def edit_whitelist_pre_step(update: Update, context: CustomContext, action: ActionType):
    """Preparazione per aggiunta o rimozione dalla whitelist"""
    sub_text = 'Aggiungi ad una' if action == "add" else 'Rimuovi da una'
    text = MessageBuilder.build_base_text(f"{sub_text} Whitelist")

    if action == "add":
        return await _handle_add_preparation(update, context, text)
    else:
        return await _handle_remove_preparation(update=update, text=text)


async def remove_from_whitelist(update: Update, context: CustomContext, category: CategoryType):
    """Gestisce la rimozione da una categoria specifica"""
    whitelist = WhitelistManager.get_whitelist(context, category)

    if not whitelist:
        await _send_empty_list_message(update, category)
        return PCS.ADMIN_CONVERSATION

    text = MessageBuilder.build_removal_list_message(category, whitelist)

    await update.effective_message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            text="🔙 Indietro",
            callback_data="moderation/security_filters/antispam/whitelist/remove"
        )]]),
        parse_mode=ParseMode.HTML
    )

    context.chat_data["editing_antispam_whitelist"] = {
        "action": "remove",
        "message_id": update.effective_message.id,
        "category": category
    }

    return PCS.REMOVE_ANTISPAM_MENTION_WHITELIST


async def handle_user_input_antispam_whitelist(update: Update, context: CustomContext):
    """Gestisce l'input dell'utente per aggiunta/rimozione"""
    data = context.chat_data.get("editing_antispam_whitelist", {})
    action = data.get("action")
    message_id = data.get("message_id")
    category = data.get("category")

    if not all([action, message_id, category]):
        return PCS.ADMIN_CONVERSATION

    await safe_delete(update=update, context=context, message_id=message_id)
    await safe_delete(update=update, context=context)

    if action == "add":
        return await _handle_add_action(update, context, data)
    else:
        return await _handle_remove_action(update, context, data)


async def _send_empty_list_message(update: Update, category: CategoryType, from_category: bool = False):
    """Invia messaggio per lista vuota"""
    text = MessageBuilder.build_empty_list_message(category)
    if not from_category:
        callback_data = "moderation/security_filters/antispam/whitelist/view"
    else:
        callback_data = f"moderation/security_filters/antispam/{category}"
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
        "action": "add",
        "message_id": message.id,
        "category": rid_mapping
    }

    return PCS.ADD_ANTISPAM_MENTION_WHITELIST


async def _handle_remove_preparation(update: Update, text: str):
    """Gestisce la preparazione per la rimozione"""
    keyboard = KeyboardBuilder.build_category_inline_keyboard(
        "moderation/security_filters/antispam/whitelist/remove/",
        "moderation/security_filters/antispam/whitelist"
    )

    await update.effective_message.edit_text(
        text=text + "🔹 Scegli la categoria da cui rimuovere gli elementi.",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )

    return PCS.ADMIN_CONVERSATION


async def _handle_add_action(update: Update, context: CustomContext, data: Dict[str, Any]):
    """Gestisce l'azione di aggiunta"""
    ureq = update.effective_message.users_shared
    creq = update.effective_message.chat_shared

    if not (ureq or creq):
        return PCS.ADMIN_CONVERSATION

    req_id = ureq.request_id if ureq else creq.request_id
    category = data["category"].get(req_id)

    if not category:
        return PCS.ADMIN_CONVERSATION

    word = CATEGORY_LABELS[category]
    text = MessageBuilder.build_base_text(f"Aggiunta ID Whitelist {word}")

    if ureq:
        user_ids = [user.user_id for user in ureq.users]
        added = WhitelistManager.add_to_whitelist(context, category, user_ids)

        if not added:
            text += "ℹ Tutti gli elementi indicati sono già presenti in Whitelist."
        else:
            text += MessageBuilder.build_success_message("add", [str(eid) for eid in added])
    else:  # creq
        chat_id = creq.chat_id
        added = WhitelistManager.add_to_whitelist(context, category, [chat_id])

        if not added:
            text += f"ℹ L'elemento <code>{chat_id}</code> è già presente in Whitelist."
        else:
            text += f"✅ L'elemento <code>{chat_id}</code> è stato <b>aggiunto alla Whitelist</b>."

    keyboard = _build_post_action_keyboard("add", None)

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

    return PCS.ADMIN_CONVERSATION


async def _handle_remove_action(update: Update, context: CustomContext, data: Dict[str, Any]):
    """Gestisce l'azione di rimozione"""
    category = data.get("category")
    if not category:
        return PCS.ADMIN_CONVERSATION

    word = CATEGORY_LABELS[category]

    input_ids = _parse_ids_from_input(update.effective_message.text)
    removed = WhitelistManager.remove_from_whitelist(context, category, input_ids)

    if not removed:
        text = (MessageBuilder.build_base_text(f"Rimozione ID Whitelist {word}") +
                "ℹ Nessun elemento indicato è presente in Whitelist.")
    else:
        text = (MessageBuilder.build_base_text(f"Rimozione ID Whitelist {word}") +
                MessageBuilder.build_success_message("remove", [str(eid) for eid in removed]))

    keyboard = _build_post_action_keyboard("remove", category)

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
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


def _build_post_action_keyboard(action: ActionType, category: Optional[CategoryType]) -> List[
    List[InlineKeyboardButton]]:
    """Costruisce la tastiera post-azione"""
    if action == "add":
        return [
            [InlineKeyboardButton(
                text="➕ Aggiungi Altri Elementi",
                callback_data="moderation/security_filters/antispam/whitelist/add/"
            )],
            [InlineKeyboardButton(
                text="🔙 Indietro",
                callback_data="moderation/security_filters/antispam/whitelist"
            )]
        ]
    else:  # remove
        return [
            [InlineKeyboardButton(
                text="➖ Rimuovi Altro Elemento",
                callback_data=f"moderation/security_filters/antispam/whitelist/remove/{category}"
            )],
            [InlineKeyboardButton(
                text="🔙 Indietro",
                callback_data="moderation/security_filters/antispam/whitelist"
            )]
        ]


async def _handle_if_list_empty(update: Update, category: str, l: List) -> bool:
    """Funzione di compatibilità - usa _send_empty_list_message"""
    if not l:
        # noinspection PyTypeChecker
        await _send_empty_list_message(update, category)
        return True
    return False

