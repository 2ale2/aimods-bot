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
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, ValidationError
from telegram.ext import CallbackContext, ExtBot, Application

from aimods_bot.src.core.pydantic import Configuration, JobInfo
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
    jobs: Dict[str, JobInfo] = Field(default_factory=dict)
    bot_version: str = "1.0.0"
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())

    class Config:
        validate_assignment = True
        extra = "allow"


def with_bot_data(
        auto_init: bool = True
):
    """Al momento il decoratore può solo essere usato da funzioni che richiedono update e context come parametri.
    Per renderlo più flessibile si può agire dinamicamente su di esso in base ai paramatri che una funzione possiede.
    Sino a quando non si presenta l'eventualità, non lo farò."""

    def decorator(func):
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        @wraps(func)
        async def async_wrapper(update, context: CustomContext, *args, **kwargs):
            try:
                if auto_init and not context.bot_data:
                    context.pydantic_bot_data = BotData()

                context.pydantic_bot_data = BotData(**context.bot_data)
                if "update" in params:
                    return await func(update, context, *args, **kwargs)
                else:
                    return await func(context, *args, **kwargs)
            except ValidationError as e:
                log.error(f"Errore nella validazione di bot_data in {func.__name__}: {e}")
                raise
            except Exception as e:
                log.error(f"Errore imprevisto in {func.__name__}: {e}")
                raise

        @wraps(func)
        def sync_wrapper(update, context: CustomContext, *args, **kwargs):
            try:
                if auto_init and not context.bot_data:
                    context.pydantic_bot_data = BotData()

                context.pydantic_bot_data = BotData(**context.bot_data)

                if "update" in params:
                    return func(update, context, *args, **kwargs)
                else:
                    return func(context, *args, **kwargs)
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
