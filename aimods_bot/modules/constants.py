from typing import List, Set
import json

TOPICS = {}

'''
scope
    'FORUM_SCOPE',              tutti i topic 
    'REQUESTS_SCOPE',           i topic delle richieste
    'ASSISTENCE_SCOPE',         i topic dell'assistenza 
    'OFF_TOPIC_SCOPE',          i topic off topic
    'SPECIFIC_TOPICS_SCOPE',    gruppo di topic
    'SINGLE_TOPIC'              singolo topic
    tutti gli scope sono costanti, ad eccezione di SPECIFIC_TOPICS_SCOPE che può essere stabilito arbitrariamente e 
    comprendere uno o più topic.
    ogni topic ha un 'SIGNLE_TOPIC'
'''


class Scope:
    def __init__(self, scope: str, topics: Set[int] | int):
        self.scope = scope.upper()
        self.topics = topics

    def add_topics(self, topics: Set[int] | int):
        self.topics = self.topics | {topics}

    def remove_topics(self, topics: Set[int] | int):
        self.topics = self.topics - {topics}

    def set_scope_name(self, scope: str):
        self.scope = scope

    def get_topics(self):
        return self.topics


class Scopes(Scope):
    FORUM_SCOPE = Scope('FORUM_SCOPE', )