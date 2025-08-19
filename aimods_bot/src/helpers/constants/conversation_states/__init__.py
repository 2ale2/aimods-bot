class PrivateConversationState:
    USER_CONVERSATION = 0
    ADMIN_CONVERSATION = 1
    SET_PUNISHMENT_DURATION = 2
    EDIT_ANTISPAM_LINK_LIST = 3
    ADD_ANTISPAM_MENTION_WHITELIST = 4
    REMOVE_ANTISPAM_MENTION_WHITELIST = 5
    NEW_REQUEST = 6


class RequestConversationState:
    class AndroidRequest:
        APP_NAME = 1
        APP_LINK = 2
        APP_VERSION = 3
        APP_FUNCTIONALITIES = 4
        CHECK_REQUEST = 5
    class WindowsRequest:
        SOFTWARE_CATEGORY = 6
        class GameRequest:
            GAME_NAME = 7
            GAME_LINK = 8
            GAME_VERSION = 9
            GAME_FUNCTIONALITIES = 10
            GAME_STEAMTOOLS = 11

    CHECK_REQUEST = 12
    EDIT_NAME = 13
    EDIT_LINK = 15
    EDIT_VERSION = 15
    EDIT_FUNCTIONALITIES = 16
    MAIN_BACKER = 17
