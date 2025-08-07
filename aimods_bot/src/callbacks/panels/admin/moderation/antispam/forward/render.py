from telegram import Update
from telegram.ext import CallbackContext


async def render_antispam_forward_panel(update: Update, context: CallbackContext):
    pass


def _get_text(context: CallbackContext) -> str:
    text = ""
