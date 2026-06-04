from enum import StrEnum


class GlobalAction(StrEnum):
    MAIN_MENU = "main_menu"
    BACK = "back"
    CLOSE_MENU = "close_menu"

    YES = "yes"
    NO = "no"

    CONFIRM = "confirm"

    OPEN = "open"
    CLOSE = "close"

    TOGGLE_ON = "toggle_on"
    TOGGLE_OFF = "toggle_off"

    REQUEST_WIZARD_BACK = "request_wizard_back"


class NotificationAction(StrEnum):
    FROM_NOTIFICATION = "from_notification"
