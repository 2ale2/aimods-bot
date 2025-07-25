from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

from aimods_bot.src.callbacks.panels.admin.moderation.punishment.render import render_punishment_panel
from aimods_bot.src.core.config_accessor import set_value
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.models import JobData
from aimods_bot.src.helpers.job_queue import send_action_message_after
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.utils.time_utils import parse_duration


async def set_punishment_type(context: CallbackContext, setting: str, punishment: str):
    set_value(context=context, path=f"moderation.{setting}.punishment.type", value=punishment)


async def set_punishment_duration(update: Update, context: CallbackContext):
    """
        Gestisce i messaggi per l'impostazione della durata di una punizione,
        in accordo con le impostazioni di moderazione.
    """
    setting = context.chat_data.get('setting_duration')
    if update.callback_query:
        # L'utente ha scelto endless.
        set_value(context=context, path=f"moderation.{setting}.punishment.time", value=1)
    else:
        await safe_delete(update=update, context=context)

        parsed_duration = await parse_duration(update.effective_message.text)
        if not parsed_duration:
            await send_action_message_after(
                update=update,
                context=context,
                text="⚠️ La sintassi non è corretta: non usare segni di punteggiatura o parole non necessarie.\n\n"
                     "<b>Esempi</b>\n\t"
                     "<code>3 giorni 4 ore 32 minuti 10 secondi</code>\n\t"
                     "<code>1 giorno 2 minuti 32 ore</code>\n\t"
                     "<code>4 ore 1 giorno 2 ore 1 minuto</code>",
                additional_job_data=JobData(
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="🚮 Chiudi", callback_data="close")]])
                )
            )

            return PCS.SET_PUNISHMENT_DURATION
        else:
            set_value(context=context, path=f"moderation.{setting}.punishment.time", value=parsed_duration.total_seconds())

    await render_punishment_panel(update=update, context=context, setting=setting)
    return PCS.ADMIN_CONVERSATION
