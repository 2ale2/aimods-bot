import platform as platf
from pathlib import Path
from typing import Iterable, AsyncIterator, Any

from aimods_bot.src.helpers.constants.constants import Platform, RequestStatus, FieldFormat, RequestField
from aimods_bot.src.helpers.models.requests import BaseRequest
from aimods_bot.src.helpers.utils.file_utils import convert_latex_to_pdf, create_latex_file, tex_escape
from aimods_bot.src.helpers.utils.time_utils import format_time_as_rome


_PLATFORM_LATEX_EMOJIS = {
    Platform.ANDROID: "robot",
    Platform.WINDOWS: "laptop",
    Platform.IOS: "green-apple",
    Platform.MACOS: "desktop-computer"
}

_STATUS_LATEX_COLORS = {
    RequestStatus.PENDING: "orange",
    RequestStatus.EXAMINING: "linkblue",
    RequestStatus.TESTING: "teal",
    RequestStatus.COMPLETED: "green!60!black",
    RequestStatus.REJECTED: "red",
    RequestStatus.CANCELLED: "statusgrey"
}

_STATUS_LATEX_EMOJIS = {
    RequestStatus.PENDING: "hourglass-not-done",
    RequestStatus.EXAMINING: "magnifying-glass-tilted-right",
    RequestStatus.TESTING: "test-tube",
    RequestStatus.COMPLETED: "check-mark-button",
    RequestStatus.REJECTED: "cross-mark",
    RequestStatus.CANCELLED: "wastebasket"
}


async def generate_user_archive_requests_pdf_file(requests: list[BaseRequest], input_path: str) -> str:
    input_path = str(Path(input_path).with_suffix(".tex"))
    tex_p = await generate_user_archive_requests_latex_file(requests=requests, out_path=input_path)
    pdf_p = await convert_latex_to_pdf(tex_path=tex_p)
    return str(pdf_p)


async def generate_user_archive_requests_latex_file(requests: list[BaseRequest], out_path: str) -> str:
    p = await create_latex_file(out_path, iter_archive_tex(requests))
    return str(p)


async def iter_archive_tex(requests: Iterable[BaseRequest]) -> AsyncIterator[str]:
    yield render_requests_latex_header()
    for r in requests:
        yield render_request_latex_item(r)
    yield render_requests_latex_footer()


def render_request_latex_item(request: BaseRequest) -> str:
    lines = [
        rf"\item\begin{{minipage}}[t]{{\linewidth}}\raggedright",
        rf"\underline{{\textbf{{Nome}}}} — {tex_escape(request.name)} \\"
    ]

    platform = request.platform

    if not platform:
        raise ValueError(f"Request {request.id} must have a platform!")

    icon = _PLATFORM_LATEX_EMOJIS[platform]
    lines.append(rf"\textbf{{Piattaforma}} — \emoji{{{icon}}} \textit{{{tex_escape(platform.label)}}} \\")

    for field in type(request).FLOW:
        if field is RequestField.NAME:
            continue
        value = getattr(request, field.value, None)
        if value is None or value == "":
            continue
        rendered = _render_field_value_latex(value, field.format)
        lines.append(rf"\textbf{{{field.label}}} — {rendered} \\")

    if request.issued_at:
        s = format_time_as_rome(until=request.issued_at, markup=False)
        if s:
            lines.append(rf"\textbf{{Data}} — {tex_escape(s)} \\")
        else:
            lines.append(r"\textbf{{Data}} — \texttt{None} \\")

    status = request.status
    if status:
        color = _STATUS_LATEX_COLORS[status]
        icon = _STATUS_LATEX_EMOJIS[status]
        lines.append(rf"\textbf{{Status}} — \emoji{{{icon}}} \textcolor{{{color}}}{{{tex_escape(status.label)}}} \\")

    if request.rejection_reason:
        lines.append(rf"\textbf{{Motivo}} — \textit{{{tex_escape(request.rejection_reason)}}} \\")
    else:
        lines.append(r"\textbf{Motivo} — \texttt{None} \\")

    lines.append(rf"\end{{minipage}}")
    return "".join(lines)


def _render_field_value_latex(value: Any, fmt: FieldFormat) -> str:
    if fmt is FieldFormat.BOOL:
        return r"\emoji{check-mark-button}" if value else r"\emoji{cross-mark}"
    if fmt is FieldFormat.LINK:
        return rf"\href{{{str(value)}}}{{\emoji{{link}} \textcolor{{linkblue}}{{Link}}}}"
    if fmt is FieldFormat.CODE:
        return rf"\texttt{{{tex_escape(str(value))}}}"
    return rf"\textit{{{tex_escape(str(value))}}}"  # TEXT


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
