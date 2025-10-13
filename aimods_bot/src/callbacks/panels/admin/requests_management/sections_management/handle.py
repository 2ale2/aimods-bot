from typing import Literal, Optional

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import CategorySetting
from aimods_bot.src.helpers.constants.constants import Platform, Category
from aimods_bot.src.helpers.scheduler import schedule_request_limitation_deletion
from aimods_bot.src.helpers.utils.file_utils import save_yaml_configuration
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)


async def handle_request_section_toggle(
        context: CustomContext,
        platform: Platform,
        category: Category,
        action: Literal["open", "close"]
):
    opening = action == "open"
    config = getattr(getattr(context.pydb.configuration.settings.request, platform.value), category.value)
    assert isinstance(config, CategorySetting)

    r = len(context.get_active_category_requests(platform=platform, category=category))
    if opening and config.limit is not None and r >= config.limit:
        config.limit = None

    config.toggle = opening

    await save_yaml_configuration(context=context)

    log.info(f"Request Section {category.value} ({platform.value}) "
             f"toggled {'on' if opening else 'off'} by {context.user_id}")


async def handle_request_section_limit(
        context: CustomContext,
        platform: Platform,
        category: Category,
        limit: int
):
    config = getattr(getattr(context.pydb.configuration.settings.request, platform.value), category.value)
    config.limit = limit if limit != 0 else None

    if config.limit is not None:
        if len(context.get_active_category_requests(platform=platform, category=category)) >= config.limit:
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
    user_limitations = context.get_user_request_limitations(user_id=user_id)

    if remove_all:
        jobs = context.job_queue.get_jobs_by_name(rf"^request_limit:{user_id}:[^:\s]+$")
        for job in jobs:
            log.info(f"Removing {job.name} for {user_id} section {job.name.split(':')[2]}")
            job.schedule_removal()

        context.set_user_request_limitations(user_id=user_id, limitations=[])
        log.info(f"Admin {context.user_id} removed all section limitations from {user_id}")
        return

    new_limitations = []

    for el in user_limitations:
        if el.section == section:
            continue
        new_limitations.append(el)

    context.set_user_request_limitations(user_id=user_id, limitations=new_limitations)

    for limitation in new_limitations:
        if limitation.until is not None:
            await schedule_request_limitation_deletion(
                context=context,
                user_id=user_id,
                section=limitation.section,
                until=limitation.until
            )

    log.info(f"Admin {context.user_id} removed {section} section limitations from {user_id}")