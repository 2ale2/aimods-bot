from typing import Optional, Literal
from datetime import datetime

from telegram.ext import ContextTypes

from aimods_bot.src.helpers.constants.models import RequestStatus
from aimods_bot.src.helpers.database import fetch_query


def get_user_requests(
        context: ContextTypes.DEFAULT_TYPE,
        platform: Optional[Literal["android", "windows", "ios", "macos"]]
) -> dict:
    if not platform:
        return context.user_data["active_requests"]
    return context.user_data["active_requests"][platform]


async def get_user_request_by_status(
        user_id: int,
        platform: Optional[Literal["android", "windows", "ios", "macos"]],
        status: RequestStatus
) -> dict:
    query = """SELECT * 
               FROM requests 
               WHERE user_id = $1 
                 AND status = $2"""
    params = (user_id, status.value)

    if platform:
        query += f" AND platform = $3"
        params = params + (platform,)

    response = await fetch_query(query=query, params=params)

    return response


def create_empty_request_user_data(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("requests", {
            "android": {
                "app": {}
            },
            "windows": {
                "game": {},
                "software": {},
                "adobe": {},
                "daw": {}
            },
            "ios": {
                "app": {}
            },
            "macos": {
                "software": {},
                "daw": {}
            }
        })


async def can_request_be_cancelled(context: ContextTypes.DEFAULT_TYPE, ix: int):
    query = """SELECT issued_at FROM requests WHERE id = $1"""

    response = await fetch_query(query=query, params=ix)

    issuing_time = dict(response[0])["issued_at"]
    cancel_timer_sec = context.bot_data["configuration"]["settings"]["request"]["cancel_timer"]

    if (datetime.now() - issuing_time).total_seconds() > cancel_timer_sec:
        return False
    return True
