from telegram import Update
from telegram.ext import ConversationHandler

from aimods_bot.src.helpers.constants.conversation_paths.navigation import GlobalAction, AdminRoute, UserRoute

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.models.routing import PathBuilder
from aimods_bot.src.helpers.models.ui import Panel, PanelConfig, ButtonItem
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete, get_banned_panel
from aimods_bot.src.helpers.utils.user_utils import user_is_banned

log = logger.getChild("start_command")


async def get_panel(update: Update, context: CustomContext, admin: bool, banned: bool):
    fn = update.effective_user.first_name
    if banned:
        return get_banned_panel()
    if admin:
        path = PathBuilder(AdminRoute.ROOT)

        return Panel(
            PanelConfig(
                base_path=path,
                text=("🎛 <b>Pannello di Controllo</b>\n\n"
                      f"▫️ Ciao {fn}! Questo è il pannello di controllo "
                      f"per l'amministrazione del canale e del gruppo.\n\n"
                      "🔹 Scegli un'opzione per cominciare."),
                keyboard=[
                    [
                        ButtonItem(text="♟ Moderazione", callback_key=path.add(AdminRoute.MODERATION)),
                        ButtonItem(text="⚙ Impostazioni", callback_key=path.add(AdminRoute.SETTINGS))
                    ],
                    [
                        ButtonItem(text="❔ Gestione Richieste", callback_key=path.add(AdminRoute.REQUESTS)),
                        ButtonItem(text="🔐 Chiudi", callback_key=GlobalAction.CLOSE)
                    ]
                ],
            )
        )
    else:
        path = PathBuilder(UserRoute.ROOT)

        return Panel(
            PanelConfig(
                base_path=path,
                text=("🌍 <b>Pannello Utente</b>\n\n"
                      f"▫️ Ciao {fn}! Questo è il tuo pannello utente. Qui potrai gestire le tue richieste.\n\n"
                      "➕ <u>In futuro tante altre funzionalità</u>.\n\n"
                      "🔹 Scegli un'opzione per cominciare."),
                keyboard=[
                    [
                        ButtonItem(text="👁 Visiona Richieste", callback_key=path.add(UserRoute.VIEW_REQUESTS)),
                        ButtonItem(
                            text=f"{'❔' if not context.user_request_cooldown() else '⏳'} Formula Richiesta",
                            callback_key=path.add(UserRoute.ADD_REQUEST)
                        )
                    ],
                    [ButtonItem(text="⚙ Impostazioni", callback_key=path.add(UserRoute.SETTINGS))],
                    [ButtonItem(text="🔐 Chiudi", callback_key=GlobalAction.CLOSE)]
                ]
            )
        )


async def start(update: Update, context: CustomContext):
    if not update.callback_query:
        await safe_delete(update=update, context=context)
    else:
        log.info(f"Callback data from {update.effective_user.id}: {update.callback_query.data}")

    user = update.effective_user
    admin = context.is_user_admin
    banned = False

    if not admin and await user_is_banned(context=context, user_id=user.username or user.id):
        banned = True

    panel = await get_panel(update=update, context=context, admin=admin, banned=banned)
    await panel.render(update=update, context=context, message_id=update.effective_message.id)

    return PCS.ADMIN_CONVERSATION if admin else (PCS.USER_CONVERSATION if not banned else ConversationHandler.END)


async def exit_nested_conversations(update: Update, context: CustomContext):
    log.info(f"User {update.effective_user.id} exiting the conv...")
    await start(update=update, context=context)
    return ConversationHandler.END
