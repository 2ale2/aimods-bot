from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters, PrefixHandler
from aimods_bot.src.callbacks.commands.general.start_command import exit_nested_conversations
from aimods_bot.src.callbacks.panels.user import user_main_router
from aimods_bot.src.callbacks.panels.user.request.request import (
    request_detail, recheck_request, confirm_request, 
    edit_request_detail, edited_detail, backer
)
from aimods_bot.src.callbacks.panels.user.request.route import request_category, request_router
from aimods_bot.src.helpers.constants.conversation_states import (
    RequestConversationState as RCS,
    PrivateConversationState as PCS
)
from aimods_bot.src.handlers.conversations.patterns_constants import CallbackPatterns, EntryPatterns, PrefixCommands


class StateBuilder:
    """Costruisce gli stati per i conversation handlers"""

    @staticmethod
    def create_input_state(callback=request_detail, use_url=False):
        """Crea uno stato per input testuale o URL"""
        filter_type = filters.Entity("url") if use_url else filters.TEXT
        return [MessageHandler(filters=filter_type & (~filters.COMMAND), callback=callback)]

    @staticmethod
    def create_confirmation_state(callback=recheck_request):
        """Crea uno stato per conferma con bottoni bool_"""
        return [CallbackQueryHandler(pattern=CallbackPatterns.BOOL_ONLY, callback=callback)]

    @staticmethod
    def create_check_state():
        """Crea lo stato CHECK_REQUEST standard"""
        return [
            CallbackQueryHandler(pattern=CallbackPatterns.CONFIRM_REQUEST, callback=confirm_request),
            CallbackQueryHandler(pattern=CallbackPatterns.EDIT_OR_BOOL, callback=edit_request_detail),
        ]

    @staticmethod
    def create_check_state_edit_only():
        """Crea lo stato CHECK_REQUEST solo con edit (senza bool)"""
        return [
            CallbackQueryHandler(pattern=CallbackPatterns.CONFIRM_REQUEST, callback=confirm_request),
            CallbackQueryHandler(pattern=CallbackPatterns.EDIT_ONLY, callback=edit_request_detail),
        ]

    @staticmethod
    def create_edit_states(use_link=True):
        """Crea tutti gli stati di editing"""
        states = {
            RCS.EDIT_NAME: StateBuilder.create_input_state(callback=edited_detail),
            RCS.EDIT_VERSION: StateBuilder.create_input_state(callback=edited_detail),
            RCS.EDIT_FUNCTIONALITIES: StateBuilder.create_input_state(callback=edited_detail),
        }

        if use_link:
            states[RCS.EDIT_LINK] = StateBuilder.create_input_state(callback=edited_detail, use_url=True)

        return states


class FallbackBuilder:
    """Costruisce i fallbacks comuni"""

    @staticmethod
    def create_standard_fallbacks(include_back_category=True):
        """Crea i fallbacks standard per nested handlers"""
        fallbacks = [
            CallbackQueryHandler(pattern=CallbackPatterns.RESET_CONVERSATION, callback=user_main_router),
            CallbackQueryHandler(pattern=CallbackPatterns.BACK_NOT_CATEGORY, callback=backer),
        ]

        if include_back_category:
            fallbacks.append(
                CallbackQueryHandler(pattern=CallbackPatterns.BACK_CATEGORY, callback=request_category)
            )

        fallbacks.append(
            PrefixHandler(
                prefix=PrefixCommands.PREFIXES,
                command=PrefixCommands.START,
                callback=exit_nested_conversations
            )
        )

        return fallbacks

    @staticmethod
    def create_parent_fallbacks():
        """Crea i fallbacks per handler parent"""
        return [
            CallbackQueryHandler(pattern=CallbackPatterns.RESET_CONVERSATION, callback=user_main_router),
            CallbackQueryHandler(pattern=CallbackPatterns.BACK_CATEGORY, callback=request_category),
            CallbackQueryHandler(pattern=CallbackPatterns.BACK_ANY, callback=backer),
            PrefixHandler(
                prefix=PrefixCommands.PREFIXES,
                command=PrefixCommands.START,
                callback=exit_nested_conversations
            )
        ]


class HandlerCategory:
    """Categorie di handler"""
    NESTED = "nested"  # Handler dentro un parent (es: windows_game dentro windows)
    STANDALONE = "standalone"  # Handler indipendente (es: android, ios)
    PARENT = "parent"  # Handler che contiene altri handler


