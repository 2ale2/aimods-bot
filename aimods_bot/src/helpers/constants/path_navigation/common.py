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


class DigitRoute(StrEnum):
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
