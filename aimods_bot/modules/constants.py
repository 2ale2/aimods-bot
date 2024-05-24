# contiene classi personalizzate che contengono valori di default usati dal bot
# la classe Scopes è istaziata per consentire di aggiungere istanze di Scope personalizzate

from typing import Set, Union
from enum import IntEnum
from dataclasses import dataclass, field
import core

TOPICS = core.get_topics_from_json()

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
class Limitations(IntEnum):
    SEND_MESSAGES: 0
    SEND_ALL_MEDIA: 1
    SEND_PHOTO: 2
    SEND_VIDEO_FILES: 3
    SEND_VIDEO_MESSAGES: 4
    SEND_MUSIC: 5
    SEND_FILES: 6
    SEND_STICKERS_GIFTS: 7
    SEND_EMBEDDED_LINKS: 8
    SEND_POOLS: 9
    ADD_MEMBERS: 10
    CREATE_TOPICS: 11
    PIN_MESSAGES: 12
    CHANGE_GROUP_INFO: 13


@dataclass
class DatabaseException(Exception):
    error_message = 'Qualcosa è andato storto col database. Leggi i log.'


@dataclass(frozen=True)
class Exceptions(Exception):
    DatabaseException = DatabaseException,

