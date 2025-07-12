from enum import Enum, auto


class AntiSpamStates(Enum):
    MAIN_PANEL = auto()
    ANTISPAM_SET_LINK = auto()
    ANTISPAM_SET_LINK_ALLOW_AFTER = auto()
    ANTISPAM_MANAGE_LINK_LIST = auto()
    ANTISPAM_EDIT_LINK_LIST = auto()
