"""
Notifiche di cambio stato di una richiesta: il toggle dell'utente deve finire nel database,
non solo nella copia in memoria (che si perde al riavvio).
"""
import asyncio
from types import SimpleNamespace

import aimods_bot.src.core.customcontext as customcontext
from aimods_bot.src.core.customcontext import CustomContext, BotData
from aimods_bot.src.core.constants import RequestStatus
from aimods_bot.src.features.requests.user.management.handle import toggle_status_notifications
from aimods_bot.tests.test_channel_membership import make_request


def _context(requests):
    bot_data = BotData()
    bot_data.active_requests = requests
    ctx = SimpleNamespace(pydb=bot_data, user_id=42)
    ctx.set_request_status_change_notifications = (
        lambda ix, enabled: CustomContext.set_request_status_change_notifications(ctx, ix, enabled)
    )
    return ctx


def _patch_db(monkeypatch, result: bool):
    calls = []

    async def fake_execute_query(query, params):
        calls.append((query, params))
        return result

    monkeypatch.setattr(customcontext, "execute_query", fake_execute_query)
    return calls


def test_toggle_writes_db_then_cache(monkeypatch):
    calls = _patch_db(monkeypatch, result=True)
    request = make_request(status_change_notifications=True)
    ctx = _context({7: request})

    assert asyncio.run(toggle_status_notifications(ctx, request))
    assert request.status_change_notifications is False
    (query, params), = calls
    assert "SET status_change_notifications = $1 WHERE id = $2" in query
    assert params == [False, 7]

    assert asyncio.run(toggle_status_notifications(ctx, request))
    assert request.status_change_notifications is True
    assert calls[1][1] == [True, 7]


def test_toggle_leaves_cache_alone_if_db_fails(monkeypatch):
    _patch_db(monkeypatch, result=False)
    request = make_request(status_change_notifications=True)
    ctx = _context({7: request})

    assert not asyncio.run(toggle_status_notifications(ctx, request))
    assert request.status_change_notifications is True


def test_toggle_ignores_closed_requests(monkeypatch):
    calls = _patch_db(monkeypatch, result=True)
    request = make_request(status=RequestStatus.COMPLETED, status_change_notifications=True)
    ctx = _context({7: request})

    assert not asyncio.run(toggle_status_notifications(ctx, request))
    assert request.status_change_notifications is True
    assert calls == []
