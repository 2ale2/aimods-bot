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

import inspect
from datetime import datetime
from functools import wraps
from typing import Optional, Dict, Any, Literal, List

from pydantic import BaseModel, Field, ValidationError
from telegram import Update
from telegram.ext import CallbackContext, ExtBot, Application

from aimods_bot.src.core.exceptions import MissingParameterException
from aimods_bot.src.core.pydantic import Configuration, JobInfo, RestartData, BanListItem, Request, CommandConfig, RequestConversationFlowsConfig
from aimods_bot.src.helpers.constants.models import RequestStatus
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("custom_context")


class CustomContext(CallbackContext[ExtBot, dict, dict, dict]):

    def __init__(
            self,
            application: Application,
            chat_id: Optional[int] = None,
            user_id: Optional[int] = None,
    ):
        super().__init__(application=application, chat_id=chat_id, user_id=user_id)
        self.pydantic_bot_data: Optional[BotData] = None
        self.is_user_admin: bool = False
        self.user_active_requests: Optional[List[Request]] = None


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

    class Config:
        validate_assignment = True
        extra = "allow"


def with_bot_data(
        auto_init: bool = True,
        param_name: str = "pydantic_bot_data",
):
    """Al momento il decoratore può solo essere usato da funzioni che richiedono update e context come parametri.
    Per renderlo più flessibile si può agire dinamicamente su di esso in base ai paramatri che una funzione possiede.
    Sino a quando non si presenta l'eventualità, non lo farò."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            context = None
            update = None
            for arg in args:
                if isinstance(arg, (CustomContext, CallbackContext, Application)):
                    context = arg
                elif isinstance(arg, Update):
                    update = arg
                if context and update:
                    break
            if context is None:
                context = kwargs.get("context", None)
            if context is None:
                raise MissingParameterException("You must provide a context.")
            if update is None:
                raise MissingParameterException("You must provide an update.")

            raw_bot_data = getattr(context, "bot_data", None)

            try:
                if auto_init and not raw_bot_data:
                    raw_bot_data = BotData().model_dump()
                    context.bot_data = raw_bot_data

                pydantic_bot_data = BotData(**raw_bot_data)

                if isinstance(context, CustomContext):
                    context.pydantic_bot_data = pydantic_bot_data
                else:
                    kwargs[param_name] = pydantic_bot_data

            except ValidationError as e:
                log.error(f"Errore nella validazione di bot_data in {func.__name__}: {e}")
                raise
            except Exception as e:
                log.error(f"Errore imprevisto in {func.__name__}: {e}")
                raise

            user_id = update.effective_user.id

            # ======== TIPO UTENTE ========
            if user_id in list(context.pydantic_bot_data.admins.keys()):
                context.is_user_admin = True

            # ======== RICHIESTE ATTIVE DELL'UTENTE ========
            user_active_requests = []
            for ix in pydantic_bot_data.active_requests:
                request = pydantic_bot_data.active_requests[ix]
                if (request.user_id == user_id and request.status not in
                        (RequestStatus.COMPLETED, RequestStatus.CANCELLED, RequestStatus.REJECTED)):
                    user_active_requests.append(request)

            context.user_active_requests = user_active_requests

            return await func(*args, **kwargs)


        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            context = None
            for arg in args:
                if isinstance(arg, (CustomContext, CallbackContext, Application)):
                    context = arg
                    break
            if context is None:
                context = kwargs.get("context", None)
            if context is None:
                raise MissingParameterException("You must provide a context.")

            raw_bot_data = getattr(context, "bot_date", None)

            try:
                if auto_init and not raw_bot_data:
                    raw_bot_data = BotData().model_dump()
                    context.bot_data = raw_bot_data

                pydantic_bot_data = BotData(**raw_bot_data)

                if isinstance(context, CustomContext):
                    context.pydantic_bot_data = pydantic_bot_data
                else:
                    kwargs[param_name] = pydantic_bot_data

                return func(*args, **kwargs)
            except ValidationError as e:
                log.error(f"Errore nella validazione di bot_data in {func.__name__}: {e}")
                raise
            except Exception as e:
                log.error(f"Errore imprevisto in {func.__name__}: {e}")
                raise

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
