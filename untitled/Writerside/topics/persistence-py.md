# 💾 persistence.py

> Questo modulo definisce la classe persistenza `PostgresPersistence`,
> che si occupa di gestire i dati permanenti del bot all'interno del
> database _Postgres_ (tabella `persistence`).

L'istanza della classe persistenza viene creata dal modulo `init.py`, 
che si occupa di creare l'istanza di `Application`:

<code-block>
application = ApplicationBuilder().token(core.get_env("BOT_TOKEN")).persistence(PostgresPersistence(url=core.get_env("POSTGRES_CONNECTION_URL"))).post_init(core.set_application_data).build()
</code-block>

## Metodo `init`

> Crea l'istanza della classe `PostgresPersistence`.

<note>
    <format style="bold">Parametri</format>
    <list>
    <li><code>url: str</code> – Link al database Postgres (deve cominciare con <code>postgresql://</code>).</li>
    </list>
</note>

Ci sono anche altri parametri in realtà, ma non li uso.

La funzione impone di indicare almeno un parametro tra `url` e un altro, che rappresenta un altro tipo di connessione.
`url` viene usato per effettuare una **preliminare connessione** al database indicato, il cui cursore viene salvato 
all'interno di un attributo della classe `self._session`.

Quest'ultimo parametro viene poi riutilizzato immediatamente dopo, quando il metodo `init` chiama 
`self.__init_database()` (vedi sotto) usato per **inizializzare** e "preparare" il **database**.

Dopo l'inizializzazione, il metodo `init` procede al caricamento delle informazioni eventualmente contenute nel 
database; in particolare:
1. Vengono prelevate le informazioni tramite una query (`SELECT data FROM persistence`), che assume il contenuto 
dell'unica colonna presente `data` nella tabella `persistence`.
    > Le informazioni sono salvate all'interno della tabella in formato JSON, convertito in stringa.
2. Le informazioni sono caricate all'interno di un dizionario Python (da stringa a dizionario).
3. I vari elementi della persistenza (`chata_data`, `user_data`, `bot_data`, `conversations` e `callback_data`).
    > Se gli elementi non sono presenti nel dizionario, viene ritornato un dizionario vuoto `{}`.

Se il caricamento viene correttamente portato a termine, viene creato un messaggio di log.

Qualora la tabella fosse vuota, il processo di caricamento delle informazioni viene sostituito da una procedura di 
creazione di un elemento (dizionario JSON in formato stringa) vuoto ma correttamente gestibile dalla classe stessa:

<code-block>
insert_qry = "INSERT INTO persistence (data) VALUES (%s)"
self._session.execute(str(insert_qry), 
                         [
                             json.dumps({"jsondata": "{}"})
                         ]
                     )
</code-block>

Con le informazioni così ottenute vengono usare per inizializzare l'istanza di `DictPersistence`, la classe da cui 
deriva `PostgresPersistence`.

## Metodo `__init_database`
> Crea la tabella per salvare le informazioni se non esiste già nel database.

La creazione avviene tramite query: `CREATE TABLE IF NOT EXISTS persistence(data json NOT NULL);` eseguita, ovviamente, 
all'interno del database cui si è già effettuata una connessione preliminare.

## Metodo `_dump_into_json`
> Effettua la conversione da dizionario a stringa in formato JSON, per l'inserimento delle informazioni nel database.

Il metodo crea un dizionario `to_dump` che contiene le informazioni da convertire; viene poi creato un messaggio di log 
che comunica del tentativo di _dumping_. Infine, viene eseguita la conversione tramite `json.dumps(to_dump)`.

## Metodo `_update_database`
> Aggiorna il contenuto della tabella `persistence`.

Viene dapprima creato un messaggio di log che comunica dell'avvio della procedura di aggiornamento. Poi, viene fatto un
tentativo di aggiornamento che prevede la creazione di due variabili (`insert_qry` e `params`) che contengono la query
di aggiornamento e le informazioni aggiornate, rispettivamente.

La variabile `params`, in particolare, viene creata chiamando il metodo `_dump_into_json` (vedi sopra).

Dopo aver combinato le due variabili, viene eseguita la query di aggiornamento. In caso di _Eccezioni_, viene creato 
un messaggio di log con i dettagli dell'errore.

## Metodo `update_conversation`
> Aggiorna una conversazione per un determinato utente.

<note>
    <format style="bold">Parametri</format>
    <list>
    <li><code>name: str</code> – Nome del ConversationHandler.</li>
    <li><code>key: Tuple[int, ...]</code> – Per quali utenti lo stato della conversazione deve essere aggiornato.</li>
    <li><code>new_state: Optional[object]</code> – Il nuovo stato della conversazione. Se <code>None</code>, la 
    conversazione è rimossa dalla memoria.</li>
    </list>
</note>

Il metodo chiama quello omonimo della classe padre `DictPersistence`, passando i parametri ottenuti.

## Metodo `update_user_data`
> Aggiorna la persistenza associata a un utente (`user_data`).

<note>
    <format style="bold">Parametri</format>
    <list>
        <li><code>user_id: int</code> – ID dell'utente da aggiornare.</li>
        <li><code>data: Dict</code> – Le informazioni aggiornate.</li>
    </list>
</note>

Il metodo chiama quello omonimo della classe padre `DictPersistence`, passando i parametri ottenuti.

## Metodo `update_chat_data`
> Aggiorna la persistenza associata a una chat (`chat_data`).

<note>
    <format style="bold">Parametri</format>
    <list>
        <li><code>chat_id: int</code> – ID della chat da aggiornare.</li>
        <li><code>data: Dict</code> – Le informazioni aggiornate.</li>
    </list>
</note>

Il metodo chiama quello omonimo della classe padre `DictPersistence`, passando i parametri ottenuti.

## Metodo `update_bot_data`
> Aggiorna la persistenza associata al bot (`bot_data`).

<note>
    <format style="bold">Parametri</format>
    <list>
        <li><code>data: Dict</code> – Le informazioni aggiornate.</li>
    </list>
</note>

Il metodo chiama quello omonimo della classe padre `DictPersistence`, passando i parametri ottenuti.

## Metodo `update_callback_data`
> Aggiorna la callback_data (se è cambiata).

<note>
    <format style="bold">Parametri</format>
    <list>
        <li><code>data: CDCData</code> – Le informazioni aggiornate.</li>
    </list>
</note>

<code-block>CDCData = Tuple[List[Tuple[str, float, Dict[str, Any]]], Dict[str, str]]</code-block>

Il metodo chiama quello omonimo della classe padre `DictPersistence`, passando i parametri ottenuti.