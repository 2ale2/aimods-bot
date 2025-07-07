import json
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("utils")


def get_data_from_json(data: str):
    """
    :param data: Chiave da estrarre
    :return: il contenuto del file di configurazione json richiesto
    """
    try:
        with open("aimods_bot/misc/data.json", encoding="utf-8", mode="r") as fp:
            content = json.load(fp)
    except FileNotFoundError:
        log.error("❌ File data.json non trovato.")
        raise
    except json.JSONDecodeError as e:
        log.error(f"❌ Errore parsing JSON: {e}")
        raise

    try:
        return content[data]
    except KeyError as e:
        log.error(f"❌ Chiave '{data}' mancante in data.json")
        raise
