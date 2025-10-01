import copy

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.core.pydantic import Configuration


def get_config(context: CustomContext) -> Configuration:
    return context.pydb.configuration


def get_value(context, path: str, default=None):
    """Ritorna una sezione della configurazione del bot o un valore specifico."""

    try:
        config = get_config(context)
        keys = path.split(".")
        for key in keys:
            config = config[key]
        return config
    except KeyError:
        return default


def set_value(context, path: str, value):
    config = get_config(context)
    config_copy = copy.copy(config)
    keys = path.replace("/", ".").split(".")
    for key in keys[:-1]:
        config_copy = config_copy[key]
    config_copy[keys[-1]] = value
