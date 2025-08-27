import json
from datetime import datetime, timezone
from typing import Optional, Literal

from telegram.ext import ContextTypes
from unicodedata import category

from aimods_bot.src.core.exceptions import MissingParameterException, DatabaseBotException
from aimods_bot.src.helpers.constants.constants import REQUEST_STATUS_DETAILS, PLATFORM_DETAILS
from aimods_bot.src.helpers.constants.models import RequestStatus, RequestData, Platform, Category, AndroidCategory, \
    WindowsCategory, IOSCategory, MacOSCategory
from aimods_bot.src.helpers.database import fetch_query, execute_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.time_utils import format_time_as_rome

log = logger.getChild("request_utils")


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


def get_request_by_id(
        context: ContextTypes.DEFAULT_TYPE,
        ix: str
):
    request_dict = context.bot_data["active_requests"].get(ix)

    if request_dict is None:
        request_dict = context.bot_data["active_requests"].get(str(ix))

    return RequestData.from_dict(request_dict)


def create_empty_request_user_data(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault("active_requests", {})


async def can_request_be_cancelled(
        context: ContextTypes.DEFAULT_TYPE,
        ix: Optional[int] = None,
        request: Optional[RequestData] = None
):
    if ix is None and request is None:
        raise MissingParameterException("Se ometti 'request', devi fornire 'context' e 'ix'.")

    if request is None:
        request = get_request_by_id(context=context, ix=ix)
        if not request:
            raise ValueError(f"Request {ix} not found.")

    if isinstance(request, dict):
        request = RequestData.from_dict(request)

    cancel_timer_sec = context.bot_data["configuration"]["settings"]["request"]["cancel_timer"]

    if (datetime.now(timezone.utc) - request.issued_at).total_seconds() > cancel_timer_sec:
        return False
    return True


async def get_user_requests_archive(user_id: int) -> list[dict]:
    """Interroga il db per ottenere le richieste formulate da un certo utente."""
    query = """SELECT * FROM requests WHERE user_id = $1 ORDER BY id"""
    response = await fetch_query(query=query, params=(user_id,))
    return [dict(r) for r in response]


async def request_data_from_record(request: dict) -> RequestData:
    query = """SELECT column_name 
               FROM information_schema.columns 
               WHERE columns.table_schema = 'public' AND table_name = 'requests';"""
    response = await fetch_query(query=query)

    if not response:
        raise DatabaseBotException("Errore nel fatch delle colonne dalla tabella 'requests'")

    response = [dict(c)['column_name'] for c in response]

    if any(k not in request for k in response):
        raise MissingParameterException("La struttura del dizionario non corrisponde alla struttura del DB nella "
                                        "tabella delle richieste.")

    categories = {
        "android": AndroidCategory,
        "windows": WindowsCategory,
        "ios": IOSCategory,
        "macos": MacOSCategory
    }

    raw_id = str(request["id"])
    raw_platform = request["platform"]
    raw_category = request["category"]
    user_id = request["user_id"]
    raw_status = request["status"]
    issued_at = request["issued_at"]
    raw_content = request["content"]

    platform = Platform(raw_platform) if raw_platform else None
    category = categories[raw_platform](raw_category) if raw_category and raw_platform else None
    # noinspection PyArgumentList
    status = RequestStatus(raw_status) if raw_status else None
    content = json.loads(raw_content) if raw_content else None
    name = link = version = functionalities = steamtools = None
    if content:
        name = content.get("name", None)
        link = content.get("link", None)
        version = content.get("version", None)
        functionalities = content.get("functionalities", None)
        steamtools = content.get("steamtools", None)

    return RequestData(
        id=raw_id,
        platform=platform,
        category=category,
        user_id=user_id,
        status=status,
        issued_at=issued_at,
        name=name,
        link=link,
        version=version,
        functionalities=functionalities,
        steamtools=steamtools,
        requesting=None,
        editing=None
    )


async def get_user_cancellable_requests(context: ContextTypes.DEFAULT_TYPE) -> dict[int, RequestData]:
    """Ritorna le richieste attive cancellabili"""
    user_requests = context.user_data["active_requests"]
    cancellable_requests = {}

    for el in user_requests:
        request = RequestData.from_dict(user_requests[el])
        if await can_request_be_cancelled(request=request, context=context):
            cancellable_requests[el] = request

    return cancellable_requests


async def get_requests_summary(requests: dict[int, RequestData]) -> str:
    text = ""

    for n, el in enumerate(requests):
        request = requests[el]
        
        if isinstance(request, dict):
            request = RequestData.from_dict(data=request)            

        status = request.status.value
        status_icon = REQUEST_STATUS_DETAILS[status]['icon']
        status_label = REQUEST_STATUS_DETAILS[status]['label']
        platform = request.platform.value
        platform_label = PLATFORM_DETAILS[platform]['label']
        platform_icon = PLATFORM_DETAILS[platform]['icon']

        text += (f"    {n+1}. <i>{request.name}</i>\n"
                 f"         🖲️ <u>Piattaforma</u> – {platform_icon} <i>{platform_label}</i>\n"
                 f"         🔧 <u>Stato</u> – {status_icon} <b><i>{status_label}</i></b>\n")

    return text


async def edit_request_status(context: ContextTypes.DEFAULT_TYPE, ix: str, status: RequestStatus):
    user_requests = context.user_data["active_requests"]
    bot_requests = context.bot_data["active_requests"]

    if status == RequestStatus.CANCELLED:
        user_requests.pop(ix, None)
        bot_requests.pop(ix, None)
    else:
        user_requests[ix].status = status
        bot_requests[ix].status = status
        context.user_data["active_requests"] = user_requests
        context.bot_data["active_requests"] = bot_requests

    query = """UPDATE requests SET status = $1 WHERE id = $2"""

    res = await execute_query(query=query, params=(status.value, int(ix)))
    if not res:
        log.error(f"Failed to update request {ix} status to '{status.value}'")
    else:
        log.info(f"Updated request {ix} status to '{status.value}'")


async def get_request_details(request: RequestData):
    text = f"     🔸 <u>Nome</u> – <i>{request.name}</i>\n"
    if request.platform:
        item = PLATFORM_DETAILS[request.platform.value]
        label = item['label']
        icon = item['icon']
        text += f"     🔸️ <u>Piattaforma</u> – {icon} <i>{label}</i>\n"
    if request.link:
        text += f"     🔸 <u>Link</u> – <a href=\"{request.link}\">🔗 Link</a>\n"
    if request.version:
        text += f"     🔸 <u>Versione</u> – <code>{request.version}</code>\n"
    if request.functionalities:
        text += f"     🔸 <u>Funzionalità</u> – <i>{request.functionalities}</i>\n"
    if request.steamtools is not None:
        text += f"     🔸 <u>SteamTools</u> - <i>{'Sì' if request.steamtools else 'No'}</i>\n"
    if request.issued_at:
        text += f"     🔸 <u>Data</u> – <i>{format_time_as_rome(request.issued_at)}</i>\n"

    if request.status:
        label = REQUEST_STATUS_DETAILS[request.status.value]['label']
        icon = REQUEST_STATUS_DETAILS[request.status.value]['icon']
        text += f"\n     <b><u>Status</u></b> – {icon} <i>{label}</i>\n"

    return text
