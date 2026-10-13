"""
I tasti delle notifiche devono fare qualcosa, in qualunque stato sia la conversazione.

Ogni test manda un clic dentro il `ConversationHandler` vero. Il bot è finto: una
`BaseRequest` che registra le chiamate e risponde come Telegram. Il controllo più
importante è che il clic produca un effetto (pannello modificato, impostazione
cambiata) oltre all'`answerCallbackQuery`, che da solo è il sintomo del tasto «muto».
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

from telegram import Update  # noqa: E402
from telegram.ext import ApplicationBuilder, ContextTypes, DictPersistence, PersistenceInput  # noqa: E402
from telegram.request import BaseRequest  # noqa: E402

from aimods_bot.src.app.handlers.conversation import main_private_conversation_handler as conv  # noqa: E402
from aimods_bot.src.core.config.loader import load_configuration  # noqa: E402
from aimods_bot.src.core.config.models import Configuration  # noqa: E402
from aimods_bot.src.core.customcontext import CustomContext, BotData, ChatData, UserData  # noqa: E402
from aimods_bot.src.features.requests.section import RequestSection  # noqa: E402
from aimods_bot.src.ui.conversation_states import PrivateConversationState as PCS  # noqa: E402
from aimods_bot.src.ui.path_navigation import (  # noqa: E402
    AdminRoute, AdminSettingsNotificationsRoute, AdminSettingsRoute, GlobalAction, NotificationAction,
    UserManageSettingsRoute, UserRoute,
)
from aimods_bot.src.ui.routing import PathBuilder  # noqa: E402

USER, ADMIN, BOT = 111, 999, 42
SECTION = RequestSection(platform="windows", category="game")

BTN_NEW_REQUEST = PathBuilder(UserRoute.ROOT, UserRoute.ADD_REQUEST, NotificationAction.FROM_NOTIFICATION,
                              SECTION).build()
BTN_MUTE_SECTION = PathBuilder(UserRoute.ROOT, UserRoute.MANAGE_SETTINGS, UserManageSettingsRoute.NOTIFICATIONS,
                               UserManageSettingsRoute.SECTION_OPENING_NOTIFICATIONS,
                               NotificationAction.FROM_NOTIFICATION, SECTION).build()
BTN_ADMIN_CLOSING = PathBuilder(AdminRoute.ROOT, AdminRoute.MANAGE_SETTINGS, AdminSettingsRoute.NOTIFICATIONS,
                                AdminSettingsNotificationsRoute.SECTION_CLOSING,
                                NotificationAction.FROM_NOTIFICATION, SECTION).build()


def _bot_message(chat_id: int, text: str = "x") -> dict:
    return {"message_id": 500, "date": 0, "chat": {"id": chat_id, "type": "private"},
            "from": {"id": BOT, "is_bot": True, "first_name": "bot"}, "text": text}


class _FakeTelegram(BaseRequest):
    def __init__(self, calls: list):
        self.calls = calls

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
        self.calls.append((endpoint, params))
        if endpoint == "getMe":
            result = {"id": BOT, "is_bot": True, "first_name": "bot", "username": "testbot"}
        elif endpoint in ("sendMessage", "editMessageText", "editMessageReplyMarkup"):
            result = _bot_message(params.get("chat_id", USER), params.get("text", "x"))
        elif endpoint == "getChatMember":
            result = {"status": "member",
                      "user": {"id": params.get("user_id"), "is_bot": False, "first_name": "u"}}
        else:
            result = True
        return 200, json.dumps({"ok": True, "result": result}).encode()


class _Bench:
    def __init__(self):
        self.calls: list = []
        self.errors: list = []
        context_types = ContextTypes(context=CustomContext, bot_data=BotData, chat_data=ChatData, user_data=UserData)
        persistence = DictPersistence(store_data=PersistenceInput(False, False, False, False), update_interval=3600)
        self.app = (ApplicationBuilder().token("123:TEST")
                    .request(_FakeTelegram(self.calls)).get_updates_request(_FakeTelegram(self.calls))
                    .context_types(context_types).persistence(persistence).build())
        self.app.add_handler(conv)
        self.app.add_error_handler(self._on_error)
        bot_data = self.app.bot_data
        bot_data.configuration = Configuration.model_validate(load_configuration())
        bot_data.configuration.settings.request.windows.game.toggle = True
        bot_data.admins = {ADMIN: "admin"}
        bot_data.channel_id = -1001
        self._update_id = 0

    async def _on_error(self, update, context):
        self.errors.append(context.error)

    def chat(self, user_id: int) -> ChatData:
        return self.app.chat_data[user_id]

    def set_state(self, user_id: int, state):
        conv._conversations.pop((user_id, user_id), None)
        if state is not None:
            conv._conversations[(user_id, user_id)] = state

    def state(self, user_id: int):
        return conv._conversations.get((user_id, user_id))

    def open_wizard(self, user_id: int):
        context = CustomContext(self.app, chat_id=user_id, user_id=user_id)
        context.init_request_wizard_session(user_id=user_id, section=SECTION, from_notification=False, msg_id=400)

    async def click(self, user_id: int, data: str):
        self._update_id += 1
        update = Update.de_json({
            "update_id": self._update_id,
            "callback_query": {"id": str(self._update_id), "chat_instance": "c", "data": data,
                               "from": {"id": user_id, "is_bot": False, "first_name": "Tester"},
                               "message": _bot_message(user_id, "📭 Sezione Richieste Aperta!")},
        }, self.app.bot)
        await self.app.process_update(update)

    def edited_texts(self) -> list[str]:
        return [p.get("text", "") for e, p in self.calls if e == "editMessageText"]


def _run(scenario):
    async def main():
        bench = _Bench()
        await bench.app.initialize()
        try:
            await scenario(bench)
        finally:
            await bench.app.shutdown()
            conv._conversations.clear()
        assert not bench.errors, bench.errors
    asyncio.run(main())


def _opening(chat: ChatData) -> bool:
    return chat.persistent.user_notifications.section_opening_notifications["windows"]["game"]


@pytest.mark.parametrize("state", [None, PCS.USER_CONVERSATION])
def test_mute_section_from_notification_turns_it_off(state):
    async def scenario(b: _Bench):
        b.chat(USER).persistent.user_notifications.section_opening_notifications["windows"]["game"] = True
        b.set_state(USER, state)
        await b.click(USER, BTN_MUTE_SECTION)
        assert _opening(b.chat(USER)) is False
        assert any("Notifiche Disattivate" in t for t in b.edited_texts())
    _run(scenario)


def test_mute_section_twice_stays_off():
    async def scenario(b: _Bench):
        b.chat(USER).persistent.user_notifications.section_opening_notifications["windows"]["game"] = True
        b.set_state(USER, PCS.USER_CONVERSATION)
        await b.click(USER, BTN_MUTE_SECTION)
        await b.click(USER, BTN_MUTE_SECTION)
        assert _opening(b.chat(USER)) is False
    _run(scenario)


def test_mute_section_with_open_wizard_keeps_the_wizard():
    async def scenario(b: _Bench):
        b.chat(USER).persistent.user_notifications.section_opening_notifications["windows"]["game"] = True
        b.open_wizard(USER)
        b.set_state(USER, PCS.USER_REQUEST_WIZARD_SESSION)
        await b.click(USER, BTN_MUTE_SECTION)
        assert _opening(b.chat(USER)) is False
        assert b.chat(USER).persistent.active_request_wizard is not None
        assert b.state(USER) == PCS.USER_REQUEST_WIZARD_SESSION
    _run(scenario)


@pytest.mark.parametrize("state", [None, PCS.USER_CONVERSATION])
def test_new_request_from_notification_opens_the_wizard(state):
    async def scenario(b: _Bench):
        b.set_state(USER, state)
        await b.click(USER, BTN_NEW_REQUEST)
        assert b.state(USER) == PCS.USER_REQUEST_WIZARD_SESSION
        assert any("Nuova Richiesta" in t for t in b.edited_texts())
    _run(scenario)


def test_new_request_from_notification_with_open_wizard_offers_resume():
    async def scenario(b: _Bench):
        b.open_wizard(USER)
        b.set_state(USER, PCS.USER_REQUEST_WIZARD_SESSION)
        await b.click(USER, BTN_NEW_REQUEST)
        assert any("stai già facendo" in t for t in b.edited_texts())
        assert b.state(USER) == PCS.USER_CONVERSATION
        # «Continuo la Precedente» riporta nel wizard
        resume = PathBuilder(UserRoute.ROOT, UserRoute.ADD_REQUEST, SECTION.platform, SECTION.category,
                             "continue_request").build()
        await b.click(USER, resume)
        assert b.state(USER) == PCS.USER_REQUEST_WIZARD_SESSION
    _run(scenario)


def test_wizard_state_without_wizard_goes_back_to_menu():
    async def scenario(b: _Bench):
        b.chat(USER).persistent.active_request_wizard = None
        b.set_state(USER, PCS.USER_REQUEST_WIZARD_SESSION)
        await b.click(USER, GlobalAction.YES)
        assert b.state(USER) == PCS.USER_CONVERSATION
        assert any("Pannello Utente" in t for t in b.edited_texts())
    _run(scenario)


def test_admin_mute_section_closing_from_notification():
    async def scenario(b: _Bench):
        settings = b.chat(ADMIN).persistent.admin_notifications.section_closing_notifications
        settings["windows"]["game"] = True
        b.set_state(ADMIN, PCS.ADMIN_CONVERSATION)
        await b.click(ADMIN, BTN_ADMIN_CLOSING)
        assert settings["windows"]["game"] is False
        assert any("Notifiche Disattivate" in t for t in b.edited_texts())
    _run(scenario)
