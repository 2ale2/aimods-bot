from enum import StrEnum


class ModerationRoute(StrEnum):
    # admin/moderation
    SECURITY_FILTERS = "security_filters"
    USER_MODERATION = "user_moderation"
    MEDIA_CONTENT = "media_content"
    COMMUNITY = "community"


class SecurityFiltersRoute(StrEnum):
    # admin/moderation/security_filters
    ANTISPAM = "antispam"
    ANTIFLOOD = "antiflood"
    FORBIDDEN_WORDS = "forbidden_words"
    CHECKS = "checks"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    LENGTH = "length"

    PUNISHMENT = "punishment"
    WHITELIST = "whitelist"
    ALLOW_AFTER = "allow_after"


class ModerationListsRoute(StrEnum):
    VIEW = "view"
    ADD = "add"
    REMOVE = "remove"


class AntispamRoute(StrEnum):
    LINK = "link"
    MENTION = "mention"
    FORWARD = "forward"
    MEDIA = "media"


class PunishmentRoute(StrEnum):
    DURATION = "duration"
    DURATION_ENDLESS = "endless"

    WARN = "warn"
    KICK = "kick"
    MUTE = "mute"
    BAN = "ban"
