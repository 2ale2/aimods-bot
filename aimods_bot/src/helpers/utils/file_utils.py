import copy
import json
import mimetypes
import os
from typing import Any, List, Literal, Union, Tuple, Optional

from telegram import InputMedia, InputMediaDocument

from aimods_bot.src.helpers.constants.media import MEDIA_GROUP_TYPES
from aimods_bot.src.helpers.constants.models import MediaItem
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("file_utils")


async def get_file(file):
    try:
        iter(file)
    except TypeError:
        return file.get_file()
    else:
        return await get_file(file[-1])


def get_data_from_json(key: str = None, file_path: str = "aimods_bot/misc/data.json") -> Any:
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

    if not key:
        return content

    if key not in content:
        log.error(f"Chiave '{key}' mancante in {file_path}")
        raise KeyError(f"Chiave '{key}' mancante in '{file_path}'")

    return content[key]


def set_data_in_json(key: Union[str, List[str]], value: Any, file_path: str = "aimods_bot/misc/data.json") -> bool:
    c = get_data_from_json(None)

    if isinstance(key, str):
        if key not in c:
            log.warning(f"Chiave '{key}' mancante in {file_path}. Verrà aggiunta.")

        c[key] = value
    else:  # isinstance(key, list)
        c_copy = copy.copy(c)
        for el in key[:-1]:
            if el not in c_copy:
                log.error(f"Chiave '{key}' mancante in {file_path}.")
                return False
            c_copy = c_copy[el]
        l_key = key[-1]
        if l_key not in c_copy:
            log.error(f"Chiave '{l_key}' mancante in {file_path}. Verrà aggiunta.")
        c_copy[l_key] = value
    try:
        with open(file_path, "w") as fp:
            json.dump(c, fp, indent=4)
        log.info("File JSON modificato correttamente.")
        return True
    except Exception as e:
        log.error(f"Errore nel parsing JSON ({file_path}): {e}")
        return False


# noinspection PyTypeChecker
def get_file_type(file: Union[str, InputMedia]) -> Literal["document", "photo", "audio", "video", "gif"]:
    if isinstance(file, InputMedia):
        t = file.type.lower() if file.type.lower() in ("photo", "audio", "video", "gif") else "document"
        return t

    mime, _ = mimetypes.guess_type(file)

    if mime is None:
        return "document"

    if mime.startswith("image/"):
        if mime == "image/gif":
            return "gif"
        else:
            return "photo"
    elif mime.startswith("video/"):
        return "video"
    elif mime.startswith("audio/"):
        return "audio"
    else:
        return "document"


async def normalize_files(
        items: List[MediaItem]
) -> List[Tuple[Literal["document", "photo", "audio", "video", "gif"], InputMedia]]:
    output = []

    for el in items:
        if isinstance(el.item, InputMedia):
            if el.as_doc:
                output.append(("document", InputMediaDocument(el.item.media)))
            else:
                output.append((el.type, el.item))
        else:  # el.item è una stringa
            if not os.path.exists(el.item):
                log.error(f"Directory o file non trovato: {el.item}")
                continue
            with open(el.item, "rb") as fp:
                if el.as_doc:
                    output.append((el.type, InputMediaDocument(fp)))
                else:
                    output.append((el.type, MEDIA_GROUP_TYPES[el.type](fp)))

    return output


async def make_temp_file(content: Any, filename: str) -> Optional[str]:
    if isinstance(content, list):
        try:
            with open(filename := f"./{filename}.txt", "w") as f:
                for s in content:
                    f.write(str(s) + "\n")
            return filename
        except (FileNotFoundError, PermissionError, OSError) as e:
            log.error(f"Errore durante la scrittura del file {filename}: {e}")
            return None

    # altri tipi
