"""Navigation route segments for inline-panel callback paths."""

from .common import (
    GlobalAction,
    NotificationAction,
)
from .user import (
    UserRoute,
    UserManageSettingsRoute,
    UserManageRequestsRoute,
)
from .admin import (
    AdminRoute,
    AdminSettingsRoute,
    AdminSettingsNotificationsRoute,
    AdminRequestsRoute,
    AdminRequestManagementRoute,
    LimitationsAction,
    LimitationsOp,
    LimitationsFlow,
)
from .moderation import (
    ModerationRoute,
    SecurityFiltersRoute,
    ModerationListsRoute,
    AntispamRoute, PunishmentRoute,
)

__all__ = [
    # common
    "GlobalAction",
    "NotificationAction",
    # user
    "UserRoute",
    "UserManageSettingsRoute",
    "UserManageRequestsRoute",
    # admin
    "AdminRoute",
    "AdminSettingsRoute",
    "AdminSettingsNotificationsRoute",
    "AdminRequestsRoute",
    "AdminRequestManagementRoute",
    "LimitationsAction",
    "LimitationsOp",
    "LimitationsFlow",
    # moderation
    "ModerationRoute",
    "SecurityFiltersRoute",
    "ModerationListsRoute",
    "AntispamRoute",
    "PunishmentRoute",
]