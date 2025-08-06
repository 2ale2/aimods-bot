import copy

from telegram.ext import ContextTypes

from aimods_bot.src.core.exceptions import handle_validation_errors
from aimods_bot.src.core.validation import validate_structure
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json


def get_config(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.bot_data["configuration"]  # Se per disgrazia manca deve scatenare un'eccezione.


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

    raw_template = get_data_from_json("configuration_structure")

    errors = validate_structure(config, raw_template)
    handle_validation_errors(errors)
