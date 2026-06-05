import json
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from aimods_bot.src.helpers.constants.constants import Platform, RequestStatus, Category, FieldFormat
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.requests import PLATFORM_CATEGORY_REGISTRY, BaseRequest
from aimods_bot.src.helpers.utils.time_utils import format_time_as_rome

log = logger.getChild(__name__)


# Contiene tutte le colonne in comune tra le richieste (che corrispondono ai campi di BaseRequest, meno name e version)
_COMMON_REQUEST_TABLE_COLUMNS: set[str] = {
    "id",
    "user_id",
    "platform",
    "category",
    "status",
    "issued_at",
    "rejection_reason",
    "status_change_notifications",
}


async def get_user_requests_archive(user_id: int) -> list[BaseRequest]:
    """Interroga il db per ottenere le richieste formulate da un certo utente."""
    query = """SELECT * \
               FROM requests \
               WHERE user_id = $1 \
               ORDER BY issued_at DESC"""
    response = await fetch_query(query=query, params=[user_id])

    if not response:
        return []

    return [request_from_record(dict(el)) for el in response]



def request_to_record(request: BaseRequest) -> dict[str, Any]:
    """
    Converte un'istanza di BaseRequest (o sottoclasse) in un dict pronto per
    l'inserimento/aggiornamento nella tabella `requests`.

    La chiave `content` contiene un dict JSON-serializzabile con tutti i campi
    specifici della sottoclasse. Le chiavi top-level corrispondono alle colonne
    della tabella.

    Nota: `issued_at` viene serializzato a ISO string. Il dict risultante è
    interamente JSON-safe; asyncpg accetta sia stringhe ISO che datetime nativi
    per colonne timestamptz.
    """
    content = request.model_dump(mode="json", exclude=_COMMON_REQUEST_TABLE_COLUMNS)

    return {
        "id": request.id,
        "user_id": request.user_id,
        "platform": request.platform.value,
        "category": request.category.value,
        "status": request.status.value if request.status else None,
        "issued_at": request.issued_at.isoformat() if request.issued_at else None,
        "rejection_reason": request.rejection_reason,
        "status_change_notifications": request.status_change_notifications,
        "content": content,
    }


