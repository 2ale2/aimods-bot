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

from datetime import datetime, time, timezone
from typing import Dict, Any, Union

from pydantic import BaseModel, Field, ConfigDict, field_validator
from telegram.ext import CallbackContext, ExtBot, Application
from telegram import User as PTBUser, ChatMember as PTBChatMember
from pyrogram.types import User as PyroUser, ChatMember as PyroChatMember

from aimods_bot.src.core.pydantic import Configuration, JobInfo, RestartData, BanListItem, CommandConfig, \
    UserLimitations, RequestSectionLimitation, RequestCooldown, AdminNotifications, UserNotifications, CategorySetting
from aimods_bot.src.helpers.constants.constants import RequestStatus, SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE, \
    Platform, Category, RequestField, REQUESTS_TABLE, LOCAL_TZ, ReminderField
from aimods_bot.src.helpers.database import execute_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.jobs import RemoveCompletedRequestJob
from aimods_bot.src.helpers.models.requests import BaseRequest, PLATFORM_CATEGORY_REGISTRY
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.reminders import Reminder, Recurrence
from aimods_bot.src.helpers.utils.reminder_time_utils import compute_first_fire

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
    username: str | None = Field(default=None, description="Username of the user to be limited")
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


class ReminderWizard(BaseModel):
    """Bozza di promemoria in compilazione."""
    requesting: ReminderField | None = Field(
        default=None,
        description="The wizard reminder field the user is filling."
    )

    editing: bool = Field(
        default=False,
        description="The wizard reminder field the user is editing"
    )

    reminder_id: int | None = Field(default=None, description="ID del promemoria")

    title: str | None = None
    body: str | None = None
    thread_id: int | None = None

    recurrence: Recurrence | None = None
    fire_time: time | None = Field(default=None, description="Ora locale, solo per i ricorrenti")

    interval_days: int | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None

    once_at: datetime | None = Field(default=None, description="Naive, ora locale. Solo per ONCE")

    def set_recurrence(self, recurrence: Recurrence) -> None:
        """Cambia ricorrenza azzerando i campi delle altre."""
        self.recurrence = recurrence
        self.interval_days = None
        self.day_of_week = None
        self.day_of_month = None
        if recurrence is not Recurrence.ONCE:
            self.once_at = None
        else:
            self.fire_time = None

    @property
    def flow(self) -> list[ReminderField]:
        """Sequenza di domande in base a ricorrenza"""
        base = [ReminderField.TITLE, ReminderField.BODY, ReminderField.RECURRENCE]
        if self.recurrence is None:
            return base
        if self.recurrence is Recurrence.ONCE:
            return base + [ReminderField.ONCE_AT]

        specific = {
            Recurrence.INTERVAL: ReminderField.INTERVAL_DAYS,
            Recurrence.WEEKLY: ReminderField.DAY_OF_WEEK,
            Recurrence.MONTHLY: ReminderField.DAY_OF_MONTH,
        }[self.recurrence]
        return base + [specific, ReminderField.FIRE_TIME]

    def advance_or_finish_wizard(self) -> None:
        """Punta `requesting` alla prima domanda senza risposta. None = bozza completa."""
        self.requesting = None
        for field in self.flow:
            if getattr(self, field.value) is None:
                self.requesting = field
                break

    @property
    def missing_fields(self) -> list[ReminderField]:
        """Campi ancora da compilare, per il pannello di riepilogo."""
        return [field for field in self.flow if getattr(self, field.value) is None]

    @property
    def is_complete(self) -> bool:
        return not self.missing_fields

    @classmethod
    def from_reminder(cls, reminder: Reminder) -> ReminderWizard:
        """Precarica il wizard per la modifica di un promemoria esistente."""
        once_at = None
        if reminder.recurrence is Recurrence.ONCE:
            once_at = reminder.next_fire.astimezone(LOCAL_TZ).replace(tzinfo=None)

        return cls(
            reminder_id=reminder.id,
            title=reminder.title,
            body=reminder.body,
            thread_id=reminder.thread_id,
            recurrence=reminder.recurrence,
            fire_time=None if reminder.recurrence is Recurrence.ONCE else reminder.fire_time,
            interval_days=reminder.interval_days,
            day_of_week=reminder.day_of_week,
            day_of_month=reminder.day_of_month,
            once_at=once_at,
        )

    def to_reminder(self, chat_id: int, created_by: int) -> Reminder:
        """
        Costruisce il Reminder validato. Solleva ValueError se la bozza è incompleta.

        `next_fire` è sempre UTC; `fire_time` resta ora locale (è una regola,
        non un istante). Vedi DESIGN.md.
        """
        missing = self.missing_fields
        if missing:
            raise ValueError(f"Incomplete draft, missing: {', '.join(missing)}")

        if self.recurrence is Recurrence.ONCE:
            local = self.once_at
            if local.tzinfo is None:
                local = local.replace(tzinfo=LOCAL_TZ)
            next_fire = local.astimezone(timezone.utc)
            fire_time = local.time()
        else:
            fire_time = self.fire_time
            next_fire = compute_first_fire(
                recurrence=self.recurrence,
                fire_time=fire_time,
                day_of_week=self.day_of_week,
                day_of_month=self.day_of_month,
            )

        return Reminder(
            id=self.reminder_id,
            title=self.title,
            body=self.body,
            chat_id=chat_id,
            thread_id=self.thread_id,
            recurrence=self.recurrence,
            fire_time=fire_time,
            next_fire=next_fire,
            interval_days=self.interval_days,
            day_of_week=self.day_of_week,
            day_of_month=self.day_of_month,
            created_by=created_by,
        )


