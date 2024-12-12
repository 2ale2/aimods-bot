# 📀 database_functions.py

> Contiene tutte le funzioni per interagire col database Postgres.

## Funzione `add_to_table`
> Aggiunge un record alla tabella indicata.

<note>
    <format style="bold">Parametri</format>
    <list>
    <li><code>table_name: str</code> – La tabella in cui aggiungere il record.</li>
    <li><code>content: Any</code> – Il contenuto da aggiungere.</li>
    </list>
</note>

La funzione effettua una connessione al database tramite la funzione `connect_to_database()` (vedi sotto), dopodiché 
esegue la query SQL per aggiungere il contenuto nella tabella indicata.

<warning>

La funzione attualmente funziona per la sola aggiunta di nuovi record alla tabella `deleted_messages`,
sebbene sia già presente il parametro per la scelta della tabella. Inoltre, a seconda della tabella, è possibile che
il contenuto vada **gestito in maniera diversa** e che la query **abbia un'altra struttura**, coerente con la tabella 
in cui il contenuto dovrà essere aggiunto.

</warning>

Indipendentemente da un'eventuale insorgenza di un'eccezione in fase di esecuzione della query, la connessione al 
database viene terminata.

## Funzione `generate_values`

> Formatta le informazioni che saranno poi aggiunte al database in modo che query sia formulata correttamente.

<note>
    <format style="bold">Parametri</format>
    <list>
    <li><code>table_name: str</code> – La tabella in cui aggiungere il record.</li>
    <li><code>content_to_elaborate: Any</code> – Il contenuto da elaborare.</li>
    </list>
</note>

A seconda della tabella in cui il contenuto dovrà essere aggiunto, la funzione richiede che il parametro
`content_to_elaborate` abbia determinate caratteristiche che le permettano di lavorare sulle informazioni nel modo
corretto.

Allo stato attuale, il solo valore per il parametro `table_name` previsto è _deleted_messages_. `content_to_elaborate`
deve, in questo caso, essere un'istanza di `telegram.Message`; in caso affermativo, la funzione ricava le informazioni
dal parametro che dovranno essere aggiunte al database.

<note>
<format style="bold">Nota</format>

Affinché il messaggio rimosso venga aggiunto al database, è necessario che esso venga eliminato tramite comando.
Il comando prevede che il messaggio da rimuovere sia selezionato rispondendo a esso. Questo significa che **le informazioni
sul messaggio da eliminare sono contenute all'interno del messaggio cui il messaggio che ha generato l'`Update` sta 
rispondendo**.

Considerato questo, potrebbe anche valer la pena passare alla funzione non il messaggio contenente **il messaggio da
eliminare**, ma **direttamente** quest'ultimo.
</note>


Qualora sia presente un allegato, la funzione lo gestisce (in questo momento gestisce solamente le foto) e lo salva in
locale per poi aggiungere il percorso del file all'elenco di informazioni da aggiungere al record del database.

<warning>

**La funzione salva in locale i media**. Questo potrebbe alla lunga essere problematico, specialmente per file di grandi 
dimensioni. Potrebbe invece avere più senso creare un canale separato dove condividere i media rimossi e salvare nel 
database l'ID del messaggio contenuto all'interno del canale deposito. Alternativamente, si potrebbe salvare l'allegato 
in un formato a qualità inferiore.

</warning>

## Funzione `connect_to_database`

> Effettua la connessione al database e la ritorna al chiamante.

La funzione usa una variabile d'ambiente per reperire il link al database cui effettuare la connessione.

