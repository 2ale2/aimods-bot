import json
from typing import Optional, Literal, Dict, Any
from datetime import datetime, timezone

from telegram.ext import ContextTypes

from aimods_bot.src.core.exceptions import MissingParameterException
from aimods_bot.src.helpers.constants.constants import REQUEST_STATUS_DETAILS
from aimods_bot.src.helpers.constants.models import RequestStatus, Platform, AndroidCategory, WindowsCategory, \
    IOSCategory, MacOSCategory
from aimods_bot.src.helpers.database import fetch_query, execute_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import str_id_to_int
from aimods_bot.src.helpers.utils.time_utils import format_time_as_rome

log = logger.getChild("request_utils")


def flatten_requests_dict(requests: dict) -> Dict[int, Any]:
    """Trasforma un dizionario di dizionari di dizionari in un dizionario di dizionari."""

    if len(requests) == 0:
        return {}

    one_level = {}

    for pl in requests:
        if pl in ("android", "windows", "ios", "macos"):
            # platform -> category -> ix
            for cat in requests[pl]:
                one_level.update(requests[pl][cat])
        elif not isinstance(pl, int) and not pl.isdigit():
            # category -> ix
            one_level.update(requests[pl])
        else:
            # ix
            one_level.update({int(pl): requests[pl]})

    return one_level


def get_user_active_requests(
        context: ContextTypes.DEFAULT_TYPE,
        platform: Optional[Literal["android", "windows", "ios", "macos"]]
) -> dict:
    create_empty_request_user_data(context=context)
    if not platform:
        return context.user_data["active_requests"]
    return context.user_data["active_requests"][platform]


def get_user_active_requests_count(
        requests: Optional[dict],
        context: Optional[ContextTypes.DEFAULT_TYPE],
        platform: Optional[Literal["android", "windows", "ios", "macos"]]
) -> int:
    if requests is None and context is None:
        raise MissingParameterException("Se non specifichi 'requests', devi specificare 'context'.")

    if ((requests is not None and len(requests) == 0) or
            (requests is None and not context.user_data.get("active_requests", None))):
        return 0

    if requests is None:
        requests = get_user_active_requests(context=context, platform=platform)

    requests = flatten_requests_dict(requests=requests)

    return len(requests)


def get_active_requests(
        context: ContextTypes.DEFAULT_TYPE,
        platform: Optional[Literal["android", "windows", "ios", "macos"]]
) -> dict:
    if not platform:
        return context.bot_data["active_requests"]
    return context.bot_data["active_requests"][platform]


async def get_user_requests_by_status(
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


async def get_request_by_id(
        context: ContextTypes.DEFAULT_TYPE,
        ix: int
):
    ix = str_id_to_int(ix)
    requests = get_active_requests(context=context, platform=None)
    for el in requests:
        if ix in requests[el]:
            return requests[el][ix]

    query = "SELECT * FROM requests WHERE id = $1"

    res = await fetch_query(query=query, params=(ix,))

    if not res:
        log.error(f"No request with id {ix} found.")
        return None

    categories = {
        "android": AndroidCategory,
        "windows": WindowsCategory,
        "ios": IOSCategory,
        "macos": MacOSCategory
    }

    data = dict(res[0])
    request = json.loads(data['content'])
    # noinspection PyArgumentList
    request['status'] = data['status']
    request['platform'] = Platform(data['platform'])
    request['category'] = categories[data['platform']](data['category'])
    request['user_id'] = data['user_id']
    request['issued_at'] = data['issued_at']

    return requests


def create_empty_request_user_data(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("active_requests", {})


async def can_request_be_cancelled(context: ContextTypes.DEFAULT_TYPE, ix: int):
    ix = str_id_to_int(ix)
    query = """SELECT issued_at FROM requests WHERE id = $1"""

    response = await fetch_query(query=query, params=(ix,))

    issuing_time = dict(response[0])["issued_at"]
    cancel_timer_sec = context.bot_data["configuration"]["settings"]["request"]["cancel_timer"]

    if (datetime.now(timezone.utc) - issuing_time).total_seconds() > cancel_timer_sec:
        return False
    return True


async def get_requests_summary(
        context: ContextTypes.DEFAULT_TYPE,
        requests: dict,
        only_cancellable: bool = False
) -> str:
    text = ""

    requests = flatten_requests_dict(requests=requests)

    for n, el in enumerate(requests):
        request = requests[el]

        if only_cancellable and not await can_request_be_cancelled(context=context, ix=el):
            continue

        status = request['status']
        icon = REQUEST_STATUS_DETAILS[status]['icon']
        label = REQUEST_STATUS_DETAILS[status]['label']
        text += (f"    {n+1}. <i>{request['name']}</i>\n"
                 f"      🔧 <u>Stato</u> – {icon} <b><i>{label}</i></b>\n\n")

    return text


async def edit_request_status(context: ContextTypes.DEFAULT_TYPE, ix: int, status: RequestStatus):
    ix = str_id_to_int(ix)
    user_requests = get_user_active_requests(context=context, platform=None)
    bot_requests = get_user_active_requests(context=context, platform=None)

    user_requests = flatten_requests_dict(requests=user_requests)
    bot_requests = flatten_requests_dict(requests=bot_requests)

    user_requests.pop(ix, None)
    bot_requests.pop(ix, None)

    query = """UPDATE requests SET status = $1 WHERE id = $2"""

    res = await execute_query(query=query, params=(status.value, ix))
    if not res:
        log.error(f"Failed to update request {ix} status to '{status.value}'")

    log.info(f"Updated request {ix} status to '{status.value}'")


async def get_request_details(request: dict):
    text = f"     🔸 <u>Nome</u> – <i>{request['name']}</i>\n"
    if request.get('link', None):
        text += f"     🔸 <u>Link</u> – <a href=\"{request['link']}\">🔗 Link</a>\n"
    if request.get('version', None):
        text += f"     🔸 <u>Versione</u> – <code>{request['version']}</code>\n"
    if request.get('functionalities', None):
        text += f"     🔸 <u>Funzionalità</u> – <i>{request['functionalities']}</i>\n"
    if request.get('steamtools', None):
        text += f"     🔸 <u>SteamTools</u> - <i>{'Sì' if request['steamtools'] else 'No'}</i>\n"
    if request.get('issued_at', None):
        text += f"     🔸 <u>Data</u> – <i>{format_time_as_rome(datetime.fromisoformat(request['issued_at']))}</i>\n"

    if request.get('status', None):
        label = REQUEST_STATUS_DETAILS[request['status']]['label']
        icon = REQUEST_STATUS_DETAILS[request['status']]['icon']
        text += f"\n<b><u>Status</u></b> – {icon} <i>{label}</i>"

    return text
