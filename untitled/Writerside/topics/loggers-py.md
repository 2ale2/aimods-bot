# 🗒 loggers.py

> Crea e imposta i vari logger che vengono usati nei vari moduli

Tutti i logger integrano un formato di output del tipo:

<code-block>
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
</code-block>

dove:
- `asctime` è l'orario di generazione del log
- `name` è il nome del logger
- `levelname` è il livello del log generato
- `message` è il messaggio generato dal logger

e possiedono un **file associato** in cui tutti i relativi log vengono salvati.
## Loggers

1. `db_logger` – Il logger del database.
   - Livello: `INFO`
   - File: `aimods_bot/misc/logs/database.log`
2. `command_logger` – Il logger dei comandi del bot.
   - Livello: `INFO`
   - File: `aimods_bot/misc/logs/commands.log`
3. `job_queue_logger` – Il logger della queue.
   - Livello: `WARNING`
   - File: `aimods_bot/misc/logs/jobqueue.log`