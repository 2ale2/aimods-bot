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
    'SPECIFIC_TOPICS_SCOPE',    gruppo di topic
    SINGLE TOPICS SCOPES,       singoli topic
    tutti gli scope sono costanti, ad eccezione di SPECIFIC_TOPICS_SCOPE che può essere stabilito arbitrariamente e 
    comprendere uno o più topic.
    ogni topic ha un 'SIGNLE_TOPIC'
'''


@dataclass(frozen=True)
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


@dataclass
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

    ANDROID_TOPIC_SCOPE: Scope = _create_single_topic_scope(
        'ANDROID_TOPIC_SCOPE', 'Android')
    WINDOWS_TOPIC_SCOPE: Scope = _create_single_topic_scope(
        'WINDOWS_TOPIC_SCOPE', 'Windows')
    IOS_TOPIC_SCOPE: Scope = _create_single_topic_scope(
        'IOS_TOPIC_SCOPE', 'iOS')
    MACOS_TOPIC_SCOPE: Scope = _create_single_topic_scope(
        'MACOS_TOPIC_SCOPE', 'MacOS')
    OFFTOPIC_TOPIC_SCOPE: Scope = _create_single_topic_scope(
        'OFFTOPIC_TOPIC_SCOPE', 'OffTopic')
    ASSISTENZA_APP_SOFTWARE_TOPIC_SCOPE: Scope = _create_single_topic_scope(
        'ASSISTENZA_APP_SOFTWARE_TOPIC_SCOPE', 'Assistenza App/Software')
    ASSISTENZA_PC_SMARTPHONE_TOPIC_SCOPE: Scope = _create_single_topic_scope(
        'ASSISTENZA_PC_SMARTPHONE_TOPIC_SCOPE', 'Assistenza Tecnica PC/Smartphone')
    RICHIESTE_MACOS_TOPIC_SCOPE: Scope = _create_single_topic_scope(
        'RICHIESTE_MACOS_TOPIC_SCOPE', 'Richieste MacOS')
    RICHIESTE_WINDOWS_TOPIC_SCOPE: Scope = _create_single_topic_scope(
        'RICHIESTE_WINDOWS_TOPIC_SCOPE', 'Richieste Windows')
    RICHIESTE_ANDROID_TOPIC_SCOPE: Scope = _create_single_topic_scope(
        'RICHIESTE_ANDROID_TOPIC_SCOPE', 'Richieste Android')
    RICHIESTE_IOS_TOPIC_SCOPE: Scope = _create_single_topic_scope(
        'RICHIESTE_IOS_TOPIC_SCOPE', 'Richieste iOS')
    GENERAL_TOPIC_SCOPE: Scope = _create_single_topic_scope(
        'GENERAL_TOPIC_SCOPE', 'Generale')


@dataclass
class Limitation(IntEnum):
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