class RequestWizardSession(BaseModel):
    """Contenitore per lo stato della sessione di compilazione attiva."""

    draft: BaseRequest = Field(
        description="New Request instance the user is compiling for submission."
    )

    requesting: RequestField | None = Field(
        default=None,
        description="The wizard request field the user is filling."
    )

    editing: bool = Field(
        default=False,
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

    @field_validator("draft", mode="before")
    @classmethod
    def _rebuild_draft_subclass(cls, v):
        if isinstance(v, BaseRequest) and type(v) is not BaseRequest:
            return v

        if isinstance(v, BaseRequest):
            data = v.model_dump()
        elif isinstance(v, dict):
            data = v
        else:
            return v

        section_data = data.get("section")
        if section_data is None:
            return v

        if isinstance(section_data, RequestSection):
            platform, category = section_data.platform, section_data.category
        elif isinstance(section_data, dict):
            platform = Platform(section_data["platform"])
            category = Category(section_data["category"])
        else:
            return v

        try:
            model_cls = PLATFORM_CATEGORY_REGISTRY[platform][category].model
        except KeyError:
            return v

        data = dict(data)
        data["section"] = RequestSection(platform=platform, category=category)
        return model_cls.model_construct(**data)


class RequestRejectionSession(BaseModel):
    request_id: int = Field(description="ID of the request to be rejected")
    reason: str | None = Field(default=None, description="Rejection reason")
    bot_msg_id: int | None = Field(default=None)


class ChatDataPersistent(BaseModel):
    # ======== Both Admins & Users ========
    bot_message_id: int | None = Field(
        default=None,
        description="Memory space for saving bot message IDs in the case an input from the user is expected."
    )
    # ======== Admins ========
    admin_notifications: AdminNotifications = Field(default_factory=AdminNotifications)
    limiting_user_requests: AdminLimitingUserRequests | None = Field(
        default=None,
        description="Limitation class for getting user requests limitation parameters before saving in Bot memory"
    )
    active_reminder_wizard: ReminderWizard | None = Field(
        default=None,
        description="Reminder draft. None if no wizard is active."
    )
    # ======== Users ========
    user_notifications: UserNotifications = Field(default_factory=UserNotifications)
    active_request_wizard: RequestWizardSession | None = Field(
        default=None,
        description="Active Request compiling session. If None, the user is not formulating a Request."
    )
    root_path: str | None = Field(
        default_factory=str,
        description="For saving root path"
    )
    relative_path: str | None = Field(
        default_factory=str,
        description="For saving relative path"
    )


class ChatDataEphemeral(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # Consent ChatMember and User objs
    # ======== Both Admins & Users ========
    action: str | None = Field(
        default_factory=str,
        description="Memory space to keep which action the user is performing"
    )
    # ======== Admins ========
    working_request: BaseRequest | None = Field(
        default=None,
        description="Request that has been selected for rejection from admin (allows to write personalized reason)."
    )
    resolved_members: Dict[int, Union[PTBChatMember, PyroChatMember]] | None = Field(
        default_factory=dict,
        description="Members cache to avoid flood limit while resolving. Must be not in persistence."
    )
    resolved_users: Dict[int, Union[PTBUser, PyroUser]] | None = Field(
        default_factory=dict,
        description="Users cache to avoid flood limit while resolving. Must be not in persistence."
    )
    active_rejection_session: RequestRejectionSession | None = Field(
        default=None,
        description="Request rejection session"
    )
    # ======== Users ========


class ChatData(BaseModel):
    persistent: ChatDataPersistent = Field(default_factory=ChatDataPersistent)
    ephemeral: ChatDataEphemeral = Field(default_factory=ChatDataEphemeral)


class BotData(BaseModel):
    configuration: Configuration = Field(default_factory=Configuration)
    bot_version: str = "2.0.0"
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())

    group_chat_id: int | None = Field(default=None)
    staff_chat_id: int | None = Field(default=None)
    admins: Dict[int, str] = Field(default_factory=dict)
    ban_list: Dict[int, BanListItem] = Field(default_factory=dict)
    user_limitations: Dict[int, UserLimitations] = Field(default_factory=dict)
    user_request_cooldowns: Dict[int, RequestCooldown] = Field(default_factory=dict)
    pending_join_requests: Dict[str, float] = Field(default_factory=dict)

    commands: Dict[str, CommandConfig] = Field(default_factory=dict)
    hashtags: Dict[str, Any] = Field(default_factory=dict)
    rules_text: str = ""
    user_joined_message_text: str = ""
    channel_join_link: str = ""
    group_join_link: str = "https://example.com"

    active_requests: Dict[int, BaseRequest] = Field(default_factory=dict, exclude=True)
    jobs: Dict[str, JobInfo] = Field(default_factory=dict)
    last_auto_recap: datetime | None = None
    restart: RestartData = Field(default_factory=RestartData)

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",
        use_enum_values=True,
    )


