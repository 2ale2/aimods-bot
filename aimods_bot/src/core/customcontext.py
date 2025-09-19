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

from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict
from telegram.ext import CallbackContext, ExtBot, Application

from aimods_bot.src.core.pydantic import Configuration, JobInfo, RestartData, BanListItem, Request, CommandConfig, \
    RequestConversationFlowsConfig
from aimods_bot.src.helpers.constants.constants import RequestStatus, SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.database import execute_query

log = logger.getChild("custom_context")


class BotData(BaseModel):
    configuration: Configuration = Field(default_factory=Configuration)
    group_chat_id: Optional[int] = None

    admins: Dict[int, str] = Field(default_factory=dict)
    ban_list: Dict[int, BanListItem] = Field(default_factory=dict)
    user_joined_message_text: str = ""
    rules_text: str = ""
    commands: Dict[str, CommandConfig] = Field(default_factory=dict)
    hashtags: Dict[str, Any] = Field(default_factory=dict)
    request_conversations_flows: RequestConversationFlowsConfig = Field(default_factory=RequestConversationFlowsConfig)
    active_requests: Dict[int, Request] = Field(default_factory=dict)
    jobs: Dict[str, JobInfo] = Field(default_factory=dict)
    bot_version: str = "1.0.0"
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
    restart: RestartData = Field(default_factory=RestartData)

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",
        use_enum_values=True
    )


# noinspection PyUnresolvedReferences
class CustomContext(CallbackContext[ExtBot, BotData, dict, dict]):
    user_id: Optional[int]
    chat_id: Optional[int]

    @property
    def pyd(self) -> BotData:
        # noinspection PyTypeChecker
        return self.bot_data

    def __init__(
            self,
            application: Application,
            chat_id: Optional[int] = None,
            user_id: Optional[int] = None,
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

    @property
    def user_active_requests(self) -> dict[int, Request]:
        return {ix: r for ix, r in self.pyd.active_requests.items() if (r.user_id == self.user_id)}

    def cancellable_requests(self, from_user: Optional[bool] = False) -> dict[int, Request]:
        timer_sec = self.pyd.configuration.settings.request.cancel_timer
        active_requests = self.pyd.active_requests if not from_user else self.user_active_requests
        return {rid: r for rid, r in active_requests.items() if r.can_be_cancelled(timer_sec)}

    @property
    def user_cancellable_requests(self) -> dict[int, Request]:
        return self.cancellable_requests(from_user=True)

    def get_active_request_by_id(self, ix: int):
        return self.pyd.active_requests.get(ix, None)

    def get_requests_by_status(
            self,
            status: RequestStatus,
            platform: Optional[Platform] = None,
            category: Optional[Category] = None,
            from_user: Optional[bool] = False
    ) -> dict[int, Request]:
        if status == RequestStatus.CANCELLED:
            log.warning("bot_data only contains active requests.")
            return {}
        requests = self.pyd.active_requests if not from_user else self.user_active_requests
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
            platform: Optional[Platform] = None,
            category: Optional[Category] = None
    ) -> dict[int, Request]:
        return self.get_requests_by_status(status=status, platform=platform, category=category, from_user=True)

    def get_active_category_requests(
            self,
            platform: Platform,
            category: Category,
            from_user: Optional[bool] = False
    ) -> dict[int, Request]:
        active_requests = self.pyd.active_requests if not from_user else self.user_active_requests
        return {
            ix: r for ix, r in active_requests.items()
            if r.platform == platform and category == r.category
        }

    def get_user_active_category_requests(
            self,
            platform: Platform,
            category: Category
    ) -> dict[int, Request]:
        return self.get_active_category_requests(platform=platform, category=category, from_user=True)

    def remove_from_active_requests(self, ix: int) -> bool:
        return bool(self.pyd.active_requests.pop(ix, None))

    async def edit_request_status(self, ix: int, status: RequestStatus):
        if status == RequestStatus.CANCELLED:
            self.remove_from_active_requests(ix=ix)
        elif status == RequestStatus.COMPLETED:
            from aimods_bot.src.helpers.job_queue import scheduled_remove_completed_requests
            self.job_queue.run_once(
                callback=scheduled_remove_completed_requests,
                when=SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE,
                data={"ix": ix}
            )

        request = self.pyd.active_requests.get(ix, None)
        if request:
            request.edit_status(status=status)
        log.warning(f"Request {ix} not found.")

        status_value = status.value
        query = """UPDATE requests \
                   SET status = $1 \
                   WHERE id = $2"""

        res = await execute_query(query=query, params=[status_value, int(ix)])
        if not res:
            log.error(f"Failed to update request {ix} status to '{status}'")
        else:
            log.info(f"Updated request {ix} status to '{status}'")
