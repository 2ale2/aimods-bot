from dataclasses import dataclass, field

from telegram import InputMedia, InlineKeyboardMarkup, ReplyParameters


@dataclass
class SendMessageJob:
    """Payload per un job di invio messaggio."""
    chat_id: int
    text: str | None = None
    files: list[InputMedia | str] = field(default_factory=list)
    send_as_document: bool = False  # upload non compresso
    delete_after_sending: bool = False  # cancella i file locali dopo l'upload
    thread_id: int | None = None
    reply_markup: InlineKeyboardMarkup | None = None
    reply_parameters: ReplyParameters | None = None
    delete_after: int | None = None  # timer cancellazione msg inviato


@dataclass
class EditMessageJob:
    """Payload per un job di modifica messaggio."""
    chat_id: int
    message_id: int
    text: str
    reply_markup: InlineKeyboardMarkup | None = None


@dataclass
class DeleteMessageJob:
    """Payload per un job di eliminazione messaggio."""
    chat_id: int
    message_id: int
