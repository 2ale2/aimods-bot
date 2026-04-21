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


class AdminRoute(StrEnum):
    ROOT = "admin"

    MODERATION = "moderation"
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_REQUESTS = "manage_requests"


class UserRoute(StrEnum):
    ROOT = "user"

    MANAGE_SETTINGS = "manage_settings"
    VIEW_REQUESTS = "view_requests"
    ADD_REQUEST = "add_request"


class UserViewRequestsRoute(StrEnum):
    ACTIVE = "active_requests"
    DETAILS = "details"


class AdminSettingsRoute(StrEnum):
    # admin/settings
    NOTIFICATIONS = "notifications"


class AdminRequestsRoute(StrEnum):
    # admin/manage_requests
    ACTIVE = "active_requests"
    MANAGE_SECTIONS = "manage_sections"
    MANAGE_LIMITATIONS = "manage_limitations"
    USER_REQUESTS_ARCHIVE = "user_requests_archive"
    LAST_10 = "last_10"


class AdminRequestManagementRoute(StrEnum):
    # admin/manage_requests/<platform>/<catgeory>/<id>
    REMOVE = "remove"
    REJECT = "reject"
    CHANGE_STATUS = "change_status"


class AdminRequestsLimitationsRoute(StrEnum):
    # admin/manage_requests/manage_limitations
    REMOVE_LIMITATIONS = "remove_limitations"
    VIEW_LIMITATIONS = "view_limitations"
    LIMIT_USER_REQUESTS = "limit_user_requests"


class AdminManageRequestLimitationsUtils(StrEnum):
    LIMIT = "limit"
    VIEW = "view"
    REMOVE = "remove"
    ADD = "add"
    USER_ID = "user_id"


class AdminManageRequestLimitationsRoute(StrEnum):
    # admin/manage_requests/manage_limitations/<user_id>/add
    DURATION = "duration"
    SECTIONS = "sections"
    REASON = "reason"

    DURATION_ENDLESS = "endless"

    BLOCK_ALL = "block_all"
    UNBLOCK_ALL = "unblock_all"

    # admin/manage_requests/manage_limitations/<user_id>/remove
    REMOVE_ALL = "remove_all"


class AdminNotificationsRoute(StrEnum):
    # admin/settings/notifications
    NEW_REQUESTS = "new_requests"
    SECTION_CLOSING = "section_closing"


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
