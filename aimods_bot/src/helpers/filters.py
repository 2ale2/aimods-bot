import re
import telegram
from telegram.ext.filters import MessageFilter
from telegram.constants import ChatType


class ChannelMessageForRecapFilter(MessageFilter):
    _pattern = None

    @classmethod
    def set_hashtags(cls, hashtags_data: dict):
        platforms = hashtags_data.get("platforms", {})
        all_hashtags = []
        for key in platforms:
            all_hashtags.extend(platforms[key])

        if all_hashtags:
            pattern_str = "|".join(map(re.escape, all_hashtags))
            cls._pattern = re.compile(pattern_str, re.IGNORECASE)
        else:
            cls._pattern = None

    def filter(self, message: telegram.Message) -> bool:
        if message.chat.type is not ChatType.CHANNEL:
            return False

        text = message.caption or message.text
        if not text:
            return False

        if not self._pattern:
            return False

        return bool(self._pattern.search(text))


class MediaGroupIDMessageFilter(MessageFilter):
    def filter(self, message: telegram.Message):
        return bool(message.media_group_id)


class ChatSharedFilter(MessageFilter):
    def filter(self, message: telegram.Message):
        return bool(message.users_shared or message.chat_shared)
