from typing import Optional, List

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ConversationHandler

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.infra.telegram.utils import safe_delete
from aimods_bot.src.ui.panel import PanelConfig, Panel, ButtonItem
from aimods_bot.src.ui.path_navigation import GlobalAction
from aimods_bot.src.ui.routing import PathBuilder


async def safe_delete_wrapper(update: Update, context: CustomContext):
    """Wrapper per safe_delete usando il messaggio corrente"""
    await safe_delete(update, context, update.effective_message)
    if update.callback_query.data == GlobalAction.CLOSE_MENU:
        return ConversationHandler.END


def chunk_buttons(buttons: list[ButtonItem], size: int = 2) -> list[list[ButtonItem]]:
    """Divide una lista piatta di bottoni in righe della dimensione specificata."""
    return [buttons[i:i + size] for i in range(0, len(buttons), size)]


async def render_error_panel(
        update: Update,
        context: CustomContext,
        text: str,
        chat_id: int | None = None
):
    await context.bot.send_message(
        chat_id=chat_id or update.effective_chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="📫 Chiudi", callback_data=GlobalAction.CLOSE)]]
        )
    )


async def wrong_input_message(
        update: Update,
        context: CustomContext,
        correct_message: str,
        reply_to_message_id: int | None = None
) -> None:
    """Invia un messaggio di errore per input non valido"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"⚠️ {correct_message}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="🗑️ Chiudi", callback_data=GlobalAction.CLOSE)]]
        ),
        reply_to_message_id=reply_to_message_id,
        parse_mode=ParseMode.HTML
    )


async def not_implemented_yet(update: Update, context: CustomContext) -> None:
    """Messaggio per funzionalità non ancora implementate"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⚠️ Funzionalità non ancora implementata.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="🗑️ Chiudi", callback_data=GlobalAction.CLOSE)]]
        )
    )


async def create_and_render_panel(
        update: Update,
        context: CustomContext,
        text: str,
        keyboard: List[List[ButtonItem]],
        message_id: Optional[int] = None,
        user_id: Optional[int] = None,
        send: bool = False
) -> bool | None:
    """
    Crea e renderizza un pannello con configurazione specifica.

    Args:
        update: Update object
        context: CustomContext
        text: Testo del pannello
        keyboard: Layout tastiera
        message_id: ID messaggio da modificare (opzionale)
        user_id: ID utente target (opzionale)
        send: Se True, invia nuovo messaggio invece di modificare
    """
    panel = Panel(
        PanelConfig(text=text, keyboard=keyboard)
    )

    return await panel.render(
        update=update,
        context=context,
        message_id=message_id,
        user_id=user_id,
        send=send
    )


def get_banned_panel() -> Panel:
    """Restituisce il pannello per utenti bannati"""
    return Panel(
        PanelConfig(
            text="❌ Sei stato bannato/a. Non potrai usare il bot.",
            keyboard=[[ButtonItem(text="🗑️ Chiudi", callback_key=GlobalAction.CLOSE)]]
        ),
        send=True
    )


async def render_action_not_permitted_panel(update: Update, context: CustomContext, base_path: PathBuilder) -> None:
    text = ("⛔ <b>Azione Vietata</b>\n\n"
            "🔐 Non hai i permessi per eseguire questa azione.")

    keyboard = [
        [
            ButtonItem(text="🔙 Indietro", callback_key=base_path.back()),
            ButtonItem(text="🏠 Home", callback_key=PathBuilder(base_path.segments[0]))
        ]
    ]

    await create_and_render_panel(
        update=update,
        context=context,
        text=text,
        keyboard=keyboard
    )
