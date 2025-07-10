import json
from typing import Any
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("file_utils")


async def get_file(file):
    try:
        iter(file)
    except TypeError:
        return file.get_file()
    else:
        return await get_file(file[-1])


def get_data_from_json(key: str, file_path: str = "aimods_bot/misc/data.json") -> Any:
    """
    Estrae un campo dal file JSON specificato.

    Args:
        key: chiave da cercare nel JSON.
        file_path: percorso al file (default: aimods_bot/misc/data.json).

    Returns:
        Il valore associato alla chiave richiesta.

    Raises:
        FileNotFoundError: se il file non esiste.
        KeyError: se la chiave è assente.
        json.JSONDecodeError: se il file non è valido JSON.
    """
    try:
        with open(file_path, encoding="utf-8") as fp:
            content = json.load(fp)
    except FileNotFoundError:
        log.error(f"File JSON non trovato: {file_path}")
        raise
    except json.JSONDecodeError as e:
        log.error(f"Errore nel parsing JSON ({file_path}): {e}")
        raise

    if key not in content:
        log.error(f"Chiave '{key}' mancante in {file_path}")
        raise KeyError(f"Chiave '{key}' mancante in '{file_path}'")

    return content[key]
