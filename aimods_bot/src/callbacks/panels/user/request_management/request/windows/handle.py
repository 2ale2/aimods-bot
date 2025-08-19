import copy
from typing import Dict, Any, Optional, Literal

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, ContextTypes

from aimods_bot.src.callbacks.panels.user.request_management.request.route import user_request_route
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, edit_message_safely
from aimods_bot.src.helpers.constants.conversation_states import RequestConversationState as RCS
from aimods_bot.src.helpers.constants.constants import PLATFORM_ICONS, WINDOWS_CATEGORY_ICONS
from aimods_bot.src.helpers.constants.models import RequestStatuses as RS


class RequestDataManager:
    """Gestisce i dati della richiesta in modo centralizzato"""

    @staticmethod
    def initialize_request(
            context: CallbackContext,
            platform: Literal["android", "ios", "windows", "macos"],
            adobe: bool = False,
            game: bool = False,
            daw: bool = False
    ) -> None:
        """Inizializza una nuova richiesta nel context"""
        context.chat_data["new_request"] = {
            "editing": None,
            "platform": platform,
            "name": None,
            "link": None,
            "version": None,
            "functionalities": None,
            "steamtools": None,
            "adobe": adobe,
            "game": game,
            "daw": daw
        }

    @staticmethod
    async def request_detail(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            detail: Literal["name", "link", "version", "functionalities", "steamtools"],
            back_data: str
    ):
        request_data = RequestDataManager.get_request_data(context)
        platform = request_data["platform"]
        game = request_data["game"]
        text = MessageBuilder.build_request_summary(request_data=request_data)
        link_steamtools = "https://t.me/c/1523566735/13066"

        if platform in ("android", "ios"):
            item_text = "dell'app"
        elif game:
            item_text = "del gioco"
        else:
            item_text = "del software"

        match detail:
            case "name":
                text += f"\n🔹 Indica il <b>nome {item_text}</b> che vorresti richiedere."
            case "link":
                text += f"\n🔹 Indica il <b>link {item_text}</b> che vorresti richiedere."
            case "version":
                text += f"\n🔹 Indica la <b>versione {item_text}</b> che vorresti richiedere."
            case "functionalities":
                text += f"\n🔹 Indica le <b>funzionalità {item_text}</b> che vorresti sbloccare."
            case "steamtools":
                text += f"\n🔹 Accetteresti anche i file <a href=\"{link_steamtools}\">Steam Tools</a>?"

        keyboard = KeyboardBuilder.get_back_keyboard(
            callback_data=back_data,
            steamtools_keyboard=True if detail == "steamtools" else False
        )

        await edit_message_safely(
            context=context,
            message_id=context.chat_data["bot_message_id"],
            chat_id=update.effective_message.chat_id,
            text=text,
            keyboard=keyboard
        )

    @staticmethod
    async def request_detail_to_edit(
            update: Update,
            context: CallbackContext
    ):
        await update.callback_query.answer()
        detail = update.callback_query.data.split("_")[1]
        request_data = RequestDataManager.get_request_data(context)
        platform = request_data["platform"]
        game = request_data["game"]

        RequestDataManager.update_field(context, "editing", detail)

        if platform in ("android", "ios"):
            item_text = "dell'app"
        elif game:
            item_text = "del gioco"
        else:
            item_text = "del software"

        field_messages = {
            "name": f"🔹 Indica il <b>nome {item_text}</b> che vorresti richiedere.",
            "link": f"🔹 Indica il <b>link {item_text}</b> che vorresti richiedere.",
            "version": f"🔹 Indica la <b>versione {item_text}</b> che vorresti richiedere.",
            "functionalities": f"🔹 Indica le <b>funzionalità {item_text}</b> che vorresti sbloccare."
        }

        return_states = {
            "name": RCS.EDIT_NAME,
            "link": RCS.EDIT_LINK,
            "version": RCS.EDIT_VERSION,
            "functionalities": RCS.EDIT_FUNCTIONALITIES
        }

        text = MessageBuilder.build_request_summary(
            request_data=request_data,
            editing_field=detail
        )
        text += f"\n{field_messages['detail']}"

        keyboard = KeyboardBuilder.get_back_keyboard("no_edit")

        await edit_message_safely(
            context=context,
            message_id=context.chat_data["bot_message_id"],
            chat_id=update.effective_chat.id,
            text=text,
            keyboard=keyboard)

        return return_states[detail]

    @staticmethod
    def get_request_data(context: CallbackContext) -> Dict[str, Any]:
        """Ottiene i dati della richiesta corrente"""
        return context.chat_data["new_request"]

    @staticmethod
    def update_field(context: CallbackContext, field: str, value: Any) -> None:
        """Aggiorna un campo specifico della richiesta"""
        context.chat_data["new_request"][field] = value

    @staticmethod
    async def confirm_request(
            update: Update,
            context: CallbackContext,
            platform: Literal["android", "ios", "windows", "macos"]
    ):
        """Conferma e salva la richiesta nel database"""
        uid = update.effective_user.id
        request_data = RequestDataManager.get_request_data(context)

        request_for_db = copy.deepcopy(request_data)
        request_for_db.pop("editing", None)

        query = """
                INSERT INTO requests (id, platform, content, user_id, status, issued_at)
                VALUES (DEFAULT, 'android', $1, $2, DEFAULT, DEFAULT)
                RETURNING id \
                """

        result = await fetch_query(
            query=query,
            params=[str(request_for_db).replace("'", "\""), uid]
        )

        if not result:
            raise Exception("Errore durante l'inserimento della richiesta")

        inserted_id = dict(result[0])["id"]

        request_for_db.update({
            "status": RS.PENDING,
            "id": inserted_id
        })

        context.user_data["requests"][platform].append(request_for_db)

    @staticmethod
    def cleanup_request(context: CallbackContext) -> None:
        """Pulisce i dati della richiesta dal context"""
        context.chat_data.pop("new_request", None)
        context.chat_data.pop("bot_message_id", None)


