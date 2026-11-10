"""
«Contatta Autore»: link diretto alla chat dell'autore quando Telegram lo consente,
avviso del bot all'autore come alternativa.

Il bot è finto e risponde come Telegram, errori compresi: un tasto `tg://user` verso un
utente con la privacy chiusa fa fallire tutto il messaggio con BUTTON_USER_PRIVACY_RESTRICTED.
"""
import asyncio
import json
import locale
import os
import tempfile
from pathlib import Path

import pytest

for _key, _value in {
    "CHANNEL_ID": "-1001",
    "CHANNEL_LOGGER_ID": "-1002",
    "MYID": "1",
    "LOG_DIR": os.path.join(tempfile.gettempdir(), "aimods_bot_test_logs"),
}.items():
    os.environ.setdefault(_key, _value)
os.chdir(Path(__file__).resolve().parents[2])
_real_setlocale = locale.setlocale
locale.setlocale = lambda category, loc=None: _real_setlocale(category)  # it_IT può mancare in locale

from pydantic import HttpUrl  # noqa: E402
from telegram import Update  # noqa: E402
from telegram.error import BadRequest  # noqa: E402
from telegram.ext import ApplicationBuilder, ContextTypes, DictPersistence, PersistenceInput  # noqa: E402
from telegram.request import BaseRequest  # noqa: E402

from aimods_bot.src.app.handlers.conversation import main_private_conversation_handler as conv  # noqa: E402
from aimods_bot.src.core.config.loader import load_configuration  # noqa: E402
from aimods_bot.src.core.config.models import Configuration  # noqa: E402
from aimods_bot.src.core.constants import RequestStatus  # noqa: E402
from aimods_bot.src.core.customcontext import CustomContext, BotData, ChatData, UserData  # noqa: E402
from aimods_bot.src.features.requests.admin.contact.links import (  # noqa: E402
    LinkFailure, classify_link_error, forget_link_failures, known_link_failure,
)
from aimods_bot.src.features.requests.models import WindowsGame  # noqa: E402
from aimods_bot.src.features.requests.section import RequestSection  # noqa: E402
from aimods_bot.src.ui.conversation_states import PrivateConversationState as PCS  # noqa: E402
from aimods_bot.src.ui.path_navigation import (  # noqa: E402
    AdminRequestManagementRoute, AdminRequestsRoute, AdminRoute, GlobalAction,
)
from aimods_bot.src.ui.routing import PathBuilder  # noqa: E402

USER, ADMIN, BOT = 111, 999, 42
REQUEST_ID = 7
SECTION = RequestSection(platform="windows", category="game")

REQUEST_PATH = PathBuilder(AdminRoute.ROOT, AdminRoute.MANAGE_REQUESTS, AdminRequestsRoute.ACTIVE,
                           SECTION.platform, SECTION.category, str(REQUEST_ID))
CONTACT = REQUEST_PATH.add(AdminRequestManagementRoute.CONTACT_AUTHOR)
NOTIFY = CONTACT.add(AdminRequestManagementRoute.NOTIFY_AUTHOR)
NOTIFY_YES = NOTIFY.add(GlobalAction.YES)


def _bot_message(chat_id: int, text: str = "x") -> dict:
    return {"message_id": 500, "date": 0, "chat": {"id": chat_id, "type": "private"},
            "from": {"id": BOT, "is_bot": True, "first_name": "bot"}, "text": text}


def _error(code: int, description: str):
    return code, json.dumps({"ok": False, "error_code": code, "description": description}).encode()


