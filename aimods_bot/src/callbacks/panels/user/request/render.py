from telegram import Update

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import RequestCooldown
from aimods_bot.src.helpers.constants.constants import LOCAL_TZ, EMOJI_HOURGLASS, EMOJI_CHECKMARK, EMOJI_DOT_ORANGE, \
    DATETIME_FORMAT, EMOJI_QUESTION_RED, EMOJI_WARNING, EMOJI_ESCLAMATION_RED, EMOJI_DOT_BLUE, Platform, \
    CATEGORY_DETAILS
from aimods_bot.src.helpers.constants.conversation_paths.navigation import GlobalAction
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import ButtonItem
from aimods_bot.src.helpers.utils.request_utils import get_platform_categories
from aimods_bot.src.helpers.utils.telegram_utils import create_and_render_panel
from aimods_bot.src.helpers.utils.time_utils import get_duration_text


async def render_user_has_cooldown_panel(
        update: Update,
        context: CustomContext,
        rc: RequestCooldown
) -> None:
    """Renderizza il pannello che informa l'utente del cooldown attivo."""
    cooldown_secs = int(context.pydb.configuration.settings.request.cooldown.total_seconds())
    cooldown_text = get_duration_text(cooldown_secs, with_emoji=False)
    cooldown_end = rc.until.astimezone(LOCAL_TZ).strftime(DATETIME_FORMAT)

    await create_and_render_panel(
        update=update,
        context=context,
        base_path="user/add_request",
        text=_get_user_has_cooldown_panel_text(cooldown_end, cooldown_text),
        keyboard=[[BACK_BUTTON]]
    )


def _get_user_has_cooldown_panel_text(cooldown_end: str, cooldown_text: str):
    return (
        f"{EMOJI_HOURGLASS} <b>Hai già formulato una richiesta.</b>\n\n"
        f"<blockquote>{EMOJI_CHECKMARK} Dopo ogni richiesta, ciascun utente deve attendere "
        f"{cooldown_text}.</blockquote>\n\n"
        f"{EMOJI_DOT_ORANGE} <b>Termine Cooldown</b> — <i>{cooldown_end}</i>"
    )


async def render_user_request_platform_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder
):
    await create_and_render_panel(
        update=update,
        context=context,
        base_path=base_path,
        text=_get_user_request_panel_text(),
        keyboard=[
            [
                ButtonItem(text="🤖 Android", callback_key=base_path.add(Platform.ANDROID)),
                ButtonItem(text="💻 Windows", callback_key=base_path.add(Platform.WINDOWS)),
            ],
            [
                ButtonItem(text="🍏 iOS", callback_key=base_path.add(Platform.IOS)),
                ButtonItem(text="🖥 MacOS", callback_key=base_path.add(Platform.MACOS))
            ],
            [ButtonItem(text="🔙 Indietro", callback_key=base_path.back())]
        ]
    )


def _get_user_request_panel_text():
    return (
        f"{EMOJI_QUESTION_RED} <b>Nuova Richiesta</b>\n\n"
        f"{EMOJI_DOT_BLUE} Per <b>quale piattaforma</b> vorresti formulare la richiesta?"
    )


async def render_user_request_category_panel(
        update: Update,
        context: CustomContext,
        base_path: PathBuilder,
        platform: Platform
):
    category = get_platform_categories(platform=platform)
    category_items = CATEGORY_DETAILS[platform.value]


async def render_user_cant_request_panel(update: Update, context: CustomContext, reason: str):
    await create_and_render_panel(
        update=update,
        context=context,
        base_path="user/view_requests",
        text=_get_user_cant_request_text(reason),
        keyboard=[
            [ButtonItem(text="🔙 Indietro", callback_key=None)]
        ]
    )


def _get_user_cant_request_text(reason: str):
    return (
        f"{EMOJI_WARNING} <b>Nuova Richiesta</b>\n\n"
        f"{EMOJI_ESCLAMATION_RED} Non puoi effettuare una nuova richiesta al momento.\n\n"
        f"▪ <b>Motivo</b> – {reason}"
    )


async def render_cant_request_panel(update: Update, context: CustomContext, message: str):
    await create_and_render_panel(
        update=update,
        context=context,
        base_path="user/add_request",
        text=message,
        keyboard=[
            [ButtonItem(
                text="🔙 Indietro",
                callback_key="user/add_request",
                override_path_generation=True
            )]
        ]
    )
