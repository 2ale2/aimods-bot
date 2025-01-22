# ⚙️ handlers_functions.py

> Contiene le funzioni che vengono invocate dagli handlers.

Tutte le funzioni prevedono il passaggio dei due parametri `update` (`Update`), ovvero l'aggiornamento che ha scatenato 
la funzione e `context` (`ContextTypes.DEFAULT_TYPE`), che contiene il contesto attuale, ovvero tutte le informazioni 
memorizzate dal bot in precedenza.

## Funzione `start_command`

> Risponde al comando `/start` inviato in chat privata.

L'idea sarebbe quella di rispondere dipendentemente dal ruolo che l'utente possiede: se è admin, viene mostrato il 
pannello di controllo, altrimenti viene mostrato un messaggio di benvenuto.

## Funzione `new_member_joined_forum`

> Gestisce gli step della conversazione per l'aggiunta di un nuovo membro al gruppo.

Siccome la funzione risponde anche al comando `/request`, la funzione controlla ed elimina il rispettivo comando (per 
mere questioni di ordine).

La funzione controlla, dapprima, se l'utente che ha fatto richiesta è stato bannato, nel qual caso il bot risponde
avvertendo l'utente del ban e chiude la conversazione.

Qualora la conversazione non è terminata nei casi precedenti, la funzione controlla se l'utente che ha fatto 
richiesta si trova già nel gruppo oppure no: se lo è, manda un messaggio che rimanda al gruppo e suggerisce il comando 
`/rules` per stampare le regole. In questo caso, la conversazione viene terminata.

A questo punto, si vuole capire se l'utente ha cominciato la conversazione tramite comando `/request` oppure facendo 
una richiesta sul gruppo della community. In quest'ultimo caso, la funzione crea una variabile all'interno dello 
`user_data` associato all'utente, che tiene conto del fatto che l'utente ha fatto richiesta di entrare.
Dopo tale controllo, se tale variabile non è presente, significa che la conversazione è stata avviata tramite comando
`/requests`.

