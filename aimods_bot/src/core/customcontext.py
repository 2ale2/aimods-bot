"""
    Contesto personalizzato che contiene scorciatoie alle richieste di un utente
    e le relative restrizioni. Questo perché, da documentazione, aggiungere tali dettagli
    accedendo ad Application.user_data/chat_data è sconsigliato. Quindi quando è necessario
    aggiungere dei parametri a un utente specifico. Li si aggiunge a bot_data in una sezione
    apposita; il contesto personalizzato andrà poi a reperire il dettaglio voluto
    ritornando il valore di bot_data specificato e ponendolo all'interno di un parametro
    specifico.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union

from pydantic import BaseModel, Field, ConfigDict
from telegram.ext import CallbackContext, ExtBot, Application
from telegram import User as PTBUser, ChatMember as PTBChatMember
from pyrogram.types import User as PyroUser, ChatMember as PyroChatMember

from aimods_bot.src.core.pydantic import Configuration, JobInfo, RestartData, BanListItem, CommandConfig, \
    UserLimitations, RequestSectionLimitation, RequestCooldown, AdminNotifications, UserNotifications, CategorySetting
from aimods_bot.src.helpers.constants.constants import RequestStatus, SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE, \
    Platform, Category, RequestField
from aimods_bot.src.helpers.database import execute_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.requests import BaseRequest, PLATFORM_CATEGORY_REGISTRY
from aimods_bot.src.helpers.models.request_section import RequestSection

log = logger.getChild(__name__)


class UserDataPersistent(BaseModel):
    alerts: Dict[str, str] = Field(default_factory=dict)
    member_check: int = Field(default_factory=int)


class UserDataEphemeral(BaseModel):
    # TO BE IMPLEMENTED
    pass


class UserData(BaseModel):
    persistent: UserDataPersistent = Field(default_factory=UserDataPersistent)
    ephemeral: UserDataEphemeral = Field(default_factory=UserDataEphemeral)


class AdminLimitingUserRequests(BaseModel):
    user_id: int = Field(default_factory=int, description="User ID of the user to be limited")
    username: Optional[str] = Field(default=None, description="Username of the user to be limited")
    duration: int = Field(default_factory=int, description="Limit duration in seconds (0 if unlimited)")
    sections: Dict[RequestSection, bool] = Field(
        default_factory=dict,
        description="Sections to be limited (True if limited)"
    )
    reason: str = Field(default_factory=str, description="Reason for limiting")

    def model_post_init(self, __context):
        if not self.sections:
            self.sections = {
                RequestSection(platform=pl, category=ca): False
                for pl, categories in PLATFORM_CATEGORY_REGISTRY.items()
                for ca in categories
            }


class RequestWizardSession(BaseModel):
    """Contenitore per lo stato della sessione di compilazione attiva."""

    draft: BaseRequest = Field(
        description="New Request instance the user is compiling for submission."
    )

    requesting: RequestField | None = Field(
        default=None,
        description="The wizard request field the user is filling."
    )

    editing: bool | None = Field(
        default=None,
        description="The wizard request field the user is editing"
    )

    from_notification: bool = Field(
        default=False,
        description="Tells if the Request is being made from a received notification."
    )

    request_msg_id: int | None = Field(
        default=None,
        description="The bot message containing the wizard."
    )


class ChatDataPersistent(BaseModel):
    # ======== Both Admins & Users ========
    bot_message_id: Optional[int] = Field(
        default=None,
        description="Memory space for saving bot message IDs in the case an input from the user is expected."
    )
    # ======== Admins ========
    admin_notifications: AdminNotifications = Field(default_factory=AdminNotifications)
    limiting_user_requests: Optional[AdminLimitingUserRequests] = Field(
        default=None,
        description="Limitation class for getting user requests limitation parameters before saving in Bot memory"
    )
    # ======== Users ========
    user_notifications: UserNotifications = Field(default_factory=UserNotifications)
    active_request_wizard: Optional[RequestWizardSession] = Field(
        default=None,
        description="Active Request compiling session. If None, the user is not formulating a Request."
    )
    base_path: Optional[str] = Field(
        default_factory=str,
        description="Base path for saving ring strategy path management"
    )


class ChatDataEphemeral(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # Consent ChatMember and User objs
    # ======== Both Admins & Users ========
    action: Optional[str] = Field(
        default_factory=str,
        description="Memory space to keep which action the user is performing"
    )
    # ======== Admins ========
    working_request: Optional[BaseRequest] = Field(
        default=None,
        description="Request that has been selected for rejection from admin (allows to write personalized reason)."
    )
    resolved_members: Optional[Dict[int, Optional[Union[PTBChatMember, PyroChatMember]]]] = Field(
        default_factory=dict,
        description="Members cache to avoid flood limit while resolving. Must be not in persistence."
    )
    resolved_users: Optional[Dict[int, Union[PTBUser, PyroUser]]] = Field(
        default_factory=dict,
        description="Users cache to avoid flood limit while resolving. Must be not in persistence."
    )
    # ======== Users ========


class ChatData(BaseModel):
    persistent: ChatDataPersistent = Field(default_factory=ChatDataPersistent)
    ephemeral: ChatDataEphemeral = Field(default_factory=ChatDataEphemeral)


class BotData(BaseModel):
    configuration: Configuration = Field(default_factory=Configuration)
    bot_version: str = "1.0.1"
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())

    group_chat_id: Optional[int] = None
    admins: Dict[int, str] = Field(default_factory=dict)
    ban_list: Dict[int, BanListItem] = Field(default_factory=dict)
    user_limitations: Dict[int, UserLimitations] = Field(default_factory=dict)
    user_request_cooldowns: Dict[int, RequestCooldown] = Field(default_factory=dict)

    commands: Dict[str, CommandConfig] = Field(default_factory=dict)
    hashtags: Dict[str, Any] = Field(default_factory=dict)
    rules_text: str = ""
    user_joined_message_text: str = ""
    channel_join_link: str = ""
    group_join_link: str = "https://example.com"

    active_requests: Dict[int, BaseRequest] = Field(default_factory=dict)
    jobs: Dict[str, JobInfo] = Field(default_factory=dict)
    restart: RestartData = Field(default_factory=RestartData)

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",
        use_enum_values=True,
    )


# noinspection PyUnresolvedReferences,PyTypeChecker
class CustomContext(CallbackContext[ExtBot, BotData, dict, dict]):
    user_id: Optional[int]
    chat_id: Optional[int]

    @property
    def pydb(self) -> BotData:
        return self.bot_data

    @property
    def pydc(self) -> ChatData:
        return self.chat_data

    @property
    def pydu(self) -> UserData:
        return self.user_data

    def __init__(
            self,
            application: Application,
            chat_id: Optional[int] = None,
            user_id: Optional[int] = None
    ):
        super().__init__(application=application, chat_id=chat_id, user_id=user_id)

    @classmethod
    def from_update(cls, update: Update, application: Application) -> CustomContext:
        ctx = super().from_update(update, application)
        ctx.user_id = update.effective_user.id if update.effective_user else None
        ctx.chat_id = update.effective_chat.id if update.effective_chat else None
        return ctx

    @property
    def is_user_admin(self) -> bool:
        if self.user_id is None:
            return False
        return self.user_id in self.bot_data.admins

    def set_base_path(self, base_path: str):
        """Strategia del path ad anello mononodo: salvo il path base per costruire il secondario."""
        self.pydc.persistent.base_path = base_path

    def free_base_path(self):
        self.pydc.persistent.base_path = None

    @property
    def user_active_requests(self) -> dict[int, BaseRequest]:
        return {ix: r for ix, r in self.pydb.active_requests.items() if (r.user_id == self.user_id)}

    def cancellable_requests(self, from_user: Optional[bool] = False) -> dict[int, BaseRequest]:
        timer_sec = self.pydb.configuration.settings.request.cancel_timer
        active_requests = self.pydb.active_requests if not from_user else self.user_active_requests
        return {rid: r for rid, r in active_requests.items() if r.can_be_cancelled(timer_sec)}

    @property
    def user_cancellable_requests(self) -> dict[int, BaseRequest]:
        return self.cancellable_requests(from_user=True)

    def get_active_request_by_id(self, ix: int):
        return self.pydb.active_requests.get(ix, None)

    def get_requests_by_status(
            self,
            status: RequestStatus,
            platform: Platform | None = None,
            category: Category | None = None,
            from_user: bool | False = False
    ) -> dict[int, BaseRequest]:
        if status == RequestStatus.CANCELLED:
            log.warning("bot_data only contains active requests.")
            return {}
        requests = self.pydb.active_requests if not from_user else self.user_active_requests
        return {
            ix: r for ix, r in requests.items()
            if (
                    r.status == status and
                    (platform is None or r.platform == platform) and
                    (category is None or r.category == category)
            )
        }

    def get_user_requests_by_status(
            self,
            status: RequestStatus,
            platform: Platform | None = None,
            category: Category | None = None
    ) -> dict[int, BaseRequest]:
        return self.get_requests_by_status(status=status, platform=platform, category=category, from_user=True)

    def get_active_category_requests(
            self,
            section: RequestSection,
            from_user: Optional[bool] = False
    ) -> dict[int, BaseRequest]:
        active_requests = self.pydb.active_requests if not from_user else self.user_active_requests
        return {
            ix: r for ix, r in active_requests.items()
            if r.platform == section.platform and category == section.category
        }

    def get_user_active_category_requests(
            self,
            section: RequestSection
    ) -> dict[int, BaseRequest]:
        return self.get_active_category_requests(section=section, from_user=True)

    def init_request_wizard_session(
            self,
            user_id: int,
            section: RequestSection,
            from_notification: bool,
            msg_id: int
    ) -> None:
        config = PLATFORM_CATEGORY_REGISTRY[section.platform][section.category]
        fresh_draft = config.model(user_id=user_id, section=section)

        self.pydc.persistent.active_request_wizard = RequestWizardSession(
            draft=fresh_draft,
            from_notification=from_notification,
            request_msg_id=msg_id
        )

    def user_request_cooldown(self, user_id: Optional[int] = None) -> Optional[RequestCooldown]:
        user_id = user_id or self.user_id
        cooldown = self.pydb.user_request_cooldowns.get(user_id, None)
        if cooldown:
            end_utc = cooldown.until
            end_utc.replace(tzinfo=timezone.utc)
            if end_utc > datetime.now(timezone.utc):
                return cooldown
            try:
                del self.pydb.user_request_cooldowns[user_id]
            except KeyError:
                pass
            return None

    def set_user_request_cooldown(self, user_id: int) -> RequestCooldown:
        rc = RequestCooldown(
            user_id=user_id,
            until=datetime.now(timezone.utc) + self.pydb.configuration.settings.request.cooldown
        )
        self.pydb.user_request_cooldowns[user_id] = rc
        return rc

    def remove_user_request_cooldown(self, user_id: int) -> Optional[RequestCooldown]:
        rc = self.pydb.user_request_cooldowns.pop(user_id, None)
        if not rc:
            log.warning("User does not have a current request cooldown.")
        return rc

    def get_user_limitations(self, user_id: Optional[int] = None) -> Optional[UserLimitations]:
        return self.pydb.user_limitations.get(user_id or self.user_id, None)

    def get_user_request_limitations(
            self,
            user_id: Optional[int] = None
    ) -> Optional[list[RequestSectionLimitation]]:
        user_limitations = self.get_user_limitations(user_id=user_id or self.user_id)
        if user_limitations:
            return user_limitations.requests
        return None

    def is_user_request_limited(
            self,
            section: RequestSection,
            user_id: Optional[int] = None
    ) -> Optional[RequestSectionLimitation]:
        """Esegue il double check e ritorna l'eventuale limitazione, oppure None se l'utente non è limitato."""

        self.check_user_request_limitations(user_id=user_id or self.user_id)
        ul = self.get_user_request_limitations()
        if ul:
            for l in ul:
                if l.platform == section.platform and l.category == section.category:
                    return l
        return None

    def get_or_create_limitation_wizard(
            self,
            initial_section: Optional[RequestSection] = None,
    ) -> AdminLimitingUserRequests:
        """
        Restituisce il wizard di limitazione richieste nella chat corrente,
        creandolo se non esiste ancora.

        Se `initial_section` è specificata e il wizard viene creato in questo momento,
        quella sezione viene pre-selezionata (sections[initial_section] = True)
        """
        wizard = self.pydc.persistent.limiting_user_requests
        if wizard is None:
            wizard = AdminLimitingUserRequests()
            self.pydc.persistent.limiting_user_requests = wizard
            if initial_section is not None:
                wizard.sections[initial_section] = True
        return wizard

    def clear_limitation_wizard(self) -> None:
        """Resetta il wizard di limitazione richieste."""
        self.pydc.persistent.limiting_user_requests = None

    def set_user_request_limitations(self, user_id: int, limitations: list[RequestSectionLimitation]):
        if not self.get_user_limitations():
            self.pydb.user_limitations[user_id or self.user_id] = UserLimitations(requests=limitations)
        else:
            self.pydb.user_limitations[user_id or self.user_id].requests = limitations

    def check_user_request_limitations(self, user_id: Optional[int] = None):
        """Fa un double check per togliere le limitazioni che non sono state rimosse automaticamente."""
        ul = self.get_user_request_limitations(user_id=user_id or self.user_id)
        if ul:
            n_ul = []
            for l in ul:
                if l.until is not None and l.until < datetime.now(tz=timezone.utc):
                    continue
                n_ul.append(l)
            self.set_user_request_limitations(user_id=user_id or self.user_id, limitations=n_ul)

    def remove_from_active_requests(self, ix: int) -> bool:
        return bool(self.pydb.active_requests.pop(ix, None))

    async def edit_request_status(self, ix: int, status: RequestStatus, rejection_reason: Optional[str] = None):
        if status == RequestStatus.CANCELLED:
            self.remove_from_active_requests(ix=ix)
        elif status in (RequestStatus.COMPLETED, RequestStatus.REJECTED):
            from aimods_bot.src.helpers.job_queue import scheduled_remove_completed_requests
            job_name = f"remove_inactive_request:{ix}"
            job = self.job_queue.run_once(
                callback=scheduled_remove_completed_requests,
                when=SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE,
                data={"ix": ix},
                name=job_name
            )
            self.pydb.jobs[job_name] = JobInfo(
                next_date=job.next_t.strftime("%d_%m_%Y_%H_%M_%S"),
                executed=False
            )

        request = self.pydb.active_requests.get(ix, None)
        if request:
            request.edit_status(status=status, rejection_reason=rejection_reason)
        else:
            log.warning(f"Request {ix} not found.")

        status_value = status.value
        query = """UPDATE requests_test SET status = $1, rejection_reason = $2 WHERE id = $3"""

        res = await execute_query(query=query, params=[status_value, rejection_reason, int(ix)])
        if not res:
            log.error(f"Failed to update request {ix} status to '{status}'")
        else:
            log.info(f"Updated request {ix} status to '{status}'")

    # ======== SEZIONI RICHIESTE ========

    def is_request_section_open(self, section: RequestSection) -> bool:
        platform_section_settings = getattr(self.pydb.configuration.settings.request, section.platform, None)
        if platform_section_settings is None:
            log.error(f"Platform {section.platform.label} configuration not found.")
            return None
        category_section_settings = getattr(platform_section_settings, category, None)
        if category_section_settings is None:
            log.error(f"Category {section.category_config.label} configuration not found inside {platform.label}.")
            return None

        assert isinstance(category_section_settings, CategorySetting)
        return category_section_settings.toggle
