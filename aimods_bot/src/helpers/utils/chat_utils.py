from typing import Optional

from telegram import ChatFullInfo, ChatPermissions

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("chat_utils")


async def get_chat(context: CustomContext, chat_id: int) -> Optional[ChatFullInfo]:
    try:
        chat = await context.bot.get_chat(chat_id=chat_id)
        return chat
    except Exception as e:
        log.error(f"Impossibile reperire l'entità Chat per l'ID: {chat_id}: {e}")
        return None


async def get_chat_permissions(context: CustomContext, chat_id: int) -> Optional[ChatPermissions]:
    chat = await get_chat(context, chat_id)
    if chat is None:
        log.error(f"Impossibile ottenere i permessi della Chat per l'ID: {chat_id}. Leggi i log.")
        return None
    return chat.permissions