class _FakeTelegram(BaseRequest):
    def __init__(self, bench: "_Bench"):
        self.bench = bench

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    @property
    def read_timeout(self):
        return 1

    async def do_request(self, url, method, request_data=None, **kwargs):
        endpoint = url.rsplit("/", 1)[-1]
        params = request_data.parameters if request_data else {}
        self.bench.calls.append((endpoint, params))
        b = self.bench

        if endpoint == "getMe":
            result = {"id": BOT, "is_bot": True, "first_name": "bot", "username": "testbot"}
        elif endpoint == "getChat":
            uid = int(params["chat_id"])
            result = {"id": uid, "type": "private", "first_name": "u", "accent_color_id": 0,
                      "max_reaction_count": 0,
                      "accepted_gift_types": {"unlimited_gifts": True, "limited_gifts": True,
                                              "unique_gifts": True, "premium_subscription": True,
                                              "gifts_from_channels": True}}
            if b.usernames.get(uid):
                result["username"] = b.usernames[uid]
        elif endpoint in ("sendMessage", "editMessageText", "editMessageReplyMarkup"):
            markup = json.dumps(params.get("reply_markup", {}))
            if any(f"tg://user?id={uid}" in markup for uid in b.restricted):
                return _error(400, "Bad Request: BUTTON_USER_PRIVACY_RESTRICTED")
            if endpoint == "sendMessage" and int(params.get("chat_id", 0)) in b.blocked:
                return _error(403, "Forbidden: bot was blocked by the user")
            result = _bot_message(params.get("chat_id", ADMIN), params.get("text", "x"))
        else:
            result = True
        return 200, json.dumps({"ok": True, "result": result}).encode()


class _Bench:
    def __init__(self):
        self.calls: list = []
        self.errors: list = []
        self.usernames: dict[int, str | None] = {USER: None, ADMIN: "admin_ale"}
        self.restricted: set[int] = set()
        self.blocked: set[int] = set()
        context_types = ContextTypes(context=CustomContext, bot_data=BotData, chat_data=ChatData, user_data=UserData)
        persistence = DictPersistence(store_data=PersistenceInput(False, False, False, False), update_interval=3600)
        self.app = (ApplicationBuilder().token("123:TEST")
                    .request(_FakeTelegram(self)).get_updates_request(_FakeTelegram(self))
                    .context_types(context_types).persistence(persistence).build())
        self.app.add_handler(conv)
        self.app.add_error_handler(self._on_error)
        bot_data = self.app.bot_data
        bot_data.configuration = Configuration.model_validate(load_configuration())
        bot_data.admins = {ADMIN: "Ale"}
        bot_data.channel_id = -1001
        bot_data.active_requests[REQUEST_ID] = WindowsGame(
            id=REQUEST_ID, user_id=USER, name="Cyberpunk 2077", version="2.1",
            link=HttpUrl("https://gog.com/cyberpunk"), features="DLC", steamtools=True, hypervisor=False,
            status=RequestStatus.PENDING, section=SECTION
        )
        conv._conversations[(ADMIN, ADMIN)] = PCS.ADMIN_CONVERSATION
        self._update_id = 0

    async def _on_error(self, update, context):
        self.errors.append(context.error)

    async def click(self, data: PathBuilder):
        self.calls.clear()
        self._update_id += 1
        update = Update.de_json({
            "update_id": self._update_id,
            "callback_query": {"id": str(self._update_id), "chat_instance": "c", "data": data.build(),
                               "from": {"id": ADMIN, "is_bot": False, "first_name": "Tester"},
                               "message": _bot_message(ADMIN, "pannello")},
        }, self.app.bot)
        await self.app.process_update(update)

    def ok_edits(self) -> list[dict]:
        """Modifiche che Telegram ha accettato (quelle con tg:// bloccato sono escluse)."""
        return [p for e, p in self.calls if e == "editMessageText"
                and not any(f"tg://user?id={uid}" in json.dumps(p.get("reply_markup", {})) for uid in self.restricted)]

    def sent_to(self, chat_id: int) -> list[dict]:
        return [p for e, p in self.calls if e == "sendMessage" and int(p.get("chat_id", 0)) == chat_id]

    def alerts(self) -> list[str]:
        return [p.get("text", "") for e, p in self.calls if e == "answerCallbackQuery" and p.get("text")]


def _urls(params: dict) -> list[str]:
    rows = params.get("reply_markup", {}).get("inline_keyboard", [])
    return [b["url"] for row in rows for b in row if "url" in b]


def _labels(params: dict) -> list[str]:
    rows = params.get("reply_markup", {}).get("inline_keyboard", [])
    return [b["text"] for row in rows for b in row]


def _run(scenario):
    async def main():
        forget_link_failures()
        bench = _Bench()
        await bench.app.initialize()
        try:
            await scenario(bench)
        finally:
            await bench.app.shutdown()
            conv._conversations.clear()
            forget_link_failures()
        assert not bench.errors, bench.errors
    asyncio.run(main())


