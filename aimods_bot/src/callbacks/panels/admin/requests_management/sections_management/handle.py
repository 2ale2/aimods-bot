from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.request_section import RequestSection
from aimods_bot.src.helpers.utils.file_utils import save_yaml_configuration
from aimods_bot.src.core.config_accessor import get_section_config

log = logger.getChild(__name__)


async def handle_request_section_toggle(
        context: CustomContext,
        section: RequestSection,
        action: GlobalAction
):
    is_opening = (action == GlobalAction.OPEN)
    config = get_section_config(context=context, section=section)

    if is_opening and config.limit is not None:
        active_count = len(context.get_active_category_requests(section=section))
        if active_count >= config.limit:
            config.limit = None

    config.toggle = is_opening
    await save_yaml_configuration(context=context)

    log.info(f"Request Section {section.category.value} ({section.platform.value}) "
             f"toggled {'on' if is_opening else 'off'} by {context.user_id}")


async def handle_request_section_limit(
        context: CustomContext,
        section: RequestSection,
        limit: int
):
    config = get_section_config(context=context, section=section)

    config.limit = limit if limit != 0 else None

    if config.limit is not None:
        active_count = len(context.get_active_category_requests(section=section))
        if active_count >= config.limit:
            config.toggle = False

    await save_yaml_configuration(context=context)

    log.info(f"Request Section {section.category.value} ({section.platform.value}) Limit settled to "
             f"{config.limit if config.limit else 'unlimited'} by {context.user_id}")
