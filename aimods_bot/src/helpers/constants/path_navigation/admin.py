from enum import StrEnum


class AdminRoute(StrEnum):
    ROOT = "admin"

    MODERATION = "moderation"
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_REQUESTS = "manage_requests"


class AdminSettingsRoute(StrEnum):
    # admin/settings
    NOTIFICATIONS = "notifications"


class AdminSettingsNotificationsRoute(StrEnum):
    # admin/settings/notifications
    NEW_REQUESTS = "new_requests"
    SECTION_CLOSING = "section_closing"


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


class LimitationsAction(StrEnum):
    # admin/manage_requests/manage_limitations
    REMOVE_LIMITATIONS = "remove_limitations"
    VIEW_LIMITATIONS = "view_limitations"
    LIMIT_USER_REQUESTS = "limit_user_requests"


class LimitationsOp(StrEnum):
    LIMIT = "limit"
    VIEW = "view"
    REMOVE = "remove"
    ADD = "add"
    USER_ID = "user_id"


class LimitationsFlow(StrEnum):
    # add flow — .../manage_limitations/<user_id>/add
    DURATION = "duration"
    SECTIONS = "sections"
    REASON = "reason"

    DURATION_ENDLESS = "endless"

    BLOCK_ALL = "block_all"
    UNBLOCK_ALL = "unblock_all"

    # remove flow — .../manage_limitations/<user_id>/remove
    REMOVE_ALL = "remove_all"

