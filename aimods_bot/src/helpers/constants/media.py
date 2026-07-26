from enum import StrEnum
from telegram import InputMediaAudio, InputMediaDocument, InputMediaPhoto, InputMediaVideo, InputMediaAnimation

class MediaType(StrEnum):
    DOCUMENT = "document"
    PHOTO = "photo"
    AUDIO = "audio"
    VIDEO = "video"
    GIF = "gif"


MEDIA_GROUP_TYPES = {
    MediaType.AUDIO: InputMediaAudio,
    MediaType.DOCUMENT: InputMediaDocument,
    MediaType.PHOTO: InputMediaPhoto,
    MediaType.VIDEO: InputMediaVideo,
    MediaType.GIF: InputMediaAnimation
}
