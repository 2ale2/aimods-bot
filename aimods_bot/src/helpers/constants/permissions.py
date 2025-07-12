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
