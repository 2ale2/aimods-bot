"""
Verifica dell'iscrizione al canale per chi fa una richiesta.

Qui non si parla con Telegram: `bot` e `query` sono finti. Si testa la parte
che decide, cioè dove sbagliare costa di più: un guasto scambiato per un
"non iscritto" blocca tutti; un "mai entrato" scambiato per un guasto lascia
passare tutti con una postilla che nessuno legge.
"""
import asyncio
import inspect
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import HttpUrl
from telegram import (
    ChatMemberOwner, ChatMemberAdministrator, ChatMemberMember, ChatMemberRestricted,
    ChatMemberLeft, ChatMemberBanned, User,
)
from telegram.error import BadRequest, Forbidden, NetworkError, TimedOut

import aimods_bot.src.callbacks.panels.admin.requests_management.render as admin_render
import aimods_bot.src.callbacks.panels.admin.requests_management.handle as handle
import aimods_bot.src.core.customcontext as customcontext
from aimods_bot.src.core.customcontext import CustomContext, BotData, _membership_from_status
from aimods_bot.src.core.constants import ChannelMembership, Platform, Category, RequestStatus, \
    UNKNOWN_FIELD_SENTINEL
from aimods_bot.src.helpers.constants.path_navigation import AdminRequestManagementRoute
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.models.requests import AndroidApp
from aimods_bot.src.helpers.models.ui import ButtonItem, Panel, PanelConfig
from aimods_bot.src.helpers.utils.request_utils import request_to_record, request_from_record

CHANNEL = -100123
USER = User(id=42, first_name="Mario", is_bot=False)


def make_request(**kwargs) -> AndroidApp:
    defaults = dict(
        id=7,
        user_id=USER.id,
        name="Spotify",
        version="8.9.0",
        link=HttpUrl("https://spotify.com"),
        features="Premium",
        section=RequestSection(platform=Platform.ANDROID, category=Category.APP),
        status=RequestStatus.PENDING,
        issued_at=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
    )
    defaults.update(kwargs)
    return AndroidApp(**defaults)


class FakeBot:
    """`errors` si consumano uno per chiamata; finiti quelli, risponde `result`."""
    def __init__(self, result=None, error: Exception | None = None, errors: list[Exception] | None = None):
        self.result = result
        self.errors = list(errors) if errors is not None else ([error] * 5 if error else [])
        self.calls = []

    async def get_chat_member(self, chat_id, user_id):
        self.calls.append((chat_id, user_id))
        if self.errors:
            raise self.errors.pop(0)
        return self.result


def fake_context(bot: FakeBot, channel_id: int | None = CHANNEL, requests=None, admins=None):
    """Un CustomContext senza Application: i metodi usano solo `pydb`, `bot` e `user_id`."""
    bot_data = BotData(channel_id=channel_id, admins=admins or {})
    bot_data.active_requests = requests or {}
    ctx = SimpleNamespace(pydb=bot_data, bot=bot, user_id=USER.id)
    ctx.check_channel_membership = lambda user_id=None: CustomContext.check_channel_membership(ctx, user_id)
    ctx.set_request_channel_membership = (
        lambda ix, membership, confirmed_by=None:
        CustomContext.set_request_channel_membership(ctx, ix, membership, confirmed_by)
    )
    return ctx


def check(bot: FakeBot, **kwargs) -> ChannelMembership:
    return asyncio.run(fake_context(bot, **kwargs).check_channel_membership())


# ---------- stato del ChatMember ----------

@pytest.mark.parametrize("member, expected", [
    (ChatMemberOwner(user=USER, is_anonymous=False), ChannelMembership.MEMBER),
    (ChatMemberAdministrator(
        user=USER, can_be_edited=False, is_anonymous=False, can_manage_chat=True, can_delete_messages=True,
        can_manage_video_chats=True, can_restrict_members=True, can_promote_members=False,
        can_change_info=True, can_invite_users=True, can_post_stories=False, can_edit_stories=False,
        can_delete_stories=False,
    ), ChannelMembership.MEMBER),
    (ChatMemberMember(user=USER), ChannelMembership.MEMBER),
    (ChatMemberLeft(user=USER), ChannelMembership.NOT_MEMBER),
    (ChatMemberBanned(user=USER, until_date=None), ChannelMembership.NOT_MEMBER),
], ids=["owner", "administrator", "member", "left", "banned"])
def test_status_mapping(member, expected):
    assert _membership_from_status(member) == expected


