# contiene classi personalizzate che contengono valori di default usati dal bot

from enum import IntEnum, auto
from dataclasses import dataclass

import telegram

from utils import get_data_from_json
from telegram.ext.filters import MessageFilter
from telegram.constants import ChatType

TOPICS = get_data_from_json("forum_topics")

'''
scope
    'FORUM_SCOPE',              tutti i topic 
    'REQUESTS_SCOPE',           i topic delle richieste
    'ASSISTENCE_SCOPE',         i topic dell'assistenza 
    'OFF_TOPIC_SCOPE',          i topic off topic
    specific topic scope,       gruppo di topic
    single topic scope,       singoli topic
    tutti gli scope sono costanti, ad eccezione di SPECIFIC_TOPICS_SCOPE che può essere stabilito arbitrariamente e 
    comprendere uno o più topic.
    ogni topic ha un single topic scope
'''


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


@dataclass(frozen=True)
class Permissions(IntEnum):
    can_send_messages = 0
    can_send_polls = 1
    can_send_other_messages = 2
    can_add_web_page_previews = 3
    can_invite_users = 4
    can_send_audios = 5
    can_send_documents = 6
    can_send_photos = 7
    can_send_videos = 8
    can_send_video_notes = 9
    can_send_voice_notes = 10


class ModerationSettingsStates(IntEnum):
    # - menu principale
    MAIN_MENU_CHOICE = auto()
    # -- menu.sicurezza_e_filtri
    SECURITY_FILTERS_CHOICE = auto()
    # --- menu.sicurezza_e_filtri.antispam
    ANTISPAM_MAIN_PANEL = auto()
    # ---- menu.sicurezza_e_filtri.antispam.blocco_link
    ANTISPAM_SET_LINK = auto()
    # ---- menu.sicurezza_e_filtri.antispam.blocco_link
    ANTISPAM_EDIT_LIST = auto()
    # ---- imposta punizione
    SET_PUNISHMENT = auto()
    # ----- durata punizione
    SET_PUNISHMENT_DURATION = auto()

    # -- menu.sicurezza_e_filtri.antiflood
    ANTIFLOOD_MAIN_PANEL = auto()
    # --- menu.sicurezza_e_filtri.antiflood.set_limits
    ANTIFLOOD_SET_LIMITS = auto()