def request_from_record(row: dict[str, Any]) -> BaseRequest:
    """
    Converte una riga della tabella `requests` (dict o asyncpg.Record convertito
    a dict) nell'istanza concreta di BaseRequest corrispondente, scegliendo la
    sottoclasse tramite PLATFORM_CATEGORY_REGISTRY.

    Solleva ValueError per dati mancanti, malformati o combinazioni platform/category non registrate.
    """
    raw_id = row.get("id")
    raw_platform = row.get("platform")
    raw_category = row.get("category")
    raw_status = row.get("status")
    raw_content = row.get("content")
    issued_at = row.get("issued_at")
    user_id = row.get("user_id")
    rejection_reason = row.get("rejection_reason")
    status_change_notifications = row.get("status_change_notifications", True)

    if user_id is None:
        raise ValueError(f"Request {raw_id}: missing user_id!")

    if (isinstance(user_id, str) and not user_id.isnumeric()) and not isinstance(user_id, int):
        raise ValueError(f"User id {user_id} is not numeric!")

    if not raw_platform or not raw_category:
        raise ValueError(
            f"Request {raw_id}: missing platform or category (platform={raw_platform!r}, category={raw_category!r})!"
        )

    if issued_at is not None and not isinstance(issued_at, (str, datetime)):
        raise ValueError(
            f"Request {raw_id}: issued_at must be datetime or ISO string, found {type(issued_at).__name__}"
        )

    try:
        platform = Platform(raw_platform)
    except ValueError as e:
        raise ValueError(f"Request {raw_id}: invalid platform '{raw_platform}'!") from e

    try:
        category = Category(raw_category)
    except ValueError as e:
        raise ValueError(f"Request {raw_id}: invalid category '{raw_category}'!") from e

    status: RequestStatus | None = None
    if raw_status:
        try:
            status = RequestStatus(raw_status)
        except ValueError as e:
            raise ValueError(f"Request {raw_id}: invalid status '{raw_status}'!") from e

    try:
        model_cls = PLATFORM_CATEGORY_REGISTRY[platform][category].model
    except KeyError as e:
        raise ValueError(
            f"Request {raw_id}: {platform.value}/{category.value} combination not found in PLATFORM_CATEGORY_REGISTRY!"
        ) from e

    content_dict: dict[str, Any]
    if raw_content is None:
        content_dict = {}
    elif isinstance(raw_content, dict):
        content_dict = raw_content
    elif isinstance(raw_content, str):
        try:
            content_dict = json.loads(raw_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Request {raw_id}: wrong JSON structure!") from e
    else:
        raise ValueError(
            f"Request {raw_id}: unexpected content type {type(raw_content).__name__}!"
        )

    try:
        return model_cls(
            id=raw_id,
            user_id=int(user_id),
            section=RequestSection(platform=platform, category=category),
            status=status,
            issued_at=issued_at,
            rejection_reason=rejection_reason,
            status_change_notifications=status_change_notifications,
            **content_dict,
        )
    except ValidationError as e:
        log.error(f"Request {raw_id}: validation failed for {model_cls.__name__}: {e}")
        raise


def get_requests_summary(requests: list[BaseRequest], with_authors: bool = False) -> str:
    """
    Ritorna il sommario delle richieste nel dizionario.
    """
    parts = []

    for n, request in enumerate(requests):
        status = request.status
        platform = request.platform
        category = request.category

        if not status:
            raise ValueError(f"Request {request.id}: status must not be None!")

        if not category or not platform:
            raise ValueError(
                f"Request {request.id}: missing platform or category (platform={platform!r}, category={category!r})!"
            )

        category_config = PLATFORM_CATEGORY_REGISTRY[platform][category]

        block = [
            f"    {n + 1}. <i>{request.name}</i>\n",
            f"         #️⃣ <u>ID</u> — <code>{request.id}</code>\n"
        ]

        if with_authors:
            block.append(f"         👤 <u>Formulata Da</u> — <code>{request.user_id}</code>\n")

        block.extend([
            f"         🖲️ <u>Piattaforma</u> — {platform.icon} {category_config.icon}\n",
            f"         🔧 <u>Stato</u> — {status.icon} <b><i>{status.label}</i></b>\n\n"
        ])

        parts.append("".join(block))

    return "".join(parts).rstrip("\n")


def get_request_details(request: BaseRequest, admin: bool = False) -> str:
    """
    Ritorna i dettagli di una richiesta.
    """

    platform = request.platform
    category = request.category

    if not category or not platform:
        raise ValueError(
            f"Request {request.id}: missing platform or category (platform={platform!r}, category={category!r})!"
        )

    category_config = PLATFORM_CATEGORY_REGISTRY[platform][category]
    parts: list[str] = []

    if admin:
        if request.id:
            parts.append(f"      #️⃣ <u>ID</u> — <code>{request.id}</code>\n")
        if request.user_id:
            parts.append(f"      👤 <u>User ID</u> — <code>{request.user_id}</code>\n")
        parts.append("\n")

    parts.append(f"     🔸️ <u>Piattaforma</u> — {platform.icon} <i>{category_config.label}</i>\n")

    for field in type(request).FLOW:
        value = getattr(request, field.value, None)
        if value is None or value == "":
            continue
        rendered = _render_field_value_html(value, field.format)
        parts.append(f"     🔸 <u>{field.label}</u> — {rendered}\n")

    if request.issued_at:
        parts.append(f"     🔸 <u>Data</u> — <i>{format_time_as_rome(request.issued_at)}</i>\n")

    if request.status:
        parts.append(f"\n      <b><u>Status</u></b> — {request.status.icon} <i>{request.status.label}</i>\n")

        if request.status == RequestStatus.REJECTED:
            parts.append(f"      <b><u>Motivazione</u></b> — {request.rejection_reason}\n")

        if request.status == RequestStatus.COMPLETED and not admin:
            parts.append(
                "\n<blockquote>ℹ <b>Cosa Significa?</b> — Se una richiesta è <i>✅ Completata</i>, "
                "il post dell'app o del software richiesto è in programmazione. Per i software Windows "
                "e MacOS, <b>il rilascio sulle piattaforme avverrà assieme al post, oppure prima</b>.</blockquote>"
            )

    if not admin and request.is_active:
        prefix = "🔔 Riceverai" if request.status_change_notifications else "🔕 Non riceverai"
        parts.append(f"\n<blockquote>{prefix} una notifica quando questa richiesta verrà chiusa.</blockquote>")

    return "".join(parts)


def _render_field_value_html(value: Any, fmt: FieldFormat) -> str:
    if fmt is FieldFormat.BOOL:
        return "<i>✔️</i>" if value else "<i>✖️</i>"
    if fmt is FieldFormat.LINK:
        return f'<a href="{str(value)}">🔗 Link</a>'
    if fmt is FieldFormat.CODE:
        return f"<code>{value}</code>"
    return f"<i>{value}</i>"  # TEXT


async def get_last_n_requests(
        n: int,
        platform: Platform | None = None,
        category: Category | None = None,
) -> list[BaseRequest]:
    """
    Ritorna le ultime n richieste fatte per una specifica sezione.
    """
    if not isinstance(n, int) or n <= 0:
        raise ValueError(f"Invalid request number: {n}!")

    query = "SELECT * FROM requests"
    params = []
    conditions = []

    if platform:
        params.append(platform.value)
        conditions.append(f"platform = ${len(params)}")

        if category:
            params.append(category.value)
            conditions.append(f"category = ${len(params)}")
    elif category:
        params.append(category.value)
        conditions.append(f"category = ${len(params)}")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    params.append(n)
    query += f" ORDER BY issued_at DESC LIMIT ${len(params)}"

    res = await fetch_query(query, params)

    if res is None:
        return []

    return [request_from_record(dict(record)) for record in res]
