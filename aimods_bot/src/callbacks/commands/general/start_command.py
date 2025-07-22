from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.constants.keyboards.start_keyboard import admin_keyboard_panel, user_keyboard_panel
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, render_panel
from aimods_bot.src.helpers.utils.user_utils import is_admin

log = logger.getChild("start_command")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Due funzioni: la prima per gestire il menu per non staff, l'altra per lo staff
    user_id = update.effective_user.id
    await safe_delete(update=update, context=context)

    if await is_admin(user_id=user_id, context=context):
        await _render_admin_panel(update=update, context=context)
    else:
        await _render_user_panel(update=update, context=context)


async def _render_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await render_panel(panel=admin_keyboard_panel, update=update, context=context)


async def _render_user_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await render_panel(panel=user_keyboard_panel, update=update, context=context)
