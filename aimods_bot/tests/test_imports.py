"""
Importa OGNI modulo di `src/`, anche quelli che nessun altro test tocca.

Serve a trasformare "il bot non parte" in "il test fallisce": import rotti
dopo uno spostamento, import circolari, nomi spariti. `pytest` da solo importa
solo i moduli che i test usano, e l'import circolare di `requests_management`
è uscito solo all'avvio proprio per questo.

Le variabili d'ambiente lette all'import (es. `CHANNEL_ID`) ricevono un valore
finto solo se mancano: il test non deve dipendere dal `.env` di chi lo lancia.
"""
import importlib
import locale
import os
import pkgutil
import tempfile
from pathlib import Path

import pytest

# Lette a livello di modulo da qualche file di `src/`. Valori finti, mai usati.
_IMPORT_TIME_ENV = {
    "CHANNEL_ID": "-1001",
    "CHANNEL_LOGGER_ID": "-1002",
    "MYID": "1",
    "LOG_DIR": os.path.join(tempfile.gettempdir(), "aimods_bot_test_logs"),
}
for _key, _value in _IMPORT_TIME_ENV.items():
    os.environ.setdefault(_key, _value)

# Alcuni moduli aprono file con percorsi relativi alla radice del repo
# ("aimods_bot/misc/data.json"): nel container la cartella corrente è /app, cioè
# proprio la radice. Qui la si imposta uguale, da qualunque cartella parta pytest.
os.chdir(Path(__file__).resolve().parents[2])

# L'entrypoint imposta `it_IT.UTF-8` all'import: su una macchina senza quella
# locale fallirebbe per un motivo che non c'entra con gli import.
_real_setlocale = locale.setlocale


def _tolerant_setlocale(category, value=None):
    try:
        return _real_setlocale(category, value)
    except locale.Error:
        return _real_setlocale(category)


locale.setlocale = _tolerant_setlocale

import aimods_bot.src as _src  # noqa: E402

_MODULES = sorted(
    info.name
    for info in pkgutil.walk_packages(_src.__path__, prefix=f"{_src.__name__}.")
)


def test_found_modules():
    # Se questo scende a zero, il test sotto passerebbe senza controllare niente.
    assert len(_MODULES) > 100


@pytest.mark.parametrize("module", _MODULES)
def test_module_imports(module):
    importlib.import_module(module)
