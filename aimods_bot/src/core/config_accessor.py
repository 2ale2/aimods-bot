from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import Configuration, CategorySetting
from aimods_bot.src.helpers.constants.constants import Platform, Category
from aimods_bot.src.helpers.models.request_section import RequestSection


def get_config(context: CustomContext) -> Configuration:
    return context.pydb.configuration


def get_value(context, path: str, default=None):
    """Ritorna una sezione della configurazione del bot o un valore specifico."""
    try:
        config = get_config(context)
        for key in path.split("."):
            config = getattr(config, key)
        return config
    except AttributeError:
        return default


def set_value(context, path: str, value):
    config = get_config(context)
    keys = path.replace("/", ".").split(".")
    obj = config
    for key in keys[:-1]:
        obj = getattr(obj, key)
    setattr(obj, keys[-1], value)


def get_section_config(context: CustomContext, section: RequestSection) -> CategorySetting:
    """Helper per recuperare la configurazione in modo sicuro e tipizzato."""
    return getattr(
        getattr(context.pydb.configuration.settings.request, section.platform.value),
        section.category.value
    )