class RequestHandlerFactory:
    """Factory principale per creare conversation handlers"""

    @staticmethod
    def create_nested_handler(config: dict) -> ConversationHandler:
        """
        Crea un conversation handler nested basato sulla configurazione.

        Args:
            config: Dict con chiavi:
                - name: nome del handler
                - platform: piattaforma (windows, macos, etc)
                - category: categoria (game, adobe, etc)
                - input_states: lista di stati input da creare
                - confirmation_states: lista di stati con conferma bool
                - transition_callback: callback per transizione (default: request_detail)
                - use_edit_link: se includere EDIT_LINK negli stati
                - map_to_parent_override: override per map_to_parent
        """
        name = config['name']
        platform = config['platform']
        category = config['category']
        input_states = config['input_states']
        confirmation_states = config.get('confirmation_states', [])
        transition_callback_name = config.get('transition_callback', 'request_detail')
        use_edit_link = config.get('use_edit_link', True)

        # Determina il callback di transizione
        transition_callback = recheck_request if transition_callback_name == 'recheck_request' else request_detail

        entry_points = [
            CallbackQueryHandler(
                pattern=EntryPatterns.from_notification(platform, category),
                callback=user_main_router
            ),
            CallbackQueryHandler(
                pattern=EntryPatterns.category_direct(category),
                callback=request_router
            )
        ]

        states = {}

        # Stati di input
        for i, state in enumerate(input_states):
            is_last_input = (i == len(input_states) - 1) and not confirmation_states
            callback = transition_callback if is_last_input else request_detail

            if state == RCS.REQUEST_LINK:
                states[state] = StateBuilder.create_input_state(callback=callback, use_url=True)
            else:
                states[state] = StateBuilder.create_input_state(callback=callback)

        for state in confirmation_states:
            states[state] = StateBuilder.create_confirmation_state()

        if confirmation_states:
            states[RCS.CHECK_REQUEST] = StateBuilder.create_check_state()
        else:
            states[RCS.CHECK_REQUEST] = StateBuilder.create_check_state_edit_only()

        states.update(StateBuilder.create_edit_states(use_link=use_edit_link))

        # Map to parent - SOLO per handler veramente nested
        map_to_parent = {
            RCS.REQUEST_SUBMITTED: ConversationHandler.END,
            RCS.MAIN_BACKER: RCS.MAIN_BACKER,
            RCS.CANCEL_PROCESS: RCS.REQUEST_CATEGORY,
            ConversationHandler.END: ConversationHandler.END
        }

        return ConversationHandler(
            entry_points=entry_points,
            states=states,
            fallbacks=FallbackBuilder.create_standard_fallbacks(),
            map_to_parent=map_to_parent,
            name=name,
            allow_reentry=True,
            persistent=True
        )

    @staticmethod
    def create_standalone_handler(config: dict) -> ConversationHandler:
        """
        Crea un conversation handler standalone (né nested né parent).
        Usato per Android e iOS che non hanno sub-categorie.

        Args:
            config: Dict con configurazione simile a nested_handler
        """
        name = config['name']
        platform = config['platform']
        category = config['category']
        input_states = config['input_states']
        transition_callback_name = config.get('transition_callback', 'request_detail')
        use_edit_link = config.get('use_edit_link', True)

        # Determina il callback di transizione
        transition_callback = recheck_request if transition_callback_name == 'recheck_request' else request_detail

        # Entry points
        entry_points = [
            CallbackQueryHandler(
                pattern=EntryPatterns.from_notification(platform, category),
                callback=user_main_router
            ),
            CallbackQueryHandler(
                pattern=EntryPatterns.platform_base(platform),
                callback=request_category
            )
        ]

        states = {}

        for i, state in enumerate(input_states):
            is_last_input = (i == len(input_states) - 1)
            callback = transition_callback if is_last_input else request_detail

            if state == RCS.REQUEST_LINK:
                states[state] = StateBuilder.create_input_state(callback=callback, use_url=True)
            else:
                states[state] = StateBuilder.create_input_state(callback=callback)

        states[RCS.CHECK_REQUEST] = StateBuilder.create_check_state_edit_only()

        states.update(StateBuilder.create_edit_states(use_link=use_edit_link))

        # Map to parent - STANDALONE va direttamente agli stati del parent principale
        map_to_parent = {
            RCS.MAIN_BACKER: PCS.NEW_REQUEST,
            ConversationHandler.END: PCS.USER_CONVERSATION
        }

        return ConversationHandler(
            entry_points=entry_points,
            states=states,
            fallbacks=FallbackBuilder.create_standard_fallbacks(include_back_category=False),
            map_to_parent=map_to_parent,
            name=name,
            persistent=True,
            allow_reentry=True
        )

    @staticmethod
    def create_parent_handler(config: dict, nested_handlers: list) -> ConversationHandler:
        """
        Crea un conversation handler parent che contiene nested handlers.

        Args:
            config: Dict con configurazione del parent
            nested_handlers: Lista di ConversationHandler nested
        """
        name = config['name']
        platform = config['platform']
        map_to_parent = config['map_to_parent']

        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    pattern=EntryPatterns.platform_base(platform),
                    callback=request_category
                )
            ],
            states={
                RCS.REQUEST_CATEGORY: nested_handlers,
            },
            fallbacks=FallbackBuilder.create_parent_fallbacks(),
            map_to_parent=map_to_parent,
            name=name,
            persistent=True
        )