@pytest.mark.parametrize("is_member, expected", [
    (True, ChannelMembership.MEMBER),
    (False, ChannelMembership.NOT_MEMBER),
])
def test_restricted_depends_on_is_member(is_member, expected):
    # I permessi `can_*` cambiano a ogni versione della Bot API: li ricavo dalla firma
    # invece di elencarli, così il test non si rompe al prossimo aggiornamento di PTB.
    params = inspect.signature(ChatMemberRestricted).parameters
    flags = {name: False for name in params if name.startswith("can_")}
    member = ChatMemberRestricted(user=USER, is_member=is_member, until_date=None, **flags)
    assert _membership_from_status(member) == expected


# ---------- check_channel_membership ----------

def test_member_is_member():
    bot = FakeBot(result=ChatMemberMember(user=USER))
    assert check(bot) == ChannelMembership.MEMBER
    assert bot.calls == [(CHANNEL, USER.id)]


@pytest.mark.parametrize("message", [
    "User not found",
    "Bad Request: member not found",
    "USER_NOT_PARTICIPANT",
])
def test_never_joined_is_not_member_not_failure(message):
    bot = FakeBot(error=BadRequest(message))
    assert check(bot) == ChannelMembership.NOT_MEMBER
    assert len(bot.calls) == 1


def test_transient_participant_error_is_retried_once():
    bot = FakeBot(result=ChatMemberMember(user=USER), errors=[BadRequest("PARTICIPANT_ID_INVALID")])
    assert check(bot) == ChannelMembership.MEMBER
    assert len(bot.calls) == 2


def test_persistent_participant_error_is_unverified_not_blocked():
    # Colpisce anche utenti iscritti: bloccarli sarebbe peggio che segnalarli agli admin.
    bot = FakeBot(error=BadRequest("PARTICIPANT_ID_INVALID"))
    assert check(bot) == ChannelMembership.UNVERIFIED
    assert len(bot.calls) == 2


def test_other_failures_are_not_retried():
    bot = FakeBot(error=NetworkError("down"))
    check(bot)
    assert len(bot.calls) == 1


@pytest.mark.parametrize("error", [
    BadRequest("Chat not found"),
    BadRequest("Member list is inaccessible"),
    Forbidden("bot is not a member of the channel chat"),
    NetworkError("connection reset"),
    TimedOut(),
], ids=["chat-not-found", "not-admin", "forbidden", "network", "timeout"])
def test_real_failures_are_unverified(error):
    assert check(FakeBot(error=error)) == ChannelMembership.UNVERIFIED


def test_missing_channel_id_is_unverified_without_calling_telegram():
    bot = FakeBot(result=ChatMemberMember(user=USER))
    assert check(bot, channel_id=None) == ChannelMembership.UNVERIFIED
    assert bot.calls == []


def test_unverified_is_truthy():
    # Il motivo per cui è un enum e non `bool | None`: `if not esito` non deve
    # mai trattare un guasto come un "non iscritto".
    assert ChannelMembership.UNVERIFIED
    assert ChannelMembership.NOT_MEMBER


def test_needs_admin_attention():
    assert ChannelMembership.UNVERIFIED.is_unconfirmed
    assert ChannelMembership.NOT_MEMBER.is_unconfirmed
    assert not ChannelMembership.MEMBER.is_unconfirmed
    assert not ChannelMembership.MANUALLY_CONFIRMED.is_unconfirmed
    assert not ChannelMembership.UNKNOWN.is_unconfirmed


def test_unknown_is_the_shared_sentinel():
    # È il valore che la migration scrive sulle righe esistenti.
    assert ChannelMembership.UNKNOWN.value == UNKNOWN_FIELD_SENTINEL


# ---------- persistenza sul record ----------

