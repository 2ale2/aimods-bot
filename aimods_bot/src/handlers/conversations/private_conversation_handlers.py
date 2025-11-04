"""
Private conversation handlers ottimizzati.
Semplifica la struttura usando helper functions e riducendo duplicazione.
"""

from telegram.ext import CallbackQueryHandler, ConversationHandler, PrefixHandler, MessageHandler, filters
from aimods_bot.src.callbacks.commands.general.start_command import start
from aimods_bot.src.callbacks.panels.admin import admin_main_router
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.links.list.handle import (
    handle_user_input as handler_user_input_links
)
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.handle import (
    handle_user_input_antispam_whitelist
)
from aimods_bot.src.callbacks.panels.admin.moderation.antispam.whitelist.route import (
    antispam_whitelist_backer
)
from aimods_bot.src.callbacks.panels.admin.moderation.punishment.handle import (
    set_punishment_duration
)
from aimods_bot.src.callbacks.panels.admin.requests_management.handle import (
    handle_request_rejection_reason, handle_user_archive_identifier
)
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.render import (
    render_handled_request_limitation_duration_panel,
    render_admin_user_limitation_confirmed_panel,
    handle_limitation_identifier
)
from aimods_bot.src.callbacks.panels.admin.requests_management.limit.route import (
    route_admin_limit_user_request
)
from aimods_bot.src.callbacks.panels.user import user_main_router
from aimods_bot.src.handlers.conversations.patterns_constants import CallbackPatterns, PrefixCommands
from aimods_bot.src.handlers.conversations.request_handlers import (
    android_request_handler, windows_request_handler,
    ios_request_handler, macos_request_handler,
    windows_game_request_handler, windows_adobe_request_handler,
    windows_software_request_handler, windows_daw_request_handler,
    macos_daw_request_handler, macos_software_request_handler
)
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.filters import ChatSharedFilter
from aimods_bot.src.helpers.utils.alerts import open_private_alert
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete_wrapper

# ===== FILTERS E HANDLER COMUNI =====

chat_shared_filter = ChatSharedFilter()

alert_handler = CallbackQueryHandler(
    callback=open_private_alert,
    pattern=CallbackPatterns.ALERT
)

close_button_handler = CallbackQueryHandler(
    pattern=CallbackPatterns.CLOSE_MENU,
    callback=safe_delete_wrapper
)


# ===== HELPER FUNCTIONS =====

def create_text_input_state(callback_func, include_admin_router=True):
    """
    Crea uno stato standard per input testuale con admin router.

    Args:
        callback_func: Callback principale per l'input testuale
        include_admin_router: Se includere CallbackQueryHandler per admin router
    """
    handlers = [
        MessageHandler(filters=filters.TEXT, callback=callback_func),
        close_button_handler
    ]

    if include_admin_router:
        handlers.append(
            CallbackQueryHandler(
                pattern=CallbackPatterns.NOT_CLOSE_MENU,
                callback=admin_main_router
            )
        )

    return handlers


def get_user_request_handlers():
    """Restituisce tutti gli handler per le richieste utente"""
    return [
        # Nested handlers individuali per accesso diretto da notifiche
        android_request_handler,
        windows_game_request_handler,
        windows_adobe_request_handler,
        windows_software_request_handler,
        windows_daw_request_handler,
        ios_request_handler,
        macos_daw_request_handler,
        macos_software_request_handler,
        # Router generale per user panel
        CallbackQueryHandler(
            pattern=CallbackPatterns.NOT_CLOSE_AND_NOT_FROM_NOTIFICATION,
            callback=user_main_router
        ),
        close_button_handler
    ]


def get_new_request_handlers():
    """Restituisce gli handler per nuove richieste (parent handlers)"""
    return [
        android_request_handler,
        windows_request_handler,
        ios_request_handler,
        macos_request_handler
    ]


# ===== ADMIN STATES =====
# Stati amministrativi raggruppati per tipologia

ADMIN_TEXT_INPUT_STATES = {
    PCS.SET_PUNISHMENT_DURATION: create_text_input_state(set_punishment_duration),

    PCS.SET_REQUEST_LIMITATION_DURATION: create_text_input_state(
        render_handled_request_limitation_duration_panel
    ),

    PCS.SET_REQUEST_LIMITATION_REASON: [
        MessageHandler(filters=filters.TEXT, callback=render_admin_user_limitation_confirmed_panel),
        CallbackQueryHandler(callback=admin_main_router)
    ],

    PCS.SET_REQUEST_LIMITATION_USER: create_text_input_state(route_admin_limit_user_request),

    PCS.SET_REQUEST_REJECTION_REASON: create_text_input_state(handle_request_rejection_reason),

    PCS.SET_VIEW_REQUEST_LIMITATION_USER: create_text_input_state(handle_limitation_identifier),

    PCS.SET_USER_FOR_REQUEST_ARCHIVE: create_text_input_state(handle_user_archive_identifier),
}


# ===== CONVERSATION HANDLER PRINCIPALE =====

private_conversation_handler = ConversationHandler(
    entry_points=[
        PrefixHandler(
            prefix=PrefixCommands.PREFIXES,
            command=PrefixCommands.START,
            callback=start,
            filters=filters.ChatType.PRIVATE
        )
    ],
    states={
        # User conversation
        PCS.USER_CONVERSATION: get_user_request_handlers(),

        # Admin conversation
        PCS.ADMIN_CONVERSATION: [
            CallbackQueryHandler(
                pattern=CallbackPatterns.NOT_CLOSE_MENU,
                callback=admin_main_router
            ),
            close_button_handler
        ],

        # Stati per input testuale admin (raggruppati)
        **ADMIN_TEXT_INPUT_STATES,

        # Stati speciali antispam
        PCS.EDIT_ANTISPAM_LINK_LIST: [
            MessageHandler(filters=filters.TEXT, callback=handler_user_input_links),
            close_button_handler,
            CallbackQueryHandler(
                pattern=CallbackPatterns.NOT_CLOSE_MENU,
                callback=admin_main_router
            )
        ],

        PCS.ADD_ANTISPAM_MENTION_WHITELIST: [
            MessageHandler(
                filters=filters.Text(["🔙 Indietro", "indietro", "Indietro"]),
                callback=antispam_whitelist_backer
            ),
            MessageHandler(
                filters=chat_shared_filter,
                callback=handle_user_input_antispam_whitelist
            )
        ],

        PCS.REMOVE_ANTISPAM_MENTION_WHITELIST: [
            MessageHandler(filters=filters.TEXT, callback=handle_user_input_antispam_whitelist),
            CallbackQueryHandler(callback=admin_main_router)
        ],

        # Nuove richieste (parent handlers)
        PCS.NEW_REQUEST: get_new_request_handlers(),
    },
    fallbacks=[
        CallbackQueryHandler(callback=user_main_router),
        PrefixHandler(
            prefix=PrefixCommands.PREFIXES,
            command=PrefixCommands.START,
            callback=start
        )
    ],
    allow_reentry=False,
    name="private_conversation",
    persistent=True
)


# ===== ESPORTAZIONE =====

__all__ = [
    'private_conversation_handler',
    'alert_handler',
    'close_button_handler',
]