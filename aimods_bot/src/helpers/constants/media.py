from telegram import InputMediaAudio, InputMediaDocument, InputMediaPhoto, InputMediaVideo, InputMediaAnimation

MEDIA_GROUP_TYPES = {
    "audio": InputMediaAudio,
    "document": InputMediaDocument,
    "photo": InputMediaPhoto,
    "video": InputMediaVideo,
    "gif": InputMediaAnimation
}
