import pytest

from aimods_bot.src.helpers.models.typed_callback_data import (
    AlertCallbackData,
    CallbackType,
    parse_callback_data,
)


SAMPLES = [
    AlertCallbackData(user_id=123, alert_id="abc12345"),
    AlertCallbackData(user_id=999999999, alert_id="deadbeef"),
    AlertCallbackData(user_id=1, alert_id="0"),
]


@pytest.mark.parametrize("original", SAMPLES, ids=lambda c: f"{type(c).__name__}_{c.user_id}")
def test_callback_data_roundtrip(original):
    s = original.to_string()
    parsed = parse_callback_data(s)
    assert parsed == original


def test_unknown_kind_returns_none():
    assert parse_callback_data("inesistente:123:abc") is None


def test_malformed_returns_none():
    assert parse_callback_data("") is None
    assert parse_callback_data("alert") is None  # nessun arg
    assert parse_callback_data("alert:123") is None  # arg mancante
    assert parse_callback_data("alert:nonsense:abc") is None  # user_id non int
    assert parse_callback_data("alert:123:abc:extra") is None  # arg extra


def test_callback_type_members_all_handled():
    """Sentinel: se aggiungi un CallbackKind, ricontrolla parse_callback_data."""
    for ctype in CallbackType:
        parse_callback_data(ctype.value)  # non deve sollevare
