from enum import StrEnum


class UserRoute(StrEnum):
    ROOT = "user"

    MANAGE_SETTINGS = "manage_settings"
    VIEW_REQUESTS = "view_requests"
    ADD_REQUEST = "add_request"

    NOTIFICATION = "notification"


class UserManageSettingsRoute(StrEnum):
    NOTIFICATIONS = "notifications"

    SECTION_OPENING_NOTIFICATIONS = "section_opening_notifications"


class UserManageRequestsRoute(StrEnum):
    ACTIVE = "active_requests"
    REQUEST_ARCHIVE = "request_archive"

    DETAILS = "details"
    CANCEL = "cancel"

    ENABLE_STATUS_NOTIFICATION = "enable_notification"
    DISABLE_STATUS_NOTIFICATION = "disable_notification"

