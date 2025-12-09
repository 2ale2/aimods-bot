import re
from typing import Literal, Optional

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import Platform, Category
from aimods_bot.src.helpers.utils.file_utils import save_yaml_configuration
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.telegram_utils import get_config

log = logger.getChild(__name__)


def _remove_limitation_jobs(context: CustomContext, user_id: int, section_pattern: str):
    """Rimuove i job schedulati che corrispondono al pattern."""
    job_name_pattern = rf"^request_limit:{user_id}:{section_pattern}$"
    jobs = context.job_queue.get_jobs_by_name(job_name_pattern)

    for job in jobs:
        log.info(f"Removing scheduled job {job.name} for user {user_id}")
        job.schedule_removal()


async def handle_request_section_toggle(
        context: CustomContext,
        platform: Platform,
        category: Category,
        action: Literal["open", "close"]
):
    is_opening = (action == "open")
    config = get_config(context, platform, category)

    if is_opening and config.limit is not None:
        active_count = len(context.get_active_category_requests(platform=platform, category=category))
        if active_count >= config.limit:
            config.limit = None

    config.toggle = is_opening
    await save_yaml_configuration(context=context)

    log.info(f"Request Section {category.value} ({platform.value}) "
             f"toggled {'on' if is_opening else 'off'} by {context.user_id}")


async def handle_request_section_limit(
        context: CustomContext,
        platform: Platform,
        category: Category,
        limit: int
):
    config = get_config(context, platform, category)

    config.limit = limit if limit != 0 else None

    if config.limit is not None:
        active_count = len(context.get_active_category_requests(platform=platform, category=category))
        if active_count >= config.limit:
            config.toggle = False

    await save_yaml_configuration(context=context)

    log.info(f"Request Section {category.value} ({platform.value}) Limit settled to "
             f"{config.limit if config.limit else 'unlimited'} by {context.user_id}")


async def handle_remove_user_request_limitation(
        context: CustomContext,
        user_id: int,
        section: Optional[str],
        remove_all: bool = False
):
    """
    Rimuove le limitazioni dell'utente.
    Se remove_all è False, rimuove solo la sezione specificata e il relativo job,
    senza toccare gli altri.
    """
    if remove_all:
        _remove_limitation_jobs(context, user_id, section_pattern="[^:\s]+")

        context.set_user_request_limitations(user_id=user_id, limitations=[])
        log.info(f"Admin {context.user_id} removed all section limitations from {user_id}")
        return

    current_limitations = context.get_user_request_limitations(user_id=user_id)

    new_limitations = [lim for lim in current_limitations if lim.section != section]

    if len(new_limitations) == len(current_limitations):
        return

    context.set_user_request_limitations(user_id=user_id, limitations=new_limitations)

    if section:
        safe_section = re.escape(section)
        _remove_limitation_jobs(context, user_id, section_pattern=safe_section)

    log.info(f"Admin {context.user_id} removed {section} section limitations from {user_id}")