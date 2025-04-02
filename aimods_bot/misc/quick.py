import re
from datetime import timedelta

def parse_command(command):
    pattern = r"/(\w+)\s*(?:(@\w+|(\d{7,})|<a\s+href=\"tg://user\?id=(\d{7,})\">.*?</a>))?\s*((?:\d+\s*(?:giorni|ore|minuti|secondi)\s*)*)\s*(.*)?"
    match = re.match(pattern, command)

    if not match:
        return None

    action = match.group(1)  # Comando (ban, mute, warn, ecc.)
    username = match.group(2)  # Può essere @username o None
    user_id = match.group(3) or match.group(4)  # ID numerico (da input diretto o da menzione HTML)
    user = user_id if user_id else username  # Se c'è un ID, usiamo quello, altrimenti username
    duration_text = match.group(5) or ""  # Durata
    message = match.group(6) or ""  # Messaggio

    # Mappa delle unità di tempo
    duration_mapping = {"giorni": "days", "ore": "hours", "minuti": "minutes", "secondi": "seconds"}
    duration_kwargs = {key: 0 for key in duration_mapping.values()}

    for num, unit in re.findall(r"(\d+)\s*(giorni|ore|minuti|secondi)", duration_text):
        duration_kwargs[duration_mapping[unit]] = int(num)

    duration = timedelta(**duration_kwargs) if any(duration_kwargs.values()) else None

    return {
        "action": action,  # Tipo di comando (ban, mute, warn, ecc.)
        "user": user,  # Username o ID numerico
        "duration": duration,
        "message": message.strip() if message else None
    }

# **Esempi di utilizzo**
commands = [
    "/ban",
    "/ban @user123 cazzi",
    "/ban 3 giorni 5 ore",
    "/ban 987654321",
    '/ban <a href="tg://user?id=123456789">Nome</a> 3 giorni 4 ore',
    "/ban @user123 2 giorni Flood",
    "/mute 123456789 30 minuti Violazione regole",
    "/warn <a href=\"tg://user?id=987654321\">Mario Rossi</a> Attenzione: comportamento scorretto",
    "/kick 456789123",
    "/ban 123456789 5 minuti Test"
]

for cmd in commands:
    parsed = parse_command(cmd)
    print(f"\nComando: {cmd}")
    print(f"  ➤ Azione: {parsed['action']}")
    print(f"  ➤ Utente/ID: {parsed['user']}")
    print(f"  ➤ Durata: {parsed['duration']}")
    print(f"  ➤ Messaggio: {parsed['message']}")
