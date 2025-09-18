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
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, ConfigDict
from telegram.ext import CallbackContext, ExtBot, Application

from aimods_bot.src.core.pydantic import Configuration, JobInfo, RestartData, BanListItem, Request, CommandConfig, \
    RequestConversationFlowsConfig
from aimods_bot.src.helpers.constants.constants import RequestStatus
from aimods_bot.src.helpers.loggers import logger

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
    active_requests: List[Request] = Field(default_factory=list)
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
    def user_active_requests(self) -> list[Request]:
        user_active_requests = []
        active_requests = self.pyd.active_requests
        for request in active_requests:
            if (request.user_id == self.user_id and request.status
                    not in (RequestStatus.COMPLETED, RequestStatus.REJECTED, RequestStatus.CANCELLED)):
                user_active_requests.append(request)
        return user_active_requests
