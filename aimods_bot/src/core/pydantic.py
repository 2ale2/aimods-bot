from functools import wraps
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
from enum import Enum

from aimods_bot.src.core.logger import logger

log = logger.getChild("pydantic")


class PunishmentType(str, Enum):
    BAN = "ban"
    KICK = "kick"
    MUTE = "mute"
    WARN = "warn"


class PunishmentConfig(BaseModel):
    type: PunishmentType
    time: int = Field(ge=0, description="Punishment time in seconds (0 for endless)")


class WhitelistConfig(BaseModel):
    user: List[int] = Field(default_factory=list)
    group: List[int] = Field(default_factory=list)
    channel: List[int] = Field(default_factory=list)
    bot: List[int] = Field(default_factory=list)

class AndroidRequestCategoryToggle(BaseModel):
    app: bool = True


class WindowsRequestCategoryToggle(BaseModel):
    software: bool = True
    game: bool = True
    adobe: bool = True
    daw: bool = True


class iOSRequestCategoryToggle(BaseModel):
    app: bool = True


class MacOSRequestCategoryToggle(BaseModel):
    software: bool = True
    daw: bool = True


class RequestConfig(BaseModel):
    android: AndroidRequestCategoryToggle = Field(default_factory=AndroidRequestCategoryToggle)
    windows: WindowsRequestCategoryToggle = Field(default_factory=WindowsRequestCategoryToggle)
    ios: iOSRequestCategoryToggle = Field(default_factory=iOSRequestCategoryToggle)
    macos: MacOSRequestCategoryToggle = Field(default_factory=MacOSRequestCategoryToggle)
    cancel_timer: int = Field(default=3600, ge=0, description="Timer for cancelling requests")


class AntispamLinkConfig(BaseModel):
    punishment: PunishmentConfig = Field(default_factory=lambda: PunishmentConfig(type=PunishmentType.WARN, time=0))
    allow_after: int = Field(default=3600, ge=0, description="Time before links are not allowed")
    whitelist: List[str] = Field(default_factory=list, description="Not punished domains")
    blacklist: List[str] = Field(default_factory=list, description="Banned domains")
    greylist: List[str] = Field(default_factory=list, description="Not punished links")


class AntispamMentionRateLimitConfig(BaseModel):
    toggle: bool = False
    timespan: int = Field(default=60, ge=1, description="Rate Limit Timespan")
    mention: int = Field(default=3, description="Rate Limit Mention Number")


class AntispamMentionCategoryConfig(BaseModel):
    toggle: bool = False
    if_not_member: Optional[bool] = None  # Solo per user
    punishment: PunishmentConfig = Field(default_factory=lambda: PunishmentConfig(type=PunishmentType.WARN, time=0))


class AntispamMentionConfig(BaseModel):
    allow_after: int = Field(default=3600, ge=0, description="Time before mentions are not allowed")
    per_message: int = Field(default=3, ge=1, description="Max mentions in a single message")
    rate_limit: AntispamMentionRateLimitConfig = Field(default_factory=AntispamMentionRateLimitConfig)
    user: AntispamMentionCategoryConfig = Field(default_factory=lambda: AntispamMentionCategoryConfig(
        toggle=True,
        if_not_member=True,
        punishment=PunishmentConfig(type=PunishmentType.KICK, time=100),
    ))
    group: AntispamMentionCategoryConfig = Field(default_factory=lambda: AntispamMentionCategoryConfig(
        toggle=True,
        if_not_member=None,
        punishment=PunishmentConfig(type=PunishmentType.KICK, time=100)
    ))
    channel: AntispamMentionCategoryConfig = Field(default_factory=lambda: AntispamMentionCategoryConfig(
        toggle=True,
        if_not_member=None,
        punishment=PunishmentConfig(type=PunishmentType.KICK, time=100)
    ))
    bot: AntispamMentionCategoryConfig = Field(default_factory=lambda: AntispamMentionCategoryConfig(
        toggle=True,
        if_not_member=None,
        punishment=PunishmentConfig(type=PunishmentType.KICK, time=100)
    ))
    whitelist: WhitelistConfig = Field(default_factory=WhitelistConfig)


