# ⚙️ handlers_functions.py

> Contiene le funzioni che vengono invocate dagli handlers.

Tutte le funzioni prevedono il passaggio dei due parametri `update` (`Update`), ovvero l'aggiornamento che ha scatenato 
la funzione e `context` (`ContextTypes.DEFAULT_TYPE`), che contiene il contesto attuale, ovvero tutte le informazioni 
memorizzate dal bot in precedenza.

## Funzione `start_command`

> Risponde al comando `/start` inviato in chat privata.

