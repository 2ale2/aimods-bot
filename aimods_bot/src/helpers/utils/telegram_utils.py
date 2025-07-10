from typing import Optional, Any

import telegram
from telegram import Update
from telegram.ext import ContextTypes

from aimods_bot.src.core.exceptions import CallbackDataException
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("telegram_utils")


def get_valid_thread_id(update: Update) -> Optional[int]:
    thread_id = update.effective_message.message_thread_id
    if thread_id is not None and thread_id < 20:
        return thread_id
    return None


async def safe_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, message: telegram.Message = None):
    """
    Tenta di eliminare un messaggio Telegram in modo sicuro.
    Se viene fornito 'message', tenta di eliminare quello.
    Altrimenti, tenta di eliminare update.effective_message.
    Ignora errori di tipo BadRequest (es. messaggio già eliminato o non trovato).
    """
    message_to_delete = message if message is not None else update.effective_message

    if message_to_delete is None:
        log.warning("Nessun messaggio valido da eliminare è stato fornito o trovato.")
        return

    try:
        await message_to_delete.delete()
    except telegram.error.BadRequest as e:
        log.warning(f"Impossibile eliminare il messaggio (ID: {message_to_delete.message_id if hasattr(message_to_delete, 'message_id') else 'N/A'}): {e}")
    except AttributeError:
        log.error(f"L'oggetto fornito non è un telegram.Message valido e non ha il metodo delete.")
    except Exception as e:
        log.error(f"Errore inatteso durante l'eliminazione del messaggio: {e}", exc_info=True)


def validate_callback_structure(
    callback_data: str,
    expected_fields: list[dict],
    separator: str = "_",
    should_be: str = None
) -> list[Any]:
    """
        Valida la struttura del callback_data e ne converte i valori secondo specifiche.

        Args:
            callback_data: la stringa di callback ricevuta.
            expected_fields: lista di dict, ognuno con:
                - "type": type o "literal"
                - "value": se type == "literal"
                Tutti gli elementi sono obbligatori: la loro assenza produce eccezioni.
            separator: separatore tra i campi.
            should_be: stringa per messaggio d’errore.

        Returns:
            Lista di valori convertiti (o None se opzionali mancanti).

        Raises:
            CallbackDataException
        """

    parts = callback_data.split(separator)

    if len(parts) != len(expected_fields):
        raise CallbackDataException(callback_data, should_be=should_be)

    result = []

    for i, spec in enumerate(expected_fields):
        raw_value = parts[i]
        field_type = spec["type"]  # Se non c'è, genero eccezione

        # Caso 1: valore letterale (fisso)
        if field_type == "literal":
            expected_value = spec.get("value")
            if raw_value != expected_value:
                raise CallbackDataException(callback_data, should_be)
            result.append(raw_value)

        # Caso 2: tipo singolo (int, str)
        elif isinstance(field_type, type):
            try:
                result.append(field_type(raw_value))
            except Exception:
                raise CallbackDataException(callback_data, should_be)

        # Caso 3: lista di tipi alternativi [int, str]
        elif isinstance(field_type, list):
            converted = None
            # Ordine sequenziale
            # Se il tipo è preferibile che sia int (str), int (str) dovrebbe essere il primo della lista
            for t in field_type:
                try:
                    converted = t(raw_value)
                    break
                except Exception:
                    continue
            if converted is None:
                raise CallbackDataException(callback_data, should_be)
            result.append(converted)

        else:
            raise ValueError(f"Tipo di campo non gestito: {field_type}")

    return result
