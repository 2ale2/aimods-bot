import pytz
from telegram.ext import ContextTypes, CallbackContext
from telegram import Update

from aimods_bot.src.helpers.conversationStates import *
from aimods_bot.src.helpers.database import *
from aimods_bot.src.helpers import constants


async def new_member_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    ban_list = context.bot_data.get("ban_list", {})
    group_chat_id = context.bot_data.get("group_chat_id")

    # ✅ 1. Se l'utente è bannato in memoria (blacklist)
    if uid in ban_list:
        ban_data = ban_list[uid]
        until_date = ban_data.get("expires_at")
        rome_until_date = until_date.astimezone(pytz.timezone('Europe/Rome')) if until_date else None

        await constants.pyro_instance.ban_chat_member(
            chat_id=group_chat_id,
            user_id=uid,
            until_date=until_date
        )

        await add_to_table(
            table_name="bans",
            content={
                "admin": ban_data["admin"],
                "user_id": uid,
                "reason": ban_data["reason"],
                "expires_at": until_date
            }
        )

        # 📣 Componi messaggio di servizio
        service_text = (
            f"🚫 Utente <b>in blacklist</b> {update.effective_user.name} (<code>{uid}</code>) <b>bannato</b> "
        )
        service_text += (
            f"fino al <b>{rome_until_date.strftime('%d %B %Y')}</b> alle {rome_until_date.strftime('%H:%M')}."
            if rome_until_date else "a <b>tempo indeterminato</b>."
        )
        if ban_data.get("reason"):
            service_text += f"\n<b>Motivo</b>: <i>{ban_data['reason']}</i>."
        service_text += "\n\nℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."

        await job_queue_functions.send_temporary_message(
            update=update,
            context=context,
            text=service_text,
            delay_delete=300
        )
        return ConversationHandler.END

    # ✅ 2. Se l'utente è bannato da database o verifica async
    if await user_is_banned(uid, group_chat_id, context):
        await job_queue_functions.send_temporary_message(
            update=update,
            context=context,
            text="❌ Il tuo ID è stato <b>bannato</b>.\n\nNon puoi unirti al gruppo.",
            delay_delete=10
        )
        return ConversationHandler.END

    # ✅ 3. Cleanup messaggio callback se presente
    if update.callback_query:
        await delete_effective_message(update, context)

    # ✅ 4. Messaggio privato con accettazione regole
    try:
        message = await context.bot.send_message(
            chat_id=uid,
            text=context.bot_data["user_joined_message_text"].format(update.effective_user.full_name),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    text="Ho letto e accetto le regole 🖋",
                    callback_data=f"accept_rules {uid}"
                )]
            ]),
            link_preview_options=telegram.LinkPreviewOptions(is_disabled=True)
        )
    except telegram.error.Forbidden:
        # Utente non ha il bot avviato: opzionale logging
        return ConversationHandler.END

    # ✅ 5. Schedule fallback captcha reminder
    context.job_queue.run_once(
        callback=job_queue_functions.scheduled_edit_message,
        data={
            'chat_id': uid,
            'message_id': message.message_id,
            'text': (
                "⚠️ <b>Non hai completato la verifica</b>.\n\n"
                "Per ricaricare la doppia verifica, puoi premere il tasto sotto."
            ),
            'reply_markup': InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    text="🔄 Ricarica Captcha",
                    callback_data="recreate_captcha"
                )
            ]])
        },
        when=5,
        name=f'captcha_failed_{uid}'
    )

    return RULES_ACCEPTED


async def new_member_rules_agreed(update: Update, context: CallbackContext) -> int:
    if (uid := update.effective_user.id) in context.bot_data["ban_list"]:
        ban_data = context.bot_data["ban_list"][uid]
        if ban_data["expires_at"] is not None:
            rome_until_date = (until_date := ban_data['expires_at']).astimezone(pytz.timezone('Europe/Rome'))
        else:
            until_date = None
            rome_until_date = None
    return NewMemberJoinedForum.RULES_AGREED