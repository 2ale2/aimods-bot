from telegram.ext import ContextTypes


async def is_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int = None) -> bool:
    """
    Verifica se l'utente è un admin del gruppo.
    """
    return str(user_id) in context.bot_data["admins"].keys()


async def user_in_chat(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Verifica se l'utente è attualmente nella chat.
    """
    member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    return member.status not in ("left", "kicked")


async def user_is_banned(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
        Verifica se l'utente è bannato (presente in una lista ban).
    """
    res = await context.bot.get_chat_member(
        user_id=user_id,
        chat_id=chat_id
    )
    ban_list = context.bot_data.get("ban_list", {})
    return res.status == "kicked" or str(user_id) in ban_list
