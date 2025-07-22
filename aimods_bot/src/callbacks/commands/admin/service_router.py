import asyncio
from functools import partial
from typing import TypedDict, Literal, cast, List

from telegram import Update, InputMediaAudio, InputMediaDocument, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
from telegram.helpers import effective_message_type
from aimods_bot.src.callbacks.commands.admin.echo import echo
from aimods_bot.src.helpers.utils.alerts import send_private_alert
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.utils.user_utils import is_admin
from aimods_bot.src.helpers.job_queue import send_temporary_message
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("service_router")

action_map = {
    "annuncio": echo,
    "echo": echo
}

MEDIA_GROUP_TYPES = {
    "audio": InputMediaAudio,
    "document": InputMediaDocument,
    "photo": InputMediaPhoto,
    "video": InputMediaVideo,
}


class MsgDict(TypedDict):
    media_type: Literal["video", "photo", "document"]
    media_id: str
    caption: str
    post_id: int
    sender_id: int


async def service_command_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_delete(update, context)
    cmd = update.effective_message.text.split()[0][1:].lower()

    # ⛔ Solo admin/moderatori
    if not await is_admin(update.effective_user.id, context):
        return await send_temporary_message(update, context, "⛔ Solo gli admin possono usare questo comando.")

    if cmd not in action_map:
        return await send_private_alert(update, context, "❌ Comando non riconosciuto.")

    await action_map[cmd](update, context, update.message.text)



async def multimedia_echo_sender(context: ContextTypes.DEFAULT_TYPE, update: Update):
    bot = context.bot
    job_data = cast(List[MsgDict], context.job.data)
    media_group_sender_id = context.job.data[0]["sender_id"]

    if not _check_echo_command_in_group_media(job_data):
        log.info("Nessun comando tipo 'echo' presente nel media group.")
        return

    for el in job_data:
        await safe_delete(update=update, context=context, message_id=el["post_id"])
        await asyncio.sleep(0.3)

    if not await is_admin(user_id=media_group_sender_id, context=context):
        await send_temporary_message(
            update=update,
            context=context,
            text="⛔ Solo gli admin possono usare questo comando."
        )
        return

    media = []
    for msg_dict in job_data:
        media.append(
            MEDIA_GROUP_TYPES[msg_dict["media_type"]](
                media=msg_dict["media_id"], caption=msg_dict["caption"]
            )
        )
    if not media:
        return
    msgs = await bot.send_media_group(chat_id=context.bot_data["group_chat_id"], media=media)
    for index, msg in enumerate(msgs):
        context.bot_data["messages"][
            job_data[index]["post_id"]
        ] = msg.message_id
    await msgs[-1].pin()


def _check_echo_command_in_group_media(message_data: List[MsgDict]) -> bool:
    for el in message_data:
        caption = el["caption"]
        if not caption:
            continue
        s_caption = caption.split(None, 1)
        if s_caption[0].lower() in (".echo", "/echo", "!echo", ".annuncio", "!annuncio", "/annuncio"):
            return True
    return False


async def handle_media_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "caption": message.caption_html,
        "post_id": message.message_id,
        "sender_id": message.from_user.id
    }
    jobs = context.job_queue.get_jobs_by_name(str(message.media_group_id))
    if jobs:
        jobs[0].data.append(msg_dict)
    else:
        context.job_queue.run_once(
            callback=partial(multimedia_echo_sender, update),
            when=5,
            data=[msg_dict],
            name=str(message.media_group_id)
        )