class AntispamForwardRateLimitConfig(BaseModel):
    timespan: int = Field(default=100, ge=1, description="Rate Limit Timespan")
    same_content: int = Field(default=2, ge=1, description="Max forwards with same content within the timespan")
    same_source: int = Field(default=2, ge=1, description="Max forwards from the same source within the timespan")
    same_user: int = Field(default=2, ge=1, description="Max forwards from the same user within the timespan")


class AntispamForwardCategoryConfig(BaseModel):
    toggle: bool = True
    if_not_member: Optional[bool] = None  # Solo per user
    punishment: PunishmentConfig = Field(default_factory=lambda: PunishmentConfig(type=PunishmentType.WARN, time=0))


class AntispamForwardConfig(BaseModel):
    allow_after: int = Field(default=86400, ge=0, description="Time before forwards are not allowed")
    rate_limit: AntispamForwardRateLimitConfig = Field(default_factory=AntispamForwardRateLimitConfig)
    user: AntispamMentionCategoryConfig = Field(default_factory=lambda: AntispamMentionCategoryConfig(
        toggle=True,
        if_not_member=True,
        punishment=PunishmentConfig(type=PunishmentType.KICK, time=100)
    ))
    group: AntispamMentionCategoryConfig = Field(default_factory=lambda: AntispamMentionCategoryConfig(
        toggle=True,
        if_not_member=None,
        punishment=PunishmentConfig(type=PunishmentType.KICK, time=100)
    ))
    channel: AntispamMentionCategoryConfig = Field(default_factory=lambda: AntispamMentionCategoryConfig(
        toggle=True,
        if_not_member=None,
        punishment=PunishmentConfig(type=PunishmentType.KICK, time=100)
    ))
    bot: AntispamMentionCategoryConfig = Field(default_factory=lambda: AntispamMentionCategoryConfig(
        toggle=True,
        if_not_member=None,
        punishment=PunishmentConfig(type=PunishmentType.KICK, time=100)
    ))


class AntispamConfig(BaseModel):
    toggle: bool = True
    punishment: PunishmentConfig = Field(default_factory=lambda: PunishmentConfig(type=PunishmentType.WARN, time=0))
    whitelist: WhitelistConfig = Field(default_factory=WhitelistConfig)
    link: AntispamLinkConfig = Field(default_factory=AntispamLinkConfig)
    mention: AntispamMentionConfig = Field(default_factory=AntispamMentionConfig)
    forward: AntispamForwardConfig = Field(default_factory=AntispamForwardConfig)


class AntifloodSettings(BaseModel):
    time_messages: int = Field(default=5, ge=1, description="Antiflood timespan")
    number_messages: int = Field(default=10, ge=1, description="Max number of messages within the timespan")


class AntifloodConfig(BaseModel):
    toggle: bool = True
    settings: AntifloodSettings = Field(default_factory=AntifloodSettings)
    punishment: PunishmentConfig = Field(default_factory=lambda: PunishmentConfig(type=PunishmentType.KICK, time=100))


class ModerationConfig(BaseModel):
    antispam: AntispamConfig = Field(default_factory=AntispamConfig)
    antiflood: AntifloodConfig = Field(default_factory=AntifloodConfig)


class SettingsConfig(BaseModel):
    request: RequestConfig = Field(default_factory=RequestConfig)


class Configuration(BaseModel):
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    moderation: ModerationConfig = Field(default_factory=ModerationConfig)

    class Config:
        validate_assignment = True
        extra = "forbid"


class BotData(BaseModel):
    configuration: Configuration = Field(default_factory=Configuration)
    group_chat_id: Optional[int] = None

    admins: Dict[int, str] = Field(default_factory=dict)
    ban_list: Dict[str, Any] = Field(default_factory=dict)
    user_joined_message_text: str = ""
    rules_text: str = ""
    commands: Dict[str, Any] = Field(default_factory=dict)
    hashtags: Dict[str, Any] = Field(default_factory=dict)
    active_requests: Dict[str, Any] = Field(default_factory=dict)
    jobs: Dict[str, Any] = Field(default_factory=dict)
    bot_version: str = "1.0.0"
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())

    class Config:
        validate_assignment = True
        extra = "allow"
