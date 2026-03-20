from enum import StrEnum


class GlobalAction(StrEnum):
    MAIN_MENU = "main_menu"
    BACK = "back"
    CLOSE = "close_menu"

class AdminRoute(StrEnum):
    ROOT = "admin"

    MODERATION = "moderation"
    SETTINGS = "manage_settings"
    REQUESTS = "manage_requests"


class UserRoute(StrEnum):
    ROOT = "user"

    SETTINGS = "manage_settings"
    VIEW_REQUESTS = "view_requests"
    ADD_REQUEST = "add_request"


class AdminSettingsRoute(StrEnum):
    # admin/settings
    NOTIFICATIONS = "notifications"


class AdminRequestsRoute(StrEnum):
    # admin/manage_requests
    ACTIVE = "active_requests"
    MANAGE_SECTIONS = "manage_sections"
    MANAGE_LIMITATIONS = "manage_limitations"
    USER_ARCHIVE = "user_archive"
    LAST_10 = "last_10"


class AdminNotificationsRoute(StrEnum):
    # admin/settings/notifications
    NEW_REQUESTS = "new_requests"
    SECTION_CLOSING ="section_closing"


class ModerationRoute(StrEnum):
    # admin/moderation
    SECURITY_FILTERS = "security_filters"
    USER_MODERATION = "user_moderation"
    MEDIA_CONTENT = "media_content"
    COMMUNITY = "community"


class SecurityFiltersRoute(StrEnum):
    # admin/moderation/security_filters
    ANTISPAM = "antispam"
    ANTIFLOOD = "antiflood"
    FORBIDDEN_WORDS = "forbidden_words"
    CHECKS = "checks"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    LENGHT = "length"


class NotificationAction(StrEnum):
    FROM_NOTIFICATION = "from_notification"