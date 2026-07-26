from enum import StrEnum
from typing import Annotated, Literal, Optional, Union, Callable
from pydantic import BaseModel, Field, ValidationError

from aimods_bot.src.helpers.models.request_section import RequestSection

_SEPARATOR = ":"


class JobKind(StrEnum):
    AUTO_RECAP = "auto_recap"
    REMOVE_INACTIVE_REQUEST = "remove_inactive_request"
    REQUEST_LIMIT = "request_limit"
    REQUEST_COOLDOWN = "request_cooldown"
    DELAYED_SECTION_OPENING_CHECK = "delayed_section_opening_check"


class _BaseJobName(BaseModel):
    """Base per i nomi tipizzati dei job pianificati."""
    model_config = {"frozen": True}

    def __str__(self) -> str:
        return self.to_string()

    def to_string(self) -> str:
        raise NotImplementedError


class AutoRecapJobName(_BaseJobName):
    name: Literal[JobKind.AUTO_RECAP] = JobKind.AUTO_RECAP

    def to_string(self) -> str:
        return self.name.value


class RemoveInactiveRequestJobName(_BaseJobName):
    name: Literal[JobKind.REMOVE_INACTIVE_REQUEST] = JobKind.REMOVE_INACTIVE_REQUEST
    request_id: int

    def to_string(self) -> str:
        return _SEPARATOR.join([self.name.value, str(self.request_id)])


class RequestLimitJobName(_BaseJobName):
    name: Literal[JobKind.REQUEST_LIMIT] = JobKind.REQUEST_LIMIT
    user_id: int
    section: RequestSection

    def to_string(self) -> str:
        return _SEPARATOR.join([
            self.name.value,
            str(self.user_id),
            self.section.platform.value,
            self.section.category.value,
        ])


class RequestCooldownJobName(_BaseJobName):
    name: Literal[JobKind.REQUEST_COOLDOWN] = JobKind.REQUEST_COOLDOWN
    user_id: int

    def to_string(self) -> str:
        return _SEPARATOR.join([self.name.value, str(self.user_id)])


class DelayedSectionOpeningJobName(_BaseJobName):
    name: Literal[JobKind.DELAYED_SECTION_OPENING_CHECK] = JobKind.DELAYED_SECTION_OPENING_CHECK
    section: RequestSection

    def to_string(self) -> str:
        return _SEPARATOR.join([
            self.name.value,
            self.section.platform.value,
            self.section.category.value,
        ])


JobName = Annotated[
    Union[
        AutoRecapJobName,
        RemoveInactiveRequestJobName,
        RequestLimitJobName,
        RequestCooldownJobName,
        DelayedSectionOpeningJobName,
    ],
    Field(discriminator="name"),
]


def parse_job_name(raw: str) -> Optional[JobName]:
    """
    Parsa un nome job APScheduler in un'istanza tipizzata.
    Ritorna None se il nome non è riconosciuto o malformato.
    """
    if not raw:
        return None

    head, *args = raw.split(_SEPARATOR)

    try:
        name = JobKind(head)
    except ValueError:
        return None

    try:
        match name:
            case JobKind.AUTO_RECAP:
                return AutoRecapJobName() if not args else None

            case JobKind.REMOVE_INACTIVE_REQUEST:
                if len(args) != 1:
                    return None
                return RemoveInactiveRequestJobName(request_id=int(args[0]))

            case JobKind.REQUEST_LIMIT:
                if len(args) != 3:
                    return None
                return RequestLimitJobName(
                    user_id=int(args[0]),
                    section=RequestSection(platform=args[1], category=args[2])
                )

            case JobKind.REQUEST_COOLDOWN:
                if len(args) != 1:
                    return None
                return RequestCooldownJobName(user_id=int(args[0]))

            case JobKind.DELAYED_SECTION_OPENING_CHECK:
                if len(args) != 2:
                    return None
                return DelayedSectionOpeningJobName(
                    section=RequestSection(platform=args[0], category=args[1])
                )

    except (ValueError, ValidationError):
        return None


def filter_jobs_by_kind(
    job_queue,
    name_type: type[_BaseJobName],
    predicate: Callable[[_BaseJobName], bool] | None = None,
):
    """
    Ritorna i job APScheduler il cui nome parsato è un'istanza di `name_type`
    e (opzionalmente) soddisfa `predicate`.
    """
    for job in job_queue.jobs():
        parsed = parse_job_name(job.name)
        if isinstance(parsed, name_type) and (predicate is None or predicate(parsed)):
            yield job
