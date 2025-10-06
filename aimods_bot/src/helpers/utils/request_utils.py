import json
import platform as platf
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Iterable, Text

from aimods_bot.src.core.exceptions import MissingParameterException, DatabaseBotException
from aimods_bot.src.core.pydantic import Request, Architecture
from aimods_bot.src.helpers.constants.constants import REQUEST_STATUS_DETAILS, PLATFORM_DETAILS, \
    Platform, WindowsCategory, AndroidCategory, IOSCategory, \
    MacOSCategory, Arch, RequestStatus
from aimods_bot.src.helpers.database import fetch_query
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


async def get_user_requests_archive(user_id: int) -> list[Request]:
    """Interroga il db per ottenere le richieste formulate da un certo utente."""
    query = """SELECT * FROM requests WHERE user_id = $1 ORDER BY id"""
    response = await fetch_query(query=query, params=[user_id])
    return [await request_from_record(dict(el)) for el in response]


async def request_from_record(request: dict) -> Request:
    """Utility Function per trasformare un Record del database in un'istanza di Request."""

    query = """SELECT column_name 
               FROM information_schema.columns 
               WHERE columns.table_schema = 'public' AND table_name = 'requests';"""
    response = await fetch_query(query=query)

    if not response:
        raise DatabaseBotException("Errore nel fetch delle colonne dalla tabella 'requests'")

    response = [dict(c)['column_name'] for c in response]

    if any(k not in request for k in response):
        raise MissingParameterException("La struttura del dizionario non corrisponde alla struttura del DB nella "
                                        "tabella delle richieste.")

    raw_id = request.get("id", None)
    raw_platform = request.get("platform", None)
    raw_category = request.get("category", None)
    user_id = request.get("user_id", None)
    raw_status = request.get("status", None)
    issued_at = request.get("issued_at", None)
    raw_rejection_reason = request.get("rejection_reason", None)
    raw_content = request.get("content", None)

    assert isinstance(issued_at, datetime)

    platform = Platform(raw_platform) if raw_platform else None
    if raw_platform and raw_category:
        category = get_platform_categories(Platform(platform))(raw_category)
    else:
        category = None

    # noinspection PyArgumentList
    status = RequestStatus(raw_status) if raw_status else None
    # noinspection PyTypeChecker
    content = json.loads(raw_content) if raw_content else None
    name = link = version = functionalities = steamtools = arch = None
    if content:
        name = content.get("name", None)
        link = content.get("link", None)
        version = content.get("version", None)
        functionalities = content.get("functionalities", None)
        steamtools = content.get("steamtools", None)
        arch = content.get("arch", None)
        if arch:
            a = arch.get("arch", None)
            if not a:
                log.error("Dumped Arch instance should be a dict containing an 'arch' key")
                arch = None
            else:
                arch = Architecture(arch=Arch(arch.get("arch", None)))

    # noinspection PyTypeChecker
    return Request(
        id=raw_id,
        user_id=user_id,
        status=status,
        issued_at=issued_at.isoformat(),
        platform=platform,
        category=category,
        name=name,
        arch=arch,
        link=link,
        version=version,
        functionalities=functionalities,
        steamtools=steamtools,
        rejection_reason=raw_rejection_reason
    )


def get_requests_summary(requests: dict[int, Request]) -> str:
    text = ""

    for n, ix in enumerate(requests):
        request = requests[ix]
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


async def get_request_details(request: Request, admin: bool = False):
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
        text += f"     🔸 <u>SteamTools</u> - <i>{'✔️' if request.steamtools else '✖️'}</i>\n"
    if request.issued_at:
        text += f"     🔸 <u>Data</u> – <i>{format_time_as_rome(datetime.fromisoformat(request.issued_at))}</i>\n"
    if request.arch:
        text += f"     🔸 <u>CPU ARM</u> – <i>{'✔️' if request.arch.arm_bool else '✖️'}</i>\n"

    if request.status:
        label = REQUEST_STATUS_DETAILS[request.status.value]['label']
        icon = REQUEST_STATUS_DETAILS[request.status.value]['icon']
        text += f"\n      <b><u>Status</u></b> – {icon} <i>{label}</i>\n"
        if request.status == RequestStatus.REJECTED:
            text += f"      <b><u>Motivazione</u></b> – {request.rejection_reason}\n"

    return text


async def generate_user_archive_requests_pdf_file(requests: list[Request], input_path: str) -> str:
    input_path = str(Path(input_path).with_suffix(".tex"))
    tex_p = await generate_user_archive_requests_latex_file(requests=requests, out_path=input_path)
    pdf_p = await convert_latex_to_pdf(tex_path=tex_p)
    return str(pdf_p)


async def generate_user_archive_requests_latex_file(requests: list[Request], out_path: str) -> str:
    p = await create_latex_file(out_path, iter_archive_tex(requests))
    return str(p)


async def iter_archive_tex(requests: Iterable[Request]) -> AsyncIterator[Text]:
    yield render_requests_latex_header()
    for r in requests:
        yield render_request_latex_item(r)
    yield render_requests_latex_footer()


def render_request_latex_item(r: Request) -> str:
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
        s = format_time_as_rome(until=datetime.fromisoformat(r.issued_at)).replace("<b>", "").replace("</b>", "")
        lines.append(rf"\textbf{{Data}} – {tex_escape(s)} \\")
    if r.status:
        icon = STATUS_LATEX_EMOJIS[r.status.value]
        label = REQUEST_STATUS_DETAILS[r.status.value]['label']
        color = STATUS_COLORS[r.status.value]
        lines.append(rf"\textbf{{Status}} – \emoji{{{icon}}} \textcolor{{{color}}}{{{tex_escape(label)}}} \\")

    if r.rejection_reason:
        rejection_text = rf"\textbf{{Motivo}} – \textit{{{r.rejection_reason}}}"
    else:
        rejection_text = rf"\textbf{{Motivo}} – \texttt{{None}}"
    lines.append(rf"{rejection_text} \\")

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
