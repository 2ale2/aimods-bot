from enum import IntEnum, auto

class ModerationSettingsStates(IntEnum):
    SECURITY_FILTERS = auto()
    USERS_MODERATION = auto()
    MESSAGES_AND_CONTENT = auto()
    COMMUNITY_MANAGEMENT = auto()
