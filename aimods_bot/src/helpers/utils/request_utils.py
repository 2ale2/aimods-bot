import json
import platform as platf
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Iterable, Text, Optional, Union

from pydantic import BaseModel, ValidationError, field_validator

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import Request, Architecture, CategorySetting
from aimods_bot.src.helpers.constants.constants import REQUEST_STATUS_DETAILS, PLATFORM_DETAILS, \
    Platform, WindowsCategory, AndroidCategory, IOSCategory, \
    MacOSCategory, Arch, RequestStatus, Category, CATEGORY_DETAILS
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import tex_escape, create_latex_file, convert_latex_to_pdf
from aimods_bot.src.helpers.utils.time_utils import format_time_as_rome

log = logger.getChild("request_utils")


class RequestContent(BaseModel):
    name: Optional[str] = None
    link: Optional[str] = None
    version: Optional[str] = None
    functionalities: Optional[str] = None
    steamtools: Optional[bool] = None
    arch: Optional[dict] = None

    @field_validator('arch')
    def validate_arch(cls, v):
        if v is None:
            return None
        if not isinstance(v, dict) or 'arch' not in v:
            log.error("Dumped Arch instance should be a dict containing an 'arch' key")
            return None
        try:
            return Architecture(arch=Arch(v['arch']))
        except (ValueError, KeyError) as e:
            log.error(f"Invalid arch structure: {e}")
            return None


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
    query = """SELECT * \
               FROM requests \
               WHERE user_id = $1 \
               ORDER BY id"""
    response = await fetch_query(query=query, params=[user_id])

    if not response:
        return []

    return [await request_from_record(dict(el)) for el in response]


async def request_from_record(request: dict) -> Request:
    """
    Utility Function per trasformare un Record del database in un'istanza di Request.
    """
    raw_id = request.get("id", None)
    raw_platform = request.get("platform", None)
    raw_category = request.get("category", None)
    user_id = request.get("user_id", None)
    raw_status = request.get("status", None)
    issued_at = request.get("issued_at", None)
    raw_rejection_reason = request.get("rejection_reason", None)
    raw_content = request.get("content", None)

    if not isinstance(issued_at, datetime):
        raise ValueError(f"Invalid issued_at type: {type(issued_at)}, expected datetime")

    platform = Platform(raw_platform) if raw_platform else None
    if raw_platform and raw_category:
        category = get_platform_categories(Platform(platform))(raw_category)
    else:
        category = None

    status = RequestStatus(raw_status) if raw_status else None

    content = RequestContent()
    if raw_content:
        try:
            content_dict = json.loads(raw_content)
            content = RequestContent(**content_dict)
        except (json.JSONDecodeError, ValidationError) as e:
            log.error(f"Failed to parse request content: {e}")
            content = RequestContent()

    return Request(
        id=raw_id,
        user_id=user_id,
        status=status,
        issued_at=issued_at.isoformat(),
        platform=platform,
        category=category,
        name=content.name or "",
        arch=content.arch,
        link=content.link or "",
        version=content.version or "",
        functionalities=content.functionalities or "",
        steamtools=content.steamtools,
        rejection_reason=raw_rejection_reason
    )


def get_requests_summary(requests: dict[int, Request], with_authors: bool = False) -> str:
    """
    Ritorna il sommario delle richieste nel dizionario.

    NOTA - L'ID è nella richiesta; perché non passo una lista di Request?
    """
    parts = []

    for n, ix in enumerate(requests):
        request = requests[ix]
        status = request.status.value
        status_icon = REQUEST_STATUS_DETAILS[status]['icon']
        status_label = REQUEST_STATUS_DETAILS[status]['label']
        platform = request.platform.value
        category = request.category.value
        category_label = CATEGORY_DETAILS[platform][category]['label']
        platform_icon = PLATFORM_DETAILS[platform]['icon']

        block = [
            f"    {n + 1}. <i>{request.name}</i>\n",
            f"         #️⃣ <u>ID</u> — <code>{request.id}</code>\n"
        ]

        if with_authors:
            block.append(f"         👤 <u>Formulata Da</u> — <code>{request.user_id}</code>\n")

        block.extend([
            f"         🖲️ <u>Piattaforma</u> — {platform_icon} {category_label}\n",
            f"         🔧 <u>Stato</u> — {status_icon} <b><i>{status_label}</i></b>\n\n"
        ])

        parts.append("".join(block))

    return "".join(parts).rstrip("\n")


