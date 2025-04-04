# contiene classi personalizzate che contengono valori di default usati dal bot
# la classe Scopes è istaziata per consentire di aggiungere istanze di Scope personalizzate

from typing import Set, Union
from enum import IntEnum
from dataclasses import dataclass, field
from utils import get_data_from_json
from telegram import Video, Audio, Voice, Document, Sticker, Poll

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


@dataclass
class Scope:
    name: str
    topics: Set[int]

    def add_topics_to_scope(self, new_topics: Union[Set[int], int]):
        if isinstance(new_topics, int):
            new_topics = {new_topics}
        self.topics |= new_topics

    def remove_topics_from_scope(self, topics_to_remove: Union[Set[int], int]):
        if isinstance(topics_to_remove, int):
            topics_to_remove = {topics_to_remove}
        self.topics -= topics_to_remove


@dataclass(frozen=True)
class Scopes:
    FORUM_SCOPE: Scope = field(
        default_factory=lambda: Scope('FORUM_SCOPE', {topic["id"] for topic in TOPICS["all"].values()})
    )
    REQUESTS_SCOPE: Scope = field(
        default_factory=lambda: Scope('REQUESTS_SCOPE', {topic["id"] for topic in TOPICS["richieste"].values()})
    )
    ASSISTENCE_SCOPE: Scope = field(
        default_factory=lambda: Scope('ASSISTENCE_SCOPE', {topic["id"] for topic in TOPICS["assistenza"].values()})
    )
    OFF_TOPIC_SCOPE: Scope = field(
        default_factory=lambda: Scope('OFF_TOPIC_SCOPE', {topic["id"] for topic in TOPICS["off_topic"].values()})
    )

    @classmethod
    def create_single_topic_scope(cls, name: str, topic_name: str) -> Scope:
        topic_id = next((topic["id"] for topic in TOPICS["all"].values()
                         if topic["name"] == topic_name), None)
        return Scope(name, {topic_id} if topic_id is not None else set())


for topic in TOPICS["all"].values():
    scope_name = topic["name"].replace(" ", "_").upper() + "_TOPIC_SCOPE"
    setattr(Scopes, scope_name, Scopes.create_single_topic_scope(name=scope_name, topic_name=topic["name"]))


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


@dataclass(frozen=True)
class AttachmentType(IntEnum):
    IMAGE = 0
    VIDEO = 1
    AUDIO = 2
    VOICE = 4
    DOCUMENT = 5
    STICKER = 6
    POLL = 7

    @classmethod
    async def get_attachment_type(cls, attachment):
        match attachment:
            case list(): return cls.IMAGE
            case Video(): return cls.VIDEO
            case Audio(): return cls.AUDIO
            case Voice(): return cls.VOICE
            case Document(): return cls.DOCUMENT
            case Sticker(): return cls.STICKER
            case Poll(): return cls.POLL
            case _: raise ValueError("Tipo di allegato non supportato")
