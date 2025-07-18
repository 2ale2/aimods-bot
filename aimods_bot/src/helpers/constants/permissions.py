from telegram import ChatPermissions as PTBChatPermissions
from pyrogram.types import ChatPermissions as PyroChatPermissions

from dataclasses import dataclass
from enum import IntEnum, auto

@dataclass(frozen=True)
class Permissions(IntEnum):
    can_send_messages = auto()
    can_send_polls = auto()
    can_send_other_messages = auto()
    can_add_web_page_previews = auto()
    can_invite_users = auto()
    can_send_audios = auto()
    can_send_documents = auto()
    can_send_photos = auto()
    can_send_videos = auto()
    can_send_video_notes = auto()
    can_send_voice_notes = auto()


permissions_texts = {
    "can_send_messages": "Inviare messaggi",
    "can_send_polls": "Inviare sondaggi",
    "can_send_other_messages": "Inviare stickers e GIFs",
    "can_add_web_page_previews": "Aggiungere Web Previews",
    "can_invite_users": "Invitare altri membri",
    "can_send_audios": "Inviare file audio",
    "can_send_documents": "Inviare documenti",
    "can_send_photos": "Inviare foto",
    "can_send_videos": "Inviare video",
    "can_send_video_notes": "Inviare note video",
    "can_send_voice_notes": "Inviare note vocali"
}


default_permissions = {
    "can_send_messages": None,
    "can_send_polls": None,
    "can_send_other_messages": None,
    "can_add_web_page_previews": None,
    "can_invite_users": None,
    "can_send_audios": None,
    "can_send_documents": None,
    "can_send_photos": None,
    "can_send_videos": None,
    "can_send_video_notes": None,
    "can_send_voice_notes": None
}


def set_default_permissions(to: bool):
    return {i: to for i in default_permissions.keys()}


PTBFalsePermissions = PTBChatPermissions().no_permissions()
PTBTruePermissions = PTBChatPermissions().all_permissions()

PyroFalsePermissions = PyroChatPermissions(**(set_default_permissions(False)))
PyroTruePermissions = PyroChatPermissions(**(set_default_permissions(True)))


def get_pyro_permissions(b: bool):
    if b:
        return PTBTruePermissions
    return PTBFalsePermissions


def get_ptb_permissions(b: bool):
    if b:
        return PTBTruePermissions
    return PTBFalsePermissions
