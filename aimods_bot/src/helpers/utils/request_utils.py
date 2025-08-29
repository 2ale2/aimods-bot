import json
import platform as platf
from datetime import datetime, timezone
from typing import Optional, Literal, AsyncIterator, Iterable, Text
from pathlib import Path

from telegram.ext import ContextTypes
from aimods_bot.src.core.exceptions import MissingParameterException, DatabaseBotException
from aimods_bot.src.helpers.constants.constants import REQUEST_STATUS_DETAILS, PLATFORM_DETAILS
from aimods_bot.src.helpers.constants.models import RequestStatus, RequestData, Platform, AndroidCategory, \
    WindowsCategory, IOSCategory, MacOSCategory, Category
from aimods_bot.src.helpers.database import fetch_query, execute_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import tex_escape, create_latex_file, convert_latex_to_pdf
from aimods_bot.src.helpers.utils.time_utils import format_time_as_rome

log = logger.getChild("request_utils")


def get_platform_categories(platform: Platform):
    categories = {
        Platform.ANDROID: AndroidCategory,
        Platform.WINDOWS: WindowsCategory,
        Platform.IOS: IOSCategory,
        Platform.MACOS: MacOSCategory
    }
    return categories[platform]


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


def get_request_by_id(context: ContextTypes.DEFAULT_TYPE, ix: str):
    request_dict = context.bot_data["active_requests"].get(ix)
    request_dict["id"] = ix
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
            raise ValueError(f"Richiesta {ix} non trovata.")

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
    """Utility Function per trasformare un Record del database in un'istanza di RequestData.
    Questa funzione si rompe se la struttura della tabella requests viene modificata."""
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


def get_requests_summary(requests: dict[str, RequestData]) -> str:
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


async def get_request_details(request: RequestData, admin: bool = False):
    text = ""
    if admin:
        if request.id:
            text += f"      #️⃣ <u>ID</u> – <code>{request.id}</code>\n"
        if request.user_id:
            text += f"      👤 <u>User ID</u> – <code>#{request.user_id}</code>\n"
        text += "\n"

    text += f"     🔸 <u>Nome</u> – <i>{request.name}</i>\n"
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
        text += f"\n      <b><u>Status</u></b> – {icon} <i>{label}</i>\n"

    return text


def get_active_category_requests(
        context: ContextTypes.DEFAULT_TYPE,
        platform: Platform,
        category: Category
):
    requests = {}
    active = context.bot_data["active_requests"]
    for el in active:
        request = active[el]
        if request.get("platform") == platform.value and request.get("category") == category.value:
            requests[el] = RequestData.from_dict(data=request)
    return requests


async def generate_user_archive_requests_pdf_file(requests: list[RequestData], input_path: str) -> str:
    input_path = str(Path(input_path).with_suffix(".tex"))
    tex_p = await generate_user_archive_requests_latex_file(requests=requests, out_path=input_path)
    pdf_p = await convert_latex_to_pdf(tex_path=tex_p)
    return pdf_p


async def generate_user_archive_requests_latex_file(requests: list[RequestData], out_path: str) -> str:
    p = await create_latex_file(out_path, iter_archive_tex(requests))
    return str(p)


async def iter_archive_tex(requests: Iterable[RequestData]) -> AsyncIterator[Text]:
    yield render_requests_latex_header()
    for r in requests:
        yield render_request_latex_item(r)
    yield render_requests_latex_footer()


def render_request_latex_item(r: RequestData) -> str:
    lines = [rf"\item\begin{{minipage}}[t]{{\linewidth}}\raggedright"]

    PLATFORM_LATEX_EMOJIS = {
        "android": "robot",
        "windows": "laptop",
        "ios": "green-apple",
        "macos": "desktop-computer"
    }

    STATUS_COLORS = {
        "pending": "orange",
        "examining": "linkblue",
        "testing": "teal",
        "completed": "green!60!black",
        "rejected": "red",
        "cancelled": "statusgrey"
    }

    STATUS_LATEX_EMOJIS = {
        "pending": "hourglass-not-done",
        "examining": "magnifying-glass-tilted-right",
        "testing": "test-tube",
        "completed": "check-mark-button",
        "rejected": "cross-mark",
        "cancelled": "wastebasket"
    }

    if r.name:
        lines.append(rf"\underline{{\textbf{{Nome}}}} – {tex_escape(r.name)} \\")
    if r.platform:
        icon = PLATFORM_LATEX_EMOJIS[r.platform.value]
        label = PLATFORM_DETAILS[r.platform.value]['label']
        lines.append(rf"\textbf{{Piattaforma}} – \emoji{{{icon}}} \textit{{{tex_escape(label)}}} \\")
    if r.link:
        lines.append(rf"\textbf{{Link}} – \href{{{r.link}}}{{\emoji{{link}} \textcolor{{linkblue}}{{Link}}}} \\")
    if r.version:
        lines.append(rf"\textbf{{Versione}} – \texttt{{{r.version}}} \\")
    if r.functionalities:
        lines.append(rf"\textbf{{Funzionalità}} – \textit{{{r.functionalities}}} \\")
    if r.issued_at:
        s = format_time_as_rome(until=r.issued_at).replace("<b>", "").replace("</b>", "")
        lines.append(rf"\textbf{{Data}} – {tex_escape(s)} \\")
    if r.status:
        icon = STATUS_LATEX_EMOJIS[r.status.value]
        label = REQUEST_STATUS_DETAILS[r.status.value]['label']
        color = STATUS_COLORS[r.status.value]
        lines.append(rf"\textbf{{Status}} – \emoji{{{icon}}} \textcolor{{{color}}}{{{tex_escape(label)}}} \\")

    lines.append(rf"\end{{minipage}}")
    return """ """.join(lines)


def render_requests_latex_header() -> str:
    s = platf.system()
    if s == "Windows":
        font = "Segoe UI Emoji"
    else:
        font = "Noto Color Emoji"
    return fr"""\documentclass[a4paper,12pt]{{article}}
    \usepackage{{fontspec}}
    \usepackage{{emoji}}
    \setemojifont{{{font}}}
    \usepackage{{multicol}}
    \usepackage{{enumitem}}
    \usepackage{{xcolor}}
    \usepackage{{url}}
    \usepackage[hidelinks]{{hyperref}}
    \Urlmuskip=0mu plus 1mu\relax
    \definecolor{{linkblue}}{{HTML}}{{1F63D1}}
    \definecolor{{statusgrey}}{{HTML}}{{383A3D}}

    \begin{{document}}
    \section*{{\emoji{{closed-book}} Archivio Richieste}}
    \emoji{{small-blue-diamond}} Ecco le richieste che hai formulato in passato in ordine cronologico.

    \begin{{multicols}}{{2}}
    \begin{{enumerate}}[leftmargin=0.5cm]
    """  # noqa: E501


def render_requests_latex_footer() -> str:
    return r"""\end{enumerate}
\end{multicols}
\end{document}
"""
