from telegram.ext import ConversationHandler

from aimods_bot.src.helpers.constants.conversation_states import (
    RequestConversationState as RCS,
    PrivateConversationState as PCS
)


class RequestStates:
    """Stati comuni per le richieste"""

    BASE_INPUT = [
        RCS.REQUEST_NAME,
        RCS.REQUEST_VERSION,
    ]

    WITH_LINK = BASE_INPUT + [RCS.REQUEST_LINK]

    WITH_FUNCTIONALITIES = BASE_INPUT + [RCS.REQUEST_FUNCTIONALITIES]

    FULL = [
        RCS.REQUEST_NAME,
        RCS.REQUEST_LINK,
        RCS.REQUEST_VERSION,
        RCS.REQUEST_FUNCTIONALITIES,
    ]

    EDIT_STATES = [
        RCS.EDIT_NAME,
        RCS.EDIT_LINK,
        RCS.EDIT_VERSION,
        RCS.EDIT_FUNCTIONALITIES,
    ]


class HandlerType:
    """Tipi di handler con configurazioni specifiche"""

    WINDOWS_GAME = {
        'name': 'windows_request_game_conversation',
        'platform': 'windows',
        'category': 'game',
        'input_states': RequestStates.FULL,
        'confirmation_states': [RCS.REQUEST_STEAMTOOLS],
        'use_edit_link': True,
    }

    WINDOWS_ADOBE = {
        'name': 'windows_adobe_request_conversation',
        'platform': 'windows',
        'category': 'adobe',
        'input_states': RequestStates.WITH_FUNCTIONALITIES,
        'confirmation_states': [RCS.REQUEST_ARCH],
        'use_edit_link': True,
    }

    WINDOWS_DAW = {
        'name': 'windows_daw_request_conversation',
        'platform': 'windows',
        'category': 'daw',
        'input_states': RequestStates.WITH_LINK,
        'confirmation_states': [],
        'transition_callback': 'recheck_request',
        'use_edit_link': True,
    }

    WINDOWS_SOFTWARE = {
        'name': 'windows_software_request_conversation',
        'platform': 'windows',
        'category': 'software',
        'input_states': RequestStates.FULL,
        'confirmation_states': [],
        'transition_callback': 'recheck_request',
        'use_edit_link': True,
    }

    MACOS_DAW = {
        'name': 'macos_request_daw_conversation',
        'platform': 'macos',
        'category': 'daw',
        'input_states': RequestStates.WITH_LINK,
        'confirmation_states': [],
        'transition_callback': 'recheck_request',
        'use_edit_link': True,
    }

    MACOS_SOFTWARE = {
        'name': 'macos_request_software_conversation',
        'platform': 'macos',
        'category': 'software',
        'input_states': RequestStates.FULL,
        'confirmation_states': [],
        'transition_callback': 'recheck_request',
        'use_edit_link': True,
    }

    ANDROID = {
        'name': 'android_request_conversation',
        'platform': 'android',
        'category': 'app',
        'input_states': RequestStates.FULL,
        'transition_callback': 'recheck_request',
        'use_edit_link': True,
        'handler_type': 'standalone'
    }

    IOS = {
        'name': 'ios_request_conversation',
        'platform': 'ios',
        'category': 'app',
        'input_states': RequestStates.FULL,
        'transition_callback': 'recheck_request',
        'use_edit_link': True,
        'handler_type': 'standalone'
    }


class ParentHandlerConfig:
    """Configurazione per handler parent (che contengono nested handlers)"""

    WINDOWS = {
        'name': 'windows_request_conversation',
        'platform': 'windows',
        'nested_handlers': [
            HandlerType.WINDOWS_GAME,
            HandlerType.WINDOWS_ADOBE,
            HandlerType.WINDOWS_DAW,
            HandlerType.WINDOWS_SOFTWARE,
        ],
        'map_to_parent': {
            RCS.MAIN_BACKER: PCS.NEW_REQUEST,
            RCS.REQUEST_SUBMITTED: PCS.USER_CONVERSATION,
            ConversationHandler.END: PCS.USER_CONVERSATION,
        }
    }

    MACOS = {
        'name': 'macos_request_conversation',
        'platform': 'macos',
        'nested_handlers': [
            HandlerType.MACOS_DAW,
            HandlerType.MACOS_SOFTWARE,
        ],
        'map_to_parent': {
            RCS.MAIN_BACKER: PCS.NEW_REQUEST,
            ConversationHandler.END: PCS.USER_CONVERSATION,
        }
    }
