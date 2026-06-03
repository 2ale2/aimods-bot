def utf16_len(s: str) -> int:
    """
    Lunghezza di `s` in UTF-16 code units.
    Telegram conta gli offset delle entity in queste unità, non in caratteri Python.
    """
    return len(s.encode("utf-16-le")) // 2


def utf16_slice(s: str, start: int, end: int | None = None) -> str:
    """
    Affetta `s` per indici UTF-16, non per indici di carattere Python.
    Necessario per estrarre porzioni di testo coerenti con gli offset delle entity Telegram.
    """
    b = s.encode("utf-16-le")
    end_byte = None if end is None else end * 2
    return b[start * 2 : end_byte].decode("utf-16-le")
