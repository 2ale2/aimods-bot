from telegram import Video, Audio, Voice, Document, Sticker, Poll

from aimods_bot.modules.constants import AttachmentType


async def get_file(file):
    try:
        iter(file)
    except TypeError:
        return file.get_file()
    else:
        await get_file(file[-1])


async def get_attachment_type(attachment):
    if isinstance(attachment, list):
        return AttachmentType.IMAGE

    if isinstance(attachment, Video):
        return AttachmentType.VIDEO

    if isinstance(attachment, Audio):
        return AttachmentType.AUDIO

    if isinstance(attachment, Voice):
        return AttachmentType.VOICE

    if isinstance(attachment, Document):
        return AttachmentType.DOCUMENT

    if isinstance(attachment, Sticker):
        return AttachmentType.STICKER

    if isinstance(attachment, Poll):
        return AttachmentType.POLL
