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
    GREYLIST = "greylist"
    ALLOW_AFTER = "allow_after"
    IF_NOT_MEMBER = "if_not_member"


class ModerationListsRoute(StrEnum):
    VIEW = "view"
    ADD = "add"
    REMOVE = "remove"


class AntispamRoute(StrEnum):
    LINK = "link"
    MENTION = "mention"
    FORWARD = "forward"
    MEDIA = "media"

    # ANTISPAM MENTION
    PER_MESSAGE = "per_message"


class AntifloodRoute(StrEnum):
    MESSAGE_NUMBER = "message_number"
    MESSAGE_TIME = "message_time"


class ForwardRoute(StrEnum):
    TIMESPAN = "timespan"
    PER_USER = "per_user"
    PER_CONTENT = "per_content"
    PER_SOURCE = "per_source"


class PunishmentRoute(StrEnum):
    DURATION = "duration"
    DURATION_ENDLESS = "endless"

    WARN = "warn"
    KICK = "kick"
    MUTE = "mute"
    BAN = "ban"


class AllowafterDurationRoute(StrEnum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    OFF = "off"

    def build(self, value: int):
        return f"{value}:{self.value}"
