import asyncio
import re
from functools import partial
from typing import Optional, TypedDict, Literal, cast, List

from telegram import Update, Message, TextQuote, ReplyParameters
from telegram.constants import ParseMode
from telegram.helpers import effective_message_type

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.media import MEDIA_GROUP_TYPES
from aimods_bot.src.helpers.job_queue import send_action_message_after
from aimods_bot.src.helpers.job_queue import send_temporary_message
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, split_command_argument
from aimods_bot.src.helpers.utils.user_utils import is_admin

log = logger.getChild(__name__)


class MsgDict(TypedDict):
    media_type: Literal["video", "photo", "document"]
    media_id: str
    caption: str
    post_id: int
    thread_id: int


async def echo(update: Update, context: CustomContext, full_command: str):
    """Scrive un messaggio facendo le veci del bot. Gestisce i comandi 'annuncio' e 'echo'."""
    message = update.effective_message

    if message is None:
        raise ValueError("Effective Message must not be None here!")

    if message.media_group_id:
        log.debug("Message has more then one attachment (will be managed consequentially).")
        return

    await safe_delete(update, context)
    reply_parameters=_get_reply_parameters(reply_message=message.reply_to_message)
    text, entities = split_command_argument(message)
    attachments = _get_single_attachment(message)

    if attachments:
        additional_job_data.files = attachments

    await send_action_message_after(
        update=update,
        context=context,
        text=text,
        reply_parameters=reply_parameters,
        thread_id=message.message_thread_id
    )


def _get_reply_parameters(reply_message: Message | None = None, allow_sending_without_reply: bool = True):
    if not reply_message:
        return None

    reply_message_id = reply_message.id
    reply_quote = _get_reply_quote(reply_message.quote)

    return ReplyParameters(
        message_id=reply_message_id,
        allow_sending_without_reply=allow_sending_without_reply,
        quote=reply_quote,
        quote_parse_mode=ParseMode.HTML
    )


def _get_reply_quote(quote: Optional[TextQuote]) -> Optional[str]:
    if not quote:
        return None

    if quote.is_manual:
        return quote.text


def _get_echo_text(message: Message | str):
    """Ritorna il testo senza '[.!/]annuncio'."""

    if isinstance(message, str):
        text = message
    else:
        text = message.caption_html_urled or message.text_html_urled

    if not text:
        return None

    s = text.split(None, 1)
    if s[0].lower().endswith(("annuncio", "announce", "echo")):
        return s[1] if len(s) > 1 else ""
    return text


def _get_single_attachment(message: Message) -> Optional[List]:
    """Ritorna l'allegato del messaggio, se presente. Gestisce solo foto, video e documenti."""

    media_type = effective_message_type(message)
    if not media_type or str(media_type) not in MEDIA_GROUP_TYPES:
        return None
    media_id = message.photo[-1].file_id if media_type == "photo" else message.effective_attachment.file_id
    return [MEDIA_GROUP_TYPES[str(media_type)](media=media_id)]


async def multimedia_echo(update: Update, context: CustomContext):
    job_data = cast(List[MsgDict], context.job.data)
    media_group_sender_id = update.effective_user.id

    echo_element = _check_echo_command_in_group_media(context=context, message_data=job_data)

    if not echo_element:
        log.info("Nessun comando tipo 'echo' presente nel media group.")
        return

    text = _get_echo_text(echo_element["caption"])

    for el in job_data:
        await safe_delete(update=update, context=context, message_id=el["post_id"])
        await asyncio.sleep(0.3)

    if not await is_admin(user_id=media_group_sender_id, context=context):
        await send_temporary_message(
            update=update,
            context=context,
            recipient_id=None,
            text="⛔ Solo gli admin possono usare questo comando."
        )
        return

    media = []
    for msg_dict in job_data:
        media.append(
            MEDIA_GROUP_TYPES[msg_dict["media_type"]](
                media=msg_dict["media_id"]
            )
        )
    if not media:
        return

    additional_job_data = JobData(
        thread_id=echo_element["thread_id"],
        files=media,
        send_as_document=False
    )

    await send_action_message_after(
        update=update,
        context=context,
        text=text,
        additional_job_data=additional_job_data
    )


def _check_echo_command_in_group_media(context: CustomContext, message_data: List[MsgDict]) -> Optional[MsgDict]:
    """
        Controlla la lista di media, verificando la presenza di una descrizione che comincia col comando
        'echo' o 'annuncio'. Se lo trova, ritorna l'elemento della lista che contiene tale descrizione.
    """
    echo_pattern = context.pydb.commands["echo"].pattern
    for el in message_data:
        caption = el["caption"]
        if not caption:
            continue
        s_caption = caption.split(None, 1)
        if re.match(echo_pattern, s_caption[0]):
            return el
    return None


async def handle_media_group(update: Update, context: CustomContext):
    message = update.effective_message
    media_type = effective_message_type(message)
    media_id = (
        message.photo[-1].file_id
        if message.photo
        else message.effective_attachment.file_id
    )
    msg_dict = {
        "media_type": media_type,
        "media_id": media_id,
        "caption": message.caption_html_urled,
        "post_id": message.message_id,
        "thread_id": message.message_thread_id
    }
    jobs = context.job_queue.get_jobs_by_name(str(message.media_group_id))
    if jobs:
        cast(list, jobs[0].data).append(msg_dict)
    else:
        context.job_queue.run_once(
            callback=partial(multimedia_echo, update),
            when=2,
            data=[msg_dict],
            name=str(message.media_group_id)
        )
