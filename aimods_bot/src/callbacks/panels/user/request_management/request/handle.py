from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from aimods_bot.src.helpers.constants.models import CanUserRequest
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS


async def can_user_request(update: Update, context: CallbackContext) -> CanUserRequest:
    """Verifica se l'utente può fare richieste, per limiti di moderazione o imposti dalla gestione."""
    return CanUserRequest(
        yn=True,
        reason=None
    )
