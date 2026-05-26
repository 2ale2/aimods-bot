import pytest

from aimods_bot.src.helpers.models.job_names import (
    AutoRecapJobName,
    RemoveInactiveRequestJobName,
    RequestLimitJobName,
    RequestCooldownJobName,
    DelayedSectionOpeningJobName,
    JobKind,
    parse_job_name,
)
from aimods_bot.src.helpers.constants.constants import Platform, Category


SAMPLES = [
    AutoRecapJobName(),
    RemoveInactiveRequestJobName(request_id=42),
    RequestLimitJobName(user_id=123, platform=Platform.ANDROID, category=Category.APP),
    RequestCooldownJobName(user_id=999),
    DelayedSectionOpeningJobName(platform=Platform.WINDOWS, category=Category.GAME),
]


@pytest.mark.parametrize("original", SAMPLES, ids=lambda j: type(j).__name__)
def test_job_name_roundtrip(original):
    s = original.to_string()
    parsed = parse_job_name(s)
    assert parsed == original


def test_unknown_kind_returns_none():
    assert parse_job_name("inesistente:42") is None


def test_malformed_returns_none():
    assert parse_job_name("request_limit:nonsense") is None
    assert parse_job_name("") is None
    assert parse_job_name("auto_recap:unexpected_arg") is None
    assert parse_job_name("remove_inactive_request") is None  # arg mancante
    assert parse_job_name("request_limit:1:android") is None  # arg parziale


def test_jobkind_members_all_handled():
    """Sentinel: se aggiungi un JobKind, ricontrolla che parse_job_name lo gestisca."""
    for kind in JobKind:
        # non deve mai sollevare eccezione
        parse_job_name(kind.value)