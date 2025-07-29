import telegram
from telegram.ext.filters import MessageFilter, ChatType
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json


class ChannelMessageForRecapFilter(MessageFilter):
    def filter(self, message: telegram.Message):
        if message.chat.type is not ChatType.CHANNEL:
            return False
        if not message.text and not message.caption:
            return False
        hashtags = get_data_from_json("hashtags")["platforms"]
        l = []
        for el in hashtags:
            l.extend(hashtags[el])
        if any(hashtag in message.text for hashtag in l):
            return True
        return False


class MediaGroupIDMessageFilter(MessageFilter):
    def filter(self, message: telegram.Message):
        if message.media_group_id:
            return True
        return False


class ChatSharedFilter(MessageFilter):
    def filter(self, message: telegram.Message):
        if message.users_shared or message.chat_shared:
            return True
        return False
