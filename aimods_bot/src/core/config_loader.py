import yaml
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("config_loader")


def load_configuration():
    """
    Carica e verifica la configurazione del file YAML.

    Ritorna:
        dict: La configurazione del file YAML validata.

    Scatena:
        Exception: se c'è un errore in fare di caricamento del JSON.
    """

    try:
        with open("aimods_bot/misc/BotConfigurationStructure.yml", "r") as stream:
            yaml_data = yaml.load(stream, Loader=yaml.FullLoader)
    except Exception as e:
        log.error(f"Failed to load configuration: {e}")
        raise

    return yaml_data
