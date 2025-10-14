from __future__ import annotations

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import List, Optional, Literal, Dict, Union, Any, Set

from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer

from aimods_bot.src.helpers.constants.constants import Platform, Category, Arch, RequestStatus, RequestField, \
    SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE, CATEGORY_DETAILS
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("pydantic")


class PunishmentType(str, Enum):
    BAN = "ban"
    KICK = "kick"
    MUTE = "mute"
    WARN = "warn"


class JobInfo(BaseModel):
    next_date: str = Field(default_factory=str)
    executed: bool = Field(default=False)
    returned_value: Optional[Any] = Field(default=None)


class PunishmentConfig(BaseModel):
    type: PunishmentType
    time: int = Field(ge=0, description="Punishment time in seconds (0 for endless)")

    @field_serializer("type")
    def _serialize_punishment_type(self, ptype: PunishmentType):
        return ptype.value


class WhitelistConfig(BaseModel):
    user: List[int] = Field(default_factory=list)
    group: List[int] = Field(default_factory=list)
    channel: List[int] = Field(default_factory=list)
    bot: List[int] = Field(default_factory=list)


class CategorySetting(BaseModel):
    toggle: bool = True
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        description="Numero massimo di richieste consentite; None = illimitato"
    )

    @field_validator("limit", mode="before")
    @classmethod
    def normalize_limit(cls, v):
        if v == 0:
            return None
        return v


class AndroidRequestCategoryConfig(BaseModel):
    app: CategorySetting = Field(default_factory=CategorySetting)


class WindowsRequestCategoryConfig(BaseModel):
    software: CategorySetting = Field(default_factory=CategorySetting)
    game: CategorySetting = Field(default_factory=CategorySetting)
    adobe: CategorySetting = Field(default_factory=CategorySetting)
    daw: CategorySetting = Field(default_factory=CategorySetting)


class iOSRequestCategoryConfig(BaseModel):
    app: CategorySetting = Field(default_factory=CategorySetting)


class MacOSRequestCategoryConfig(BaseModel):
    software: CategorySetting = Field(default_factory=CategorySetting)
    daw: CategorySetting = Field(default_factory=CategorySetting)


class RequestConfig(BaseModel):
    android: AndroidRequestCategoryConfig = Field(default_factory=AndroidRequestCategoryConfig)
    windows: WindowsRequestCategoryConfig = Field(default_factory=WindowsRequestCategoryConfig)
    ios: iOSRequestCategoryConfig = Field(default_factory=iOSRequestCategoryConfig)
    macos: MacOSRequestCategoryConfig = Field(default_factory=MacOSRequestCategoryConfig)
    cancel_timer: int = Field(default=SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE, ge=0, description="Timer for cancelling requests")
    cooldown: timedelta = Field(default_factory=lambda: timedelta(days=7))

    @field_validator("cooldown", mode="before")
    def seconds_to_timedelta(cls, v):
        if isinstance(v, int):
            return timedelta(seconds=v)
        return v

    @field_serializer("cooldown")
    def _serialize_timedelta(self, td: timedelta):
        return int(td.total_seconds())


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

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",
        use_enum_values=True
    )


class RestartData(BaseModel):
    toggle: bool = False
    user_id: int = 0


class BanListItem(BaseModel):
    expires_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    reason: str = ""
    admin: int = 0


class CommandConfig(BaseModel):
    pattern: str = ""
    parameters: List[Literal["mention", "permissions", "duration", "message"]] = []


class Architecture(BaseModel):
    arch: Arch = None

    @property
    def arm_bool(self) -> bool:
        return self.arch in (Arch.ARM, Arch.ARM_64)


class RequestConversationFlow(BaseModel):
    flow: List[Literal["name", "link", "version", "functionalities", "steamtools", "arch"]]
    back_data: List[
        Literal[
            "back_main",
            "back_category",
            "back_name",
            "back_link",
            "back_version",
            "back_functionalities",
            "back_arch",
            "back_steamtools"
        ]
    ]