# noinspection PyUnresolvedReferences,PyTypeChecker
class CustomContext(CallbackContext[ExtBot, BotData, dict, dict]):
    user_id: int | None
    chat_id: int | None

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
            chat_id: int | None = None,
            user_id: int | None = None
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
        self.pydc.persistent.root_path = base_path

    def free_base_path(self):
        self.pydc.persistent.root_path = None

    @property
    def user_active_requests(self) -> dict[int, BaseRequest]:
        return {ix: r for ix, r in self.pydb.active_requests.items() if (r.user_id == self.user_id)}

    def cancellable_requests(self, from_user: bool = False) -> dict[int, BaseRequest]:
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
                    (platform is None or r.section.platform == platform) and
                    (category is None or r.section.category == category)
            )
        }

    def get_user_requests_by_status(
            self,
            status: RequestStatus,
            platform: Platform | None = None,
            category: Category | None = None
    ) -> dict[int, BaseRequest]:
        return self.get_requests_by_status(status=status, platform=platform, category=category, from_user=True)

    def get_section_active_requests(
            self,
            section: RequestSection,
            from_user: bool = False
    ) -> dict[int, BaseRequest]:
        active_requests = self.pydb.active_requests if not from_user else self.user_active_requests
        return {
            ix: r for ix, r in active_requests.items()
            if r.section == section
        }

    def get_user_active_category_requests(
            self,
            section: RequestSection
    ) -> dict[int, BaseRequest]:
        return self.get_section_active_requests(section=section, from_user=True)

    def init_request_wizard_session(
            self,
            user_id: int,
            section: RequestSection,
            from_notification: bool,
            msg_id: int
    ) -> None:
        model = PLATFORM_CATEGORY_REGISTRY[section.platform][section.category].model
        fresh_draft = model.model_construct(user_id=user_id, section=section)  # model_construct: bypass check pydantic

        self.pydc.persistent.active_request_wizard = RequestWizardSession(
            draft=fresh_draft,
            requesting=fresh_draft.FLOW[0],
            from_notification=from_notification,
            request_msg_id=msg_id
        )

    def submit_request(self, request: BaseRequest):
        self.pydb.active_requests[request.id] = request

    def user_request_cooldown(self, user_id: int | None = None) -> RequestCooldown | None:
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

    def remove_user_request_cooldown(self, user_id: int) -> RequestCooldown | None:
        rc = self.pydb.user_request_cooldowns.pop(user_id, None)
        if not rc:
            log.warning("User does not have a current request cooldown.")
        return rc

    def get_user_limitations(self, user_id: int | None = None) -> UserLimitations | None:
        return self.pydb.user_limitations.get(user_id or self.user_id, None)

    def get_user_request_limitations(
            self,
            user_id: int | None = None
    ) -> list[RequestSectionLimitation] | None:
        user_limitations = self.get_user_limitations(user_id=user_id or self.user_id)
        if user_limitations:
            return user_limitations.requests
        return None

    def is_user_request_limited(
            self,
            section: RequestSection,
            user_id: int | None = None
    ) -> RequestSectionLimitation | None:
        """Esegue il double check e ritorna l'eventuale limitazione, oppure None se l'utente non è limitato."""

        self.check_user_request_limitations(user_id=user_id or self.user_id)
        ul = self.get_user_request_limitations()
        if ul:
            for l in ul:
                if l.section == section:
                    return l
        return None

    def get_or_create_limitation_wizard(
            self,
            initial_section: RequestSection | None = None,
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

    def get_or_create_reminder_wizard(self, source: Reminder | None = None) -> ReminderWizard:
        """
            Restituisce il wizard promemoria della chat corrente, creandolo se assente.

            `source` precarica i campi da un promemoria esistente (modifica) e vince
            sulla bozza in corso, a meno che non stia già compilando quello stesso
            promemoria. Per iniziare una creazione da capo, chiamare prima
            `clear_reminder_wizard()`.
            """
        wizard = self.pydc.persistent.active_reminder_wizard

        if source is not None and (wizard is None or wizard.reminder_id != source.id):
            wizard = ReminderWizard.from_reminder(source)
        elif wizard is None:
            wizard = ReminderWizard()
        else:
            return wizard

        self.pydc.persistent.active_reminder_wizard = wizard
        return wizard

    def clear_reminder_wizard(self) -> None:
        """Resetta il wizard promemoria."""
        self.pydc.persistent.active_reminder_wizard = None

    def clear_saved_path(self, clear_relative: bool = True) -> None:
        self.pydc.persistent.root_path = None
        if clear_relative:
            self.pydc.persistent.relative_path = None

    def set_user_request_limitations(self, user_id: int, limitations: list[RequestSectionLimitation]):
        if not self.get_user_limitations():
            self.pydb.user_limitations[user_id or self.user_id] = UserLimitations(requests=limitations)
        else:
            self.pydb.user_limitations[user_id or self.user_id].requests = limitations

    def check_user_request_limitations(self, user_id: int | None = None):
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

    async def edit_request_status(self, ix: int, status: RequestStatus, rejection_reason: str | None = None):
        status_value = status.value
        is_closing = status in (
            RequestStatus.CANCELLED, RequestStatus.REJECTED, RequestStatus.COMPLETED
        )
        closed_at = datetime.now(timezone.utc) if is_closing else None
        query = f"""UPDATE {REQUESTS_TABLE} SET status = $1, rejection_reason = $2, closed_at = $3 WHERE id = $4"""

        res = await execute_query(
            query=query,
            params=[
                status_value,
                rejection_reason,
                closed_at,
                int(ix)
            ]
        )
        if not res:
            log.error(f"Failed to update request {ix} status to '{status}'")
            return

        request = self.pydb.active_requests.get(ix, None)
        if request:
            request.edit_status(status=status, rejection_reason=rejection_reason, closed_at=closed_at)
        else:
            log.warning(f"Request {ix} not found in active request cache.")

        if status == RequestStatus.CANCELLED:
            self.remove_from_active_requests(ix=ix)
        elif status in (RequestStatus.COMPLETED, RequestStatus.REJECTED):
            from aimods_bot.src.helpers.job_queue import scheduled_remove_completed_requests
            job_name = f"remove_inactive_request:{ix}"
            job = self.job_queue.run_once(
                callback=scheduled_remove_completed_requests,
                when=SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE,
                data=RemoveCompletedRequestJob(request_id=int(ix)),
                name=job_name
            )
            self.pydb.jobs[job_name] = JobInfo(
                next_date=job.next_t,
                executed=False
            )

        log.info(f"Updated request {ix} status to '{status}'")

    # ======== SEZIONI RICHIESTE ========

    def is_request_section_open(self, section: RequestSection) -> bool | None:
        platform = section.platform
        category = section.category
        category_config = PLATFORM_CATEGORY_REGISTRY[platform][category]
        platform_section_settings = getattr(self.pydb.configuration.settings.request, platform, None)
        if platform_section_settings is None:
            log.error(f"Platform {platform.label} configuration not found.")
            return None
        category_section_settings = getattr(platform_section_settings, category, None)
        if category_section_settings is None:
            log.error(f"Category {category_config.label} configuration not found inside {platform.label}.")
            return None

        assert isinstance(category_section_settings, CategorySetting)
        return category_section_settings.toggle
