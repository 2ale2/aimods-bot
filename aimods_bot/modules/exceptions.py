from loggers import bot_logger

class BotException(Exception):
    def __init__(self, message="si è verificato un errore."):
        super().__init__(message)
        self.message = message


class DatabaseBotException(BotException):
    """Eccezione per gli errori nel database."""
    def __init__(self, message="si è verificato un errore nel database.", code=None):
        super().__init__(message)
        self.message = message
        self.code = code


class ConfigValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        message = f"Configuration validation failed with {len(errors)} error(s)."
        super().__init__(message)


def handle_validation_errors(errors: list[str]):
    if errors:
        for err in errors:
            bot_logger.error(err)
        raise ConfigValidationError(errors)