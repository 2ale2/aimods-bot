import yaml
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json
from aimods_bot.src.core.exceptions import handle_validation_errors
from aimods_bot.src.core.validation import validate_structure

log = logger.getChild("config_loader")


def load_configuration():
    """
    Carica e verifica la configurazione del file YAML.

    Ritorna:
        dict: La configurazione del file YAML validata.

    Scatena:
        Exception: se c'è un errore in fare di caricamento del JSON.
    """
    raw_template = get_data_from_json("configuration_structure")

    try:
        with open("aimods_bot/misc/BotConfigurationStructure.yml", "r") as stream:
            yaml_data = yaml.load(stream, Loader=yaml.FullLoader)
    except Exception as e:
        log.error(f"Failed to load configuration: {e}")
        raise

    errors = validate_structure(yaml_data, raw_template)
    handle_validation_errors(errors)

    return yaml_data
