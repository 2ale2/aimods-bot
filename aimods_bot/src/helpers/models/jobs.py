from __future__ import annotations

from dataclasses import dataclass
from typing import Union, List, Optional

import telegram
from telegram import InputMedia, InlineKeyboardMarkup, ReplyParameters


@dataclass
class JobData:
    files: Union[str, InputMedia, List[Union[str, InputMedia]]] = None
    message_id: Optional[int | telegram.Message] = None
    send_as_document: bool = False
    delete_after_sending: bool = False
    thread_id: Optional[int] = None
    reply_markup: Optional[InlineKeyboardMarkup] = None
    reply_parameters: Optional[ReplyParameters] = None
    delete_after: Optional[int] = None


@dataclass
class ScheduledJobData:
    chat_id: int
    text: Optional[str] = None
    additional_data: Optional[JobData] = None