def test_membership_is_a_column_not_content():
    request = make_request(
        channel_membership=ChannelMembership.MANUALLY_CONFIRMED,
        channel_membership_confirmed_by=99
    )
    record = request_to_record(request)

    assert record["channel_membership"] == "manually_confirmed"
    assert record["channel_membership_confirmed_by"] == 99
    assert "channel_membership" not in record["content"]
    assert "channel_membership_confirmed_by" not in record["content"]

    restored = request_from_record(record)
    assert restored.channel_membership == ChannelMembership.MANUALLY_CONFIRMED
    assert restored.channel_membership_confirmed_by == 99


def test_pre_migration_row_loads_as_unknown_without_warning():
    # Riga come la lascia la migration: 'unknown' e confirmed_by NULL.
    record = request_to_record(make_request())
    record["channel_membership"] = UNKNOWN_FIELD_SENTINEL
    record["channel_membership_confirmed_by"] = None

    restored = request_from_record(record)
    assert restored.channel_membership == ChannelMembership.UNKNOWN
    assert not admin_render._shows_membership_buttons(restored)
    assert admin_render._get_channel_membership_note(context=fake_context(FakeBot()), request=restored) == ""

    def test_draft_starts_as_unknown():
        assert make_request().channel_membership == ChannelMembership.UNKNOWN

    def test_persisted_draft_with_null_loads_as_unknown():
        # Bozza scritta in chat_data dalla prima versione, dove il campo era `| None`.
        data = make_request().model_dump(mode="json")
        data["channel_membership"] = None
        assert AndroidApp.model_validate(data).channel_membership == ChannelMembership.UNKNOWN

    def test_null_membership_from_db_is_rejected():
        # In tabella la colonna è NOT NULL: un NULL lì è un dato rotto, non una bozza.
        record = request_to_record(make_request())
        record["channel_membership"] = None
        with pytest.raises(ValueError, match="channel_membership"):
            request_from_record(record)

    @pytest.mark.parametrize("bot", [
        FakeBot(result=ChatMemberMember(user=USER)),
        FakeBot(result=ChatMemberLeft(user=USER)),
        FakeBot(error=BadRequest("User not found")),
        FakeBot(error=BadRequest("PARTICIPANT_ID_INVALID")),
        FakeBot(error=NetworkError("down")),
    ], ids=["member", "left", "never-joined", "participant-invalid", "network"])
    def test_check_never_returns_unknown(bot):
        # UNKNOWN è il default della bozza: se il controllo potesse restituirlo, una
        # richiesta confermata finirebbe in tabella come "mai controllata".
        assert check(bot) != ChannelMembership.UNKNOWN


def test_invalid_membership_value_is_rejected():
    record = request_to_record(make_request())
    record["channel_membership"] = "boh"
    with pytest.raises(ValueError, match="channel_membership"):
        request_from_record(record)


def _patch_db(monkeypatch, result: bool):
    calls = []

    async def fake_execute_query(query, params):
        calls.append((query, params))
        return result

    monkeypatch.setattr(customcontext, "execute_query", fake_execute_query)
    return calls


def test_set_membership_writes_db_then_cache(monkeypatch):
    calls = _patch_db(monkeypatch, result=True)
    request = make_request(channel_membership=ChannelMembership.UNVERIFIED)
    ctx = fake_context(FakeBot(), requests={7: request})

    ok = asyncio.run(ctx.set_request_channel_membership(7, ChannelMembership.MANUALLY_CONFIRMED, confirmed_by=99))

    assert ok
    assert request.channel_membership == ChannelMembership.MANUALLY_CONFIRMED
    assert request.channel_membership_confirmed_by == 99
    (query, params), = calls
    assert "SET channel_membership = $1, channel_membership_confirmed_by = $2" in query
    assert params == ["manually_confirmed", 99, 7]


def test_set_membership_leaves_cache_alone_if_db_fails(monkeypatch):
    _patch_db(monkeypatch, result=False)
    request = make_request(channel_membership=ChannelMembership.UNVERIFIED)
    ctx = fake_context(FakeBot(), requests={7: request})

    assert not asyncio.run(ctx.set_request_channel_membership(7, ChannelMembership.MEMBER))
    assert request.channel_membership == ChannelMembership.UNVERIFIED


# ---------- pannello admin ----------

