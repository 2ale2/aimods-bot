import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Update
from telegram.ext import ConversationHandler, ContextTypes

import aimods_bot.src.helpers.constants.constants as constants
from aimods_bot.src.core.logger import log_join, log_ban
from aimods_bot.src.helpers.constants.models import JobData, ScheduledJobData
from aimods_bot.src.helpers.database import add_to_table
from aimods_bot.src.helpers.job_queue import send_temporary_message, scheduled_edit_message
from aimods_bot.src.helpers.utils.user_utils import user_is_banned
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete

from aimods_bot.src.helpers.constants.conversation_states.new_user import NewUserState

TIMEOUT_SECONDS = 300


# main function (callback)
async def new_member_joined_forum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await log_join(update, context)
    uid = update.effective_user.id

    await _handle_if_blacklisted(update, context, uid)

    if await _handle_if_banned(update, context, uid):
        return ConversationHandler.END

    await log_join(update, context)

    await _send_rules_and_schedule_expiry(update, context, uid)
    return NewUserState.WAITING_RULES_ACCEPTANCE


async def _handle_if_blacklisted(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int) -> bool:
    if uid not in context.bot_data.get("ban_list", {}):
        return False

    ban_data = context.bot_data["ban_list"].pop(uid)
    until_date = ban_data["expires_at"]
    rome_until = until_date.astimezone(pytz.timezone('Europe/Rome')) if until_date else None

    await constants.pyro_instance.ban_chat_member(
        chat_id=context.bot_data["group_chat_id"],
        user_id=uid,
        until_date=until_date
    )

    await add_to_table("bans", {
        "admin": ban_data["admin"],
        "user_id": uid,
        "reason": ban_data["reason"],
        "expires_at": until_date
    })

    text = f"🚫 Utente <b>in blacklist</b> {update.effective_user.name} (<code>{uid}</code>) <b>bannato</b> "
    if rome_until:
        text += f"fino al <b>{rome_until.strftime('%d %B %Y')}</b> alle {rome_until.strftime('%H:%M')}."
    else:
        text += "a <b>tempo indeterminato</b>."

    if reason := ban_data["reason"]:
        text += f"\n<b>Motivo</b>: <i>{reason}</i>."

    text += "\n\nℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."

    await log_ban(
        update=update,
        context=context,
        admin_id=ban_data["admin"],
        user_id=uid,
        until=rome_until, reason="Blacklistato")

    await send_temporary_message(
        update=update,
        context=context,
        text=text,
        recipient_id=context.bot_data["group_chat_id"],
        delay_delete=300
    )

    return True


async def _handle_if_banned(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int) -> bool:
    is_banned = await user_is_banned(
        user_id=uid,
        context=context
    )
    if is_banned:
        await send_temporary_message(
            update=update,
            context=context,
            recipient_id=None,
            text="❌ Il tuo ID è stato <b>bannato</b>.\n\nNon puoi unirti al gruppo.",
            delay_delete=10
        )
        return True
    return False


async def _send_rules_and_schedule_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    if update.callback_query:
        await safe_delete(update, context)

    rules_text = context.bot_data["user_joined_message_text"].format(update.effective_user.full_name)
    confirm_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Ho letto e accetto le regole 🖋", callback_data=f"accept_rules {uid}")]
    ])

    message = await context.bot.send_message(
        chat_id=uid,
        text=rules_text,
        parse_mode="HTML",
        reply_markup=confirm_keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

    # timeout se non clicca entro TIMEOUT_SECONDS secondi
    timeout_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Ricarica Captcha", callback_data="recreate_captcha")]
    ])

    context.job_queue.run_once(
        callback=scheduled_edit_message,
        data=ScheduledJobData(
            chat_id=uid,
            text='⚠️ <b>Non hai completato la verifica</b>.\n\n'
                 'Per ricaricare la doppia verifica, puoi premere il tasto sotto.',
            additional_data=JobData(
                reply_markup=timeout_keyboard,
                message_id=message.message_id
            )
        ),
        when=TIMEOUT_SECONDS,
        name=f'captcha_failed_{uid}'
    )
