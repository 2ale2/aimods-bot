from functools import wraps
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime

from aimods_bot.src.core.logger import logger

log = logger.getChild("pydantic")


class JobInfo(BaseModel):
    next_date: str
    executed: bool = False


class BotData(BaseModel):
    configuration: Dict[str, Any]