class RequestConversationFlowsConfig(BaseModel):
    android: Dict[Category, RequestConversationFlow] = Field(default_factory=dict)
    windows: Dict[Category, RequestConversationFlow] = Field(default_factory=dict)
    ios: Dict[Category, RequestConversationFlow] = Field(default_factory=dict)
    macos: Dict[Category, RequestConversationFlow] = Field(default_factory=dict)


class RequestCooldown(BaseModel):
    user_id: int = Field(default_factory=int)
    until: datetime = Field(default_factory=lambda: datetime.now() + timedelta(days=7))


class RequestSectionLimitation(BaseModel):
    section: str = ""
    until: Optional[datetime] = None
    reasons: Optional[list[str]] = Field(default_factory=list)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: int = Field(default_factory=int)
    updated_by: int = Field(default_factory=int)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def fill_now_if_none(cls, v):
        return v or datetime.now(timezone.utc)


class UserLimitations(BaseModel):
    user_id: Union[int, str] = Field(default_factory=str)
    requests: Optional[list[RequestSectionLimitation]] = Field(default_factory=list)


class Request(BaseModel):
    id: Optional[int] = 0
    user_id: Optional[int] = 0
    status: RequestStatus = RequestStatus.PENDING
    issued_at: str = ""
    platform: Optional[Platform] = None
    category: Optional[Category] = None
    name: str = ""
    arch: Optional[Architecture] = None
    version: str = ""
    link: str = ""
    functionalities: str = ""
    steamtools: Optional[bool] = None
    requesting: Optional[RequestField] = None
    editing: Optional[RequestField] = None
    rejection_reason: Optional[str] = Field(default_factory=str)
    status_change_notifications: bool = True

    @property
    def is_active(self):
        return self.status not in (RequestStatus.CANCELLED, RequestStatus.COMPLETED, RequestStatus.REJECTED)

    def can_be_cancelled(self, cancel_time_sec: int):
        if self.status != RequestStatus.PENDING:
            return False
        issued_datetime = datetime.fromisoformat(self.issued_at)
        if issued_datetime.tzinfo is None:
            issued_datetime = issued_datetime.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - issued_datetime).total_seconds() < cancel_time_sec

    def edit_status(self, status: RequestStatus, rejection_reason: Optional[str] = None):
        if status == RequestStatus.REJECTED:
            if not rejection_reason:
                log.warning("A rejection reason should bt not provided.")
            else:
                self.rejection_reason = rejection_reason
        self.status = status


class AdminNotifications(BaseModel):
    """Classe per le impostazioni sulle notifiche degli admin."""
    new_requests_notifications: Dict[str, Dict[str, bool]] = Field(
        default_factory=dict,
        description="Notifiche per le nuove richieste"
    )
    section_closing_notifications: Dict[str, Dict[str, bool]] = Field(
        default_factory=dict,
        description="Notifiche per la chiusura automatica delle sezioni"
    )

    def model_post_init(self, __context):
        if not self.new_requests_notifications:
            self.new_requests_notifications = {
                platform: {category: False for category in categories}
                for platform, categories in CATEGORY_DETAILS.items()
            }
        if not self.section_closing_notifications:
            self.section_closing_notifications = {
                platform: {category: False for category in categories}
                for platform, categories in CATEGORY_DETAILS.items()
            }


class UserNotifications(BaseModel):
    """Classe per le impostazioni sulle notifiche degli utenti."""
    section_opening_notifications: Dict[str, Dict[str, bool]] = Field(
        default_factory=dict,
        description="Notifiche per le nuove richieste"
    )

    def model_post_init(self, __context):
        if not self.section_opening_notifications:
            self.section_opening_notifications = {
                platform: {category: False for category in categories}
                for platform, categories in CATEGORY_DETAILS.items()
            }
