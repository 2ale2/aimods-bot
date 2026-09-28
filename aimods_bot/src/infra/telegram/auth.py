from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aimods_bot.src.core.customcontext import CustomContext


def is_admin(user_id: int, context: CustomContext) -> bool:
    """Verifica se l'utente è un admin del gruppo."""
    return user_id in context.pydb.admins
