# ⏳ job_queue_functions.py

> Questo modulo contiene le funzioni per eseguire le azioni programmate.

## Funzione `scheduled_delete_message`

> Esegue la rimozione programmata di un messaggio.

<note>
    <format style="bold">Parametri</format>
    <list>
    <li><code>context: ContextTypes.DEFAULT_TYPE</code> – Il contesto (contiene i dati necessari alla Job Queue).</li>
    </list>
</note>

La funzione apprende le informazioni necessarie associate al messaggio da eliminare (ID del messaggio e 
ID della chat in cui si trova). Se qualcosa manca, viene creato un warning. La funzione tenta quindi di rimuovere il 
messaggio indicato. Qualora ci siano errori, crea un warn che contiene le informazioni sull'errore.

## Funzione `scheduled_send_message`

> Esegue l'invio programmato di un messaggio.

<note>
    <format style="bold">Parametri</format>
    <list>
    <li><code>context: ContextTypes.DEFAULT_TYPE</code> – Il contesto (contiene i dati necessari alla Job Queue).</li>
    </list>
</note>

La funzione apprende le informazioni necessarie associate al messaggio da inviare (l'ID della chat, il testo e
la tastiera). Se qualcosa manca, viene creato un warning. La funzione tenta quindi di inviare il messaggio. 
Qualora ci siano errori, crea un warn che contiene le informazioni sull'errore.

## Funzione `scheduled_edit_message`

> Esegue la modifica programmata di un messaggio.

<note>
    <format style="bold">Parametri</format>
    <list>
    <li><code>context: ContextTypes.DEFAULT_TYPE</code> – Il contesto (contiene i dati necessari alla Job Queue).</li>
    </list>
</note>

La funzione apprende le informazioni necessarie associate al messaggio da inviare (l'ID della chat, l'ID del messaggio 
e il testo). Se qualcosa manca, viene creato un warning. La funzione tenta quindi di modificare il messaggio indicato. 
Qualora ci siano errori, crea un warn che contiene le informazioni sull'errore.