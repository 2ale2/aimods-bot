from typing import get_args

from telegram import Update
from aimods_bot.src.core.customcontext import CustomContext, RequestWizardSession
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, wrong_input_message


async def request_wizard_input_main_handler(update: Update, context: CustomContext):
    wizard = context.pydc.persistent.active_request_wizard
    if not wizard:
        raise ValueError("No wizard to process!")

    requesting_field = wizard.requesting
    if not requesting_field:
        if not update.callback_query:
            # l'utente ha scritto qualcosa ma doveva premere un tasto
            pass

    if update.message:
        await safe_delete(update=update, context=context, message_id=update.message.message_id)
        if user_input := update.message.text:
            is_input_type_correct = _check_correct_input_type(wizard, type(user_input))
        else:
            await wrong_input_message(update=update, context=context, correct_format="del testo senza allegati")
            return PCS.USER_REQUEST_WIZARD_SESSION


def _check_correct_input_type(wizard: RequestWizardSession, t: type) -> True | type | None:
    requesting_field = wizard.requesting
    if not requesting_field:
        return None
    field_type = wizard.draft.model_fields[requesting_field].annotation
    return ((field_type is t) or (t in get_args(field_type))) or field_type