class KeyboardBuilder:
    """Costruisce keyboard per le diverse fasi"""

    @staticmethod
    def get_back_keyboard(callback_data: str, steamtools_keyboard: bool = False) -> InlineKeyboardMarkup:
        """Keyboard semplice con solo tasto indietro, oppure la tastiera completa nel caso dei giochi"""
        keyboard = [[
            InlineKeyboardButton(text="🔙 Indietro", callback_data=callback_data)
        ]]
        if steamtools_keyboard:
            keyboard.insert(0, [
                InlineKeyboardButton(text="🟢 Sì", callback_data="steamtools_yes"),
                InlineKeyboardButton(text="🔴 No", callback_data="steamtools_no"),
            ])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_review_keyboard(game: bool = False, daw: bool = False, adobe: bool = False) -> InlineKeyboardMarkup:
        """Keyboard per la review finale della richiesta"""
        keyboard = [[InlineKeyboardButton(text="1️⃣ Nome", callback_data="edit_name")]]
        if adobe:
            keyboard.insert(1, [
                InlineKeyboardButton(text="2️⃣ Versione", callback_data="edit_version"),
                InlineKeyboardButton(text="3️⃣ Funzionalità", callback_data="edit_functionalities")
            ])
            keyboard.insert(2, [
                InlineKeyboardButton(text="✅ Conferma", callback_data="confirm_request"),
                InlineKeyboardButton(text="❌ Annulla", callback_data="back_main")
            ])
        else:
            keyboard[0].insert(1, InlineKeyboardButton(text="2️⃣ Link", callback_data="edit_link"))
            keyboard.insert(1, [InlineKeyboardButton(text="3️⃣ Versione", callback_data="edit_version")])
            if not daw:
                keyboard[1].insert(1, InlineKeyboardButton(text="4️⃣ Funzionalità", callback_data="edit_functionalities"))
            if game:
                keyboard.insert(2, [InlineKeyboardButton(text="5️⃣ SteamTools", callback_data="edit_steamtools")])
            keyboard.insert(3, [
                InlineKeyboardButton(text="✅ Conferma", callback_data="confirm_request"),
                InlineKeyboardButton(text="❌ Annulla", callback_data="back_main")
            ])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_confirmation_keyboard() -> InlineKeyboardMarkup:
        """Keyboard per la conferma finale"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(text="♟ Gestisci Richieste", callback_data="users/manage_requests"),
                InlineKeyboardButton(text="🔙 Indietro", callback_data="users")
            ]
        ])


class MessageBuilder:
    """Costruisce messaggi per le diverse fasi della conversazione"""

    @staticmethod
    def build_request_summary(
            request_data: Dict[str, Any],
            editing_field: Optional[str] = None
    ) -> str:
        """Costruisce il riepilogo della richiesta con evidenziazione del campo in editing"""
        platform_to_word = {
            "android": "Android",
            "windows": "Windows",
            "ios": "iOS",
            "macos": "MacOS"
        }

        game = request_data["game"]
        adobe = request_data["adobe"]
        daw = request_data["daw"]
        platform = request_data["platform"]

        name = request_data.get("name", "")
        link = link_display = None
        functionalities = functionalities_display = None
        steamtools = steamtools_display = None

        if not adobe:
            link = request_data.get("link", "")
            link_display = f"<i><b>Editing...</b></i>" if editing_field == "link" else f"🔗 <i><a href='{link}'>Link</a></i>"
        version = request_data.get("version", "")
        if not daw:
            functionalities = request_data.get("functionalities", "")
            functionalities_display = f"<i><b>Editing...</b></i>" if editing_field == "functionalities" else f"<i>{functionalities}</i>"
        if game:
            steamtools = request_data.get("steamtools", "")
            steamtools_display = f"<i>{'Sì' if steamtools else 'No'}</i>"

        # Formatta i campi con evidenziazione se in editing
        name_display = f"<i><b>Editing...</b></i>" if editing_field == "name" else f"<i>{name}</i>"
        version_display = f"<i><b>Editing...</b></i>" if editing_field == "version" else f"<code>{version}</code>"

        if platform != "windows":
            summary = f"{PLATFORM_ICONS[platform]} <b>Nuova Richiesta – {platform_to_word[platform]}</b>\n"
        else:
            if game:
                summary = f"{WINDOWS_CATEGORY_ICONS["game"]} <b>Nuova Richiesta – Gioco</b>\n"
            elif daw:
                summary = f"{WINDOWS_CATEGORY_ICONS["daw"]} <b>Nuova Richiesta – DAW</b>\n"
            elif adobe:
                summary = f"{WINDOWS_CATEGORY_ICONS["adobe"]} <b>Nuova Richiesta – Adobe</b>\n"
            else: # altro software
                summary = f"{WINDOWS_CATEGORY_ICONS["software"]} <b>Nuova Richiesta – Software</b>\n"

        if name:
            summary += f"\n      🔸 <u>Nome</u> – {name_display}\n"
        if link:
            summary += f"      🔸 <u>Link</u> – {link_display}\n"
        if version:
            summary += f"      🔸 <u>Versione</u> – {version_display}\n"
        if functionalities:
            summary += f"      🔸 <u>Funzionalità</u> – {functionalities_display}\n"
        if steamtools:
            summary += f"      🔸 <u>Steam Tools</u> – {steamtools_display}\n"

        return summary

    
class InputHandler:
    """Gestisce l'input utente delle richieste."""
    @staticmethod
    async def handle_input(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE, 
            detail: Literal["name", "link", "version", "functionalities", "steamtools"]
    ):
        if not update.callback_query:
            await safe_delete(update, context)
        match detail:
            case "link":
                entity = update.effective_message.entities[0]
                data = update.effective_message.text[entity.offset:entity.offset + entity.length]
            case "steamtools":
                data = True if update.callback_query.data == "steamtools_yes" else False
            case _:
                data = update.effective_message.text
                
        RequestDataManager.update_field(context=context, field=detail, value=data)


async def handle_back_to_main(update: Update, context: CallbackContext):
    """Gestisce il ritorno al menu principale"""
    await user_request_route(update=update, context=context, path=[])
    return RCS.MAIN_BACKER
