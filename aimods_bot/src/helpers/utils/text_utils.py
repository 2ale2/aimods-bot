def u16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def u16_slice(s: str, start: int, end: int | None = None) -> str:
    b = s.encode("utf-16-le")
    return b[start * 2 : (None if end is None else end * 2)].decode("utf-16-le")
