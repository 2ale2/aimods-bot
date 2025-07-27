from typing import Any

from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("exceptions")


class BotException(Exception):
    """Eccezione base per tutte le eccezioni del bot."""
    def __init__(self, message: str = "Si è verificato un errore generico."):
        super().__init__(message)


# ========== DATABASE ==========
class DatabaseBotException(BotException):
    """Errore durante le operazioni col database."""
    def __init__(self, message: str = "Errore nel database.", code: int = None):
        self.code = code
        super().__init__(message)


# ========== JOBQUEUE ==========
class JobDataMissingException(BotException):
    """Informazioni mancanti nei dati del Job"""
    def __init__(self, message: str = "Dati mancanti nel job.", code: int = None):
        self.code = code
        super().__init__(message)


class WrongTypeException(BotException):
    """La variabile non è del tipo corretto."""
    def __init__(self, variable: Any, variabile_name: str, should_be: str):
        self.variabile_name = variabile_name
        self.variable = variable
        self.should_be = should_be
        message = f"La variabile '{variabile_name}' è di tipo {type(variable)}, ma dovrebbe essere di tipo {should_be}."
        super().__init__(message)

# ========== CONFIGURAZIONE ==========
class ConfigValidationException(BotException):
    """Errore nella validazione della configurazione."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        message = f"Validazione configurazione fallita con {len(errors)} errore(i)."
        super().__init__(message)


class ConfigError(Exception):
    def __init__(self, errors):
        self.errors = errors
        message = f"Configuration validation failed with {len(errors)} error(s)."
        super().__init__(message)


# ========== CONFIGURAZIONE ==========
class CallbackDataException(BotException):
    """Errore nella struttura dei dati di callback."""
    def __init__(self, callback_data: str, should_be=None):
        self.callback_data = callback_data
        message = (f"Struttura dei dati di callback '{callback_data}' errata"
                   f"{f'. Dovrebbe essere: {should_be}' if should_be else '.'}")
        super().__init__(message)


class MissingConfigurationException(BotException):
    """Configurazione mancante (inesistente o con sintassi errata)."""
    def __init__(self, what: str):
        self.what = what
        message = f"Configurazione mancante o con sintassi errata per l'elemento '{what}'."
        super().__init__(message)


class UserMentionException(BotException):
    """Non si hanno abbastanza elementi per creare una menzione testuale dell'utente."""
    def __init__(self):
        message = f"Non è possibile formulare una menzione senza username o user ID."
        super().__init__(message)


class MissingParameterException(BotException):
    """Ci sono alcune funzioni in cui almeno uno dei parametri falcoltativi deve essere presente."""
    def __init__(self, explanation: str):
        self.explanation = explanation
        super().__init__(explanation)


def handle_validation_errors(errors: list[str]):
    """
    Logga e solleva eccezione se presenti errori nella validazione della configurazione.
    """
    if errors:
        for err in errors:
            log.error(f"[ConfigValidation] {err}")
        raise ConfigValidationException(errors)


# ========== TELEGRAM / CALLBACK ==========
class TelegramDataException(BotException):
    """Errore nei dati ricevuti da Telegram."""
    pass


# ========== PERMESSI / SICUREZZA ==========
class UnauthorizedAccessException(BotException):
    """L'utente non ha i permessi per eseguire l'azione richiesta."""
    pass