async def get_request_details(request: Request, admin: bool = False):
    """
    Ritorna i dettagli di una richiesta.
    """
    parts = []

    if admin:
        if request.id:
            parts.append(f"      #️⃣ <u>ID</u> — <code>{request.id}</code>\n")
        if request.user_id:
            parts.append(f"      👤 <u>User ID</u> — <code>{request.user_id}</code>\n")
        parts.append("\n")

    parts.append(f"     🔸 <u>Nome</u> — <i>{request.name}</i>\n")

    if request.platform:
        item = PLATFORM_DETAILS[request.platform.value]
        label = item['label']
        icon = item['icon']
        parts.append(f"     🔸️ <u>Piattaforma</u> — {icon} <i>{label}</i>\n")

    if request.link:
        parts.append(f"     🔸 <u>Link</u> — <a href=\"{request.link}\">🔗 Link</a>\n")

    if request.version:
        parts.append(f"     🔸 <u>Versione</u> — <code>{request.version}</code>\n")

    if request.functionalities:
        parts.append(f"     🔸 <u>Funzionalità</u> — <i>{request.functionalities}</i>\n")

    if request.steamtools is not None:
        parts.append(f"     🔸 <u>SteamTools</u> - <i>{'✔️' if request.steamtools else '✖️'}</i>\n")

    if request.issued_at:
        parts.append(f"     🔸 <u>Data</u> — <i>{format_time_as_rome(datetime.fromisoformat(request.issued_at))}</i>\n")

    if request.arch:
        parts.append(f"     🔸 <u>CPU ARM</u> — <i>{'✔️' if request.arch.arm_bool else '✖️'}</i>\n")

    if request.status:
        label = REQUEST_STATUS_DETAILS[request.status.value]['label']
        icon = REQUEST_STATUS_DETAILS[request.status.value]['icon']
        parts.append(f"\n      <b><u>Status</u></b> — {icon} <i>{label}</i>\n")

        if request.status == RequestStatus.REJECTED:
            parts.append(f"      <b><u>Motivazione</u></b> — {request.rejection_reason}\n")

        if request.status == RequestStatus.COMPLETED and not admin:
            parts.append(
                "\n<blockquote>ℹ <b>Cosa Significa?</b> — Se una richiesta è <i>✅ Completata</i>, "
                "il post dell'app o del software richiesto è in programmazione. Per i software Windows "
                "e MacOS, <b>il rilascio sulle piattaforme avverrà assieme al post, oppure prima</b>.</blockquote>"
            )

    if request.status_change_notifications is not None and not admin and request.is_active:
        notification_text = (
            f"\n<blockquote>{'🔔 Riceverai' if request.status_change_notifications else '🔕 Non riceverai'} "
            "una notifica quando questa richiesta verrà chiusa.</blockquote>"
        )
        parts.append(notification_text)

    return "".join(parts)


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
        lines.append(rf"\underline{{\textbf{{Nome}}}} — {tex_escape(r.name)} \\")
    if r.platform:
        icon = PLATFORM_LATEX_EMOJIS[r.platform.value]
        label = PLATFORM_DETAILS[r.platform.value]['label']
        lines.append(rf"\textbf{{Piattaforma}} — \emoji{{{icon}}} \textit{{{tex_escape(label)}}} \\")
    if r.link:
        lines.append(rf"\textbf{{Link}} — \href{{{r.link}}}{{\emoji{{link}} \textcolor{{linkblue}}{{Link}}}} \\")
    if r.version:
        lines.append(rf"\textbf{{Versione}} — \texttt{{{r.version}}} \\")
    if r.functionalities:
        lines.append(rf"\textbf{{Funzionalità}} — \textit{{{r.functionalities}}} \\")
    if r.issued_at:
        s = format_time_as_rome(until=datetime.fromisoformat(r.issued_at)).replace("<b>", "").replace("</b>", "")
        lines.append(rf"\textbf{{Data}} — {tex_escape(s)} \\")
    if r.status:
        icon = STATUS_LATEX_EMOJIS[r.status.value]
        label = REQUEST_STATUS_DETAILS[r.status.value]['label']
        color = STATUS_COLORS[r.status.value]
        lines.append(rf"\textbf{{Status}} — \emoji{{{icon}}} \textcolor{{{color}}}{{{tex_escape(label)}}} \\")

    if r.rejection_reason:
        rejection_text = rf"\textbf{{Motivo}} — \textit{{{r.rejection_reason}}}"
    else:
        rejection_text = rf"\textbf{{Motivo}} — \texttt{{None}}"
    lines.append(rf"{rejection_text} \\")

    lines.append(rf"\end{{minipage}}")
    return "".join(lines)


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
    """


def render_requests_latex_footer() -> str:
    return r"""\end{enumerate}
\end{multicols}
\end{document}
"""


async def get_last_n_requests(
        n: int,
        pl: Optional[Union[Platform, str]],
        ca: Optional[Union[Category, str]]
) -> list[Request]:
    """
    Ritorna le ultime n richieste fatte per una specifica sezione.

    """
    if not isinstance(n, int) or n < 0:
        raise ValueError(f"Invalid number of requests: {n}")

    if pl and isinstance(pl, Platform):
        pl = pl.value
    if ca and isinstance(ca, Category):
        ca = ca.value

    if pl and pl not in PLATFORM_DETAILS:
        raise ValueError(f"Invalid platform: {pl}")
    if pl and ca and ca not in CATEGORY_DETAILS[pl]:
        raise ValueError(f"Invalid category: {ca}")

    query = "SELECT * FROM requests"
    params = []
    conditions = []

    if pl:
        params.append(pl)
        conditions.append(f"platform = ${len(params)}")

        if ca:
            params.append(ca)
            conditions.append(f"category = ${len(params)}")
    elif ca:
        params.append(ca)
        conditions.append(f"category = ${len(params)}")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    params.append(n)
    query += f" ORDER BY issued_at DESC LIMIT ${len(params)}"

    res = await fetch_query(query, params)

    if res is None:
        return []

    return [await request_from_record(dict(record)) for record in res]


def get_config(context: CustomContext, platform: Platform, category: Category) -> CategorySetting:
    """Helper per recuperare la configurazione in modo sicuro e tipizzato."""
    return getattr(getattr(context.pydb.configuration.settings.request, platform.value), category.value)
