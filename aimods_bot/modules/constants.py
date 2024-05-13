from typing import Set, Union
from enum import IntEnum
from dataclasses import dataclass
import core

TOPICS = core.get_topics()

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
    FORUM_SCOPE: Scope = Scope('FORUM_SCOPE', {topic["id"] for topic in TOPICS["all"]})
    REQUESTS_SCOPE: Scope = Scope('REQUESTS_SCOPE', {topic["id"] for topic in TOPICS["richieste"]})
    ASSISTENCE_SCOPE: Scope = Scope('ASSISTENCE_SCOPE', {topic["id"] for topic in TOPICS["assistenza"]})
    OFF_TOPIC_SCOPE: Scope = Scope('OFF_TOPIC_SCOPE', {topic["id"] for topic in TOPICS["off_topic"]})

    @classmethod
    def _create_single_topic_scope(cls, name: str, topic_name: str) -> Scope:
        topic_id = next((topic["id"] for topic in TOPICS["forum_topics"]["all"].values()
                         if topic["name"] == topic_name), None)
        return Scope(name, {topic_id} if topic_id is not None else set())

    for topic in TOPICS["forum_topics"]["all"]:
        scope_name = topic["name"].upper() + "_TOPIC_SCOPE"
        globals()[scope_name]: Scope = _create_single_topic_scope(name=scope_name, topic_name=topic["name"])


@dataclass(frozen=True)
class Limitations(IntEnum):
    SEND_MESAGGES: 0
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