@pytest.mark.parametrize("membership, status, shown", [
    (ChannelMembership.UNVERIFIED, RequestStatus.PENDING, True),
    (ChannelMembership.NOT_MEMBER, RequestStatus.EXAMINING, True),
    (ChannelMembership.UNVERIFIED, RequestStatus.COMPLETED, False),   # niente da decidere
    (ChannelMembership.MEMBER, RequestStatus.PENDING, False),
    (ChannelMembership.MANUALLY_CONFIRMED, RequestStatus.PENDING, False),
    (ChannelMembership.UNKNOWN, RequestStatus.PENDING, False),        # richiesta di prima del controllo
])
def test_membership_buttons_visibility(membership, status, shown):
    request = make_request(channel_membership=membership, status=status)
    assert admin_render._shows_membership_buttons(request) is shown


def test_note_names_the_confirming_admin_escaped():
    request = make_request(channel_membership=ChannelMembership.MANUALLY_CONFIRMED, channel_membership_confirmed_by=99)
    ctx = fake_context(FakeBot(), admins={99: "Ale <3"})
    note = admin_render._get_channel_membership_note(context=ctx, request=request)
    assert "Ale &lt;3" in note


def test_note_is_empty_for_verified_and_legacy_requests():
    ctx = fake_context(FakeBot())
    for membership in (ChannelMembership.MEMBER, ChannelMembership.UNKNOWN):
        request = make_request(channel_membership=membership)
        assert admin_render._get_channel_membership_note(context=ctx, request=request) == ""


class FakeQuery:
    def __init__(self):
        self.answers = []

    async def answer(self, text=None, show_alert=False):
        self.answers.append(text)


def run_op(ctx, request, op):
    query = FakeQuery()
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=99))
    asyncio.run(handle.handle_membership_op(update=update, context=ctx, request=request, op=op))
    return query.answers


def test_stale_confirm_does_not_overwrite_who_confirmed(monkeypatch):
    calls = _patch_db(monkeypatch, result=True)
    request = make_request(channel_membership=ChannelMembership.MANUALLY_CONFIRMED, channel_membership_confirmed_by=1)
    ctx = fake_context(FakeBot(), requests={7: request})

    run_op(ctx, request, AdminRequestManagementRoute.CONFIRM_MEMBERSHIP)

    assert request.channel_membership_confirmed_by == 1
    assert calls == []


def test_reverify_still_failing_changes_nothing(monkeypatch):
    calls = _patch_db(monkeypatch, result=True)
    request = make_request(channel_membership=ChannelMembership.UNVERIFIED)
    ctx = fake_context(FakeBot(error=NetworkError("down")), requests={7: request})

    run_op(ctx, request, AdminRequestManagementRoute.VERIFY_MEMBERSHIP)

    assert request.channel_membership == ChannelMembership.UNVERIFIED
    assert calls == []


def test_reverify_member_clears_the_warning(monkeypatch):
    _patch_db(monkeypatch, result=True)
    request = make_request(channel_membership=ChannelMembership.UNVERIFIED)
    ctx = fake_context(FakeBot(result=ChatMemberMember(user=USER)), requests={7: request})

    run_op(ctx, request, AdminRequestManagementRoute.VERIFY_MEMBERSHIP)

    assert request.channel_membership == ChannelMembership.MEMBER
    assert not admin_render._shows_membership_buttons(request)


def test_manual_confirm_records_the_admin(monkeypatch):
    _patch_db(monkeypatch, result=True)
    request = make_request(channel_membership=ChannelMembership.NOT_MEMBER)
    ctx = fake_context(FakeBot(), requests={7: request})

    run_op(ctx, request, AdminRequestManagementRoute.CONFIRM_MEMBERSHIP)

    assert request.channel_membership == ChannelMembership.MANUALLY_CONFIRMED
    assert request.channel_membership_confirmed_by == 99


# ---------- bottone link ----------

def test_url_button_has_no_callback_data():
    panel = Panel(PanelConfig(text="x", keyboard=[[
        ButtonItem(text="📢 Vai al Canale", url="https://t.me/+abc"),
        ButtonItem(text="🔄 Riprova", callback_key="confirm"),
    ]]))
    (link, retry), = panel.build_keyboard(fallback="fallback")
    assert link.url == "https://t.me/+abc" and link.callback_data is None
    assert retry.callback_data == "confirm" and retry.url is None
