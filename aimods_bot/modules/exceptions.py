
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


class QueryException(DatabaseBotException):
    """Eccezione per gli errore nelle query del database."""
    def __init__(self, message="la query non è formulata correttamente", query=None, code=1001):
        self.message = message
        self.query = query
        self.code = code
        if self.query is None:
            super().__init__(self.message + f" ({self.code})", self.code)
        else:
            super().__init__(self.message + f" ({self.code}).\n\t{self.query}", self.code)


class AlertException(BotException):
    def __init__(self, message="mancano dei parametri nei dati della callback query", code=2000):
        super().__init__(message + f" ({code})")
        self.message = message
        self.code = code


class CommandSyntaxException(BotException):
    def __init__(self, command: str, code=3000):
        super().__init__(f"errore nella sintassi del comando: {command} ({code})")
        self.message = f"errore nella sintassi del comando: {command}"
        self.code = code

