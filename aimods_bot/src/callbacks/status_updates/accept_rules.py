from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ConversationHandler

from aimods_bot.src.core.customcontext import CustomContext


async def new_member_accepted_the_rules(update: Update, context: CustomContext):
    if job := context.job_queue.get_jobs_by_name(f'captcha_failed_{update.effective_user.id}'):
        job[0].schedule_removal()

    if not _check_user_identity(update):
        return None

    await _approve_join_request(context, update.effective_user.id)
    await _send_welcome_message(update, context)

    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _check_user_identity(update: Update) -> bool:
    return str(update.effective_user.id) == update.callback_query.data.split(" ")[1]


async def _approve_join_request(context: CustomContext, user_id: int):
    await context.bot.approve_chat_join_request(
        chat_id=context.pydb.group_chat_id,
        user_id=user_id
    )


async def _send_welcome_message(update: Update, context: CustomContext):
    clean_id = str(context.pydb.group_chat_id).removeprefix("-100")
    clean_url = f"https://t.me/c/{clean_id}/0"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Vai al Gruppo ↗️", url=clean_url)
    ]])

    await update.effective_message.edit_text(
        text=(
            "✅ <b>La tua richiesta è stata approvata</b>\n\n"
            "Lo staff di <i>AiMods</i> ti dà il benvenuto. "
            "Grazie per averci scelto 😃"
        ),
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
