import pytest
from datetime import datetime, timezone

from pydantic import HttpUrl

from aimods_bot.src.helpers.models.requests import (
    AndroidApp, WindowsGame, WindowsAdobe, WindowsDaw, WindowsSoftware, IosApp, MacOsDaw, MacOsSoftware,
)
from aimods_bot.src.helpers.utils.request_utils import request_from_record, request_to_record


SAMPLES = [
    AndroidApp(
        user_id=123,
        name="Spotify",
        version="8.9.0",
        link=HttpUrl("https://spotify.com"),
        features="Premium",
    ),
    WindowsGame(
        user_id=123,
        name="Cyberpunk 2077",
        version="2.1",
        link=HttpUrl("https://gog.com/cyberpunk"),
        features="DLC inclusi",
        steamtools=True,
        hypervisor=False,
    ),
    WindowsAdobe(
        user_id=123,
        name="Photoshop",
        version="25.0",
        features="Generative Fill",
        arch_arm=False,
    ),
    WindowsDaw(
        user_id=123,
        name="Ableton Live",
        version="12.0",
        link=HttpUrl("https://ableton.com"),
    ),
    WindowsSoftware(
        user_id=123,
        name="IDA Pro",
        version="8.4",
        link=HttpUrl("https://hex-rays.com"),
        features="Decompiler",
    ),
    IosApp(
        user_id=123,
        name="Procreate",
        version="5.3",
        link=HttpUrl("https://procreate.com"),
        features="Tutto sbloccato",
    ),
    MacOsDaw(
        user_id=123,
        name="Logic Pro",
        version="11.0",
        link=HttpUrl("https://apple.com/logic"),
        mac_os_version="Sonoma 14.5",
        arch_arm=True,
    ),
    MacOsSoftware(
        user_id=123,
        name="Final Cut Pro",
        version="10.7",
        link=HttpUrl("https://apple.com/final-cut"),
        features="Tutto sbloccato",
        mac_os_version="Sonoma 14.5",
        arch_arm=True,
    ),
]


@pytest.mark.parametrize(
    "original",
    SAMPLES,
    ids=lambda r: type(r).__name__,
)
def test_request_roundtrip(original):
    """Una richiesta serializzata e deserializzata deve restare identica."""
    original.id = 42
    original.issued_at = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    record = request_to_record(original)
    restored = request_from_record(record)

    assert type(restored) is type(original)
    assert restored == original