# ---------------------------------------------------------------------------

def test_request_panel_has_contact_button():
    async def scenario(b: _Bench):
        await b.click(REQUEST_PATH)
        assert any("💬 Contatta Autore" in _labels(p) for p in b.ok_edits())
    _run(scenario)


def test_author_with_username_gets_tme_link():
    async def scenario(b: _Bench):
        b.usernames[USER] = "autore"
        await b.click(CONTACT)
        edit = b.ok_edits()[-1]
        assert _urls(edit) == ["https://t.me/autore"]
        assert "username pubblico" in edit["text"]
    _run(scenario)


def test_author_without_username_and_open_privacy_gets_tg_link():
    async def scenario(b: _Bench):
        await b.click(CONTACT)
        edit = b.ok_edits()[-1]
        assert _urls(edit) == [f"tg://user?id={USER}"]
        assert known_link_failure(USER) is None
    _run(scenario)


def test_author_with_closed_privacy_falls_back_without_link():
    async def scenario(b: _Bench):
        b.restricted.add(USER)
        await b.click(CONTACT)
        edit = b.ok_edits()[-1]
        assert _urls(edit) == []
        assert "privacy" in edit["text"]
        assert "📨 Avvisa l'Autore" in _labels(edit)
        assert known_link_failure(USER) == LinkFailure.PRIVACY

        # Alla seconda apertura non riprova il link già rifiutato
        await b.click(CONTACT)
        attempts = [p for e, p in b.calls if e == "editMessageText" and _urls(p)]
        assert attempts == []
        assert "privacy" in b.ok_edits()[-1]["text"]
    _run(scenario)


def test_notify_confirmation_shows_preview():
    async def scenario(b: _Bench):
        await b.click(NOTIFY)
        text = b.ok_edits()[-1]["text"]
        assert "Un Admin Vuole Contattarti" in text
        assert f"<code>{REQUEST_ID}</code>" in text
        assert b.sent_to(USER) == []
    _run(scenario)


def test_notify_sends_message_with_admin_link():
    async def scenario(b: _Bench):
        await b.click(NOTIFY_YES)
        [message] = b.sent_to(USER)
        assert "<b>Ale</b>" in message["text"]
        assert f"<code>{REQUEST_ID}</code>" in message["text"]
        assert "Cyberpunk 2077" in message["text"]
        assert "https://t.me/admin_ale" in _urls(message)
        assert any("✅" in a for a in b.alerts())
        # Torna al pannello della richiesta
        assert any("💬 Contatta Autore" in _labels(p) for p in b.ok_edits())
    _run(scenario)


def test_notify_admin_without_username_uses_tg_link():
    async def scenario(b: _Bench):
        b.usernames[ADMIN] = None
        await b.click(NOTIFY_YES)
        [message] = b.sent_to(USER)
        assert _urls(message) == [f"tg://user?id={ADMIN}"]
    _run(scenario)


def test_notify_admin_with_closed_privacy_warns_the_admin():
    async def scenario(b: _Bench):
        b.usernames[ADMIN] = None
        b.restricted.add(ADMIN)
        await b.click(NOTIFY_YES)
        assert any("🔒" in a for a in b.alerts())
        assert all(len(a) <= 200 for a in b.alerts())
    _run(scenario)


def test_notify_blocked_author_warns_the_admin():
    async def scenario(b: _Bench):
        b.blocked.add(USER)
        await b.click(NOTIFY_YES)
        assert any("bloccato il bot" in a for a in b.alerts())
        # Resta sul pannello di contatto
        assert "📨 Avvisa l'Autore" in _labels(b.ok_edits()[-1])
    _run(scenario)


@pytest.mark.parametrize("message, expected", [
    ("BUTTON_USER_PRIVACY_RESTRICTED", LinkFailure.PRIVACY),
    ("Button_user_privacy_restricted", LinkFailure.PRIVACY),
    ("BUTTON_USER_INVALID", LinkFailure.INVALID),
    ("Message is not modified", None),
])
def test_classify_link_error(message, expected):
    assert classify_link_error(BadRequest(message)) == expected
