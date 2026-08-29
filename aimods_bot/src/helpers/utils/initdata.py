"""Validazione dell'initData di una Mini App Telegram."""

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qsl

# Campo che NON entra nel data_check_string: solo 'hash', che è la firma stessa.
# NOTA: 'signature' (validazione di terze parti, Bot API 8.0) va INCLUSO —
# verificato empiricamente contro un initData reale l'11/08/2026. Escluderlo
# fa fallire sempre il confronto.
_EXCLUDED = ("hash",)

MAX_AGE_SECONDS = 300


class InitDataError(Exception):
    pass


def parse_init_data(raw: str, bot_token: str, max_age: int = MAX_AGE_SECONDS) -> dict[str, Any]:
    """
    Valida l'initData e restituisce i campi decodificati.
    Solleva InitDataError se la firma non torna o se il dato è troppo vecchio.
    """
    if not raw:
        raise InitDataError("initData vuoto")

    # parse_qsl decodifica già il percent-encoding: i valori qui sono in chiaro,
    # ed è esattamente in chiaro che devono entrare nel data_check_string.
    pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=False)
    fields = dict(pairs)

    received_hash = fields.get("hash")
    if not received_hash:
        raise InitDataError("campo 'hash' assente")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(pairs) if k not in _EXCLUDED
    )

    # Attenzione all'ordine: la chiave è HMAC('WebAppData', bot_token),
    # non HMAC(bot_token, 'WebAppData'). Invertirli produce un hash che non
    # combacia mai, senza errori espliciti.
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("firma non valida")

    auth_date = fields.get("auth_date")
    if not auth_date or not auth_date.isdigit():
        raise InitDataError("auth_date assente o malformato")
    age = time.time() - int(auth_date)
    if age > max_age:
        raise InitDataError(f"initData scaduto ({int(age)}s > {max_age}s)")
    if age < -60:
        raise InitDataError("auth_date nel futuro")

    # I campi composti arrivano come JSON.
    for key in ("user", "chat", "receiver"):
        if key in fields:
            try:
                fields[key] = json.loads(fields[key])
            except json.JSONDecodeError as e:
                raise InitDataError(f"campo '{key}' non è JSON valido") from e

    return fields


if __name__ == "__main__":
    import os
    import sys

    token = os.getenv("BOT_TOKEN")
    if not token:
        sys.exit("BOT_TOKEN non impostato")
    if len(sys.argv) < 2:
        sys.exit("uso: python3 initdata.py '<initData>'")

    try:
        # max_age enorme: un initData salvato è per definizione scaduto,
        # e qui interessa solo sapere se la FIRMA torna.
        data = parse_init_data(sys.argv[1], token, max_age=10**9)
    except InitDataError as e:
        print(f"NON VALIDO: {e}")
        raise SystemExit(1)

    print("FIRMA OK")
    print(f"  query_id  : {data.get('chat_join_request_query_id')}")
    print(f"  user id   : {data.get('user', {}).get('id')}")
    print(f"  chat id   : {data.get('chat', {}).get('id')}")
    print(f"  chat_type : {data.get('chat_type')}")
    print(f"  auth_date : {data.get('auth_date')}")
