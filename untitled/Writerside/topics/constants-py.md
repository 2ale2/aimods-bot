# #️⃣ constants.py

> Questo modulo definisce oggetti personalizzati usati dal bot per la gestione delle eccezioni, limitazione e contesti.

Il modulo assume dapprima i dati dei topic contenuti nel file `data.json`.

<note>
    <format style="bold">File di configurazione <code>data.json</code></format><br></br>
    Questo file contiene dei testi predefiniti (come quello delle regole e di benvenuto) e informazioni sui vari topic
    presenti nel gruppo pubblico, suddivisi per categorie (che nel nostro contesto vengono chiamati) 
    "<i><code>Scopes</code> di default</i>":
    <list>
    <li><format style="bold">all</format> – La categoria che contiene tutti i topic.</li>
    <li><format style="bold">richieste</format> – La categoria che contiene tutti i topic relativi alle richieste.</li>
    <li><format style="bold">assistenza</format> – La categoria che contiene tutti i topic relativi all'assistenza.</li>
    <li><format style="bold">off-topic</format> – La categoria che contiene il topic off-topic.</li>
    </list>
    <warning>
        Categorie che contengono un solo topic potrebbero non servire, siccome il progetto prevede l'implementazione dei
        comandi con parametri che specificano lo <i>Scope</i> oppure un topic singolo.
    </warning>
    Ogni topic nelle categorie è costituito da un <code>id</code> e un <code>name</code>. 
</note>

## Classe `Scope`

> Rappresenta una categoria, ovvero un insieme di uno o più topic.

<note>
    <format style="bold">Parametri</format>
    <list>
        <li><code>name: str</code> – Il nome dello Scope.</li>
        <li><code>topics: Set[int]</code> – Set degli identificativi dei topic che fanno parte di questo Scope.</li>
    </list>
</note>

### Metodi di `Scope`

#### Metodo `add_topics_to_scope`

> Aggiunge uno o più topic allo Scope.

<note>
    <format style="bold">Parametri</format>
    <list>
        <li><code>new_topics: Union[Set[int], int]</code> – Intero <format style="bold">o</format> set di interi 
        corrispondenti all'identificativo dei topic da aggiungere allo Scope.</li>
    </list>
</note>

La funzione fa un test sul tipo del parametro: se è un intero, viene trasformato in un Set contenente se stesso;
dopodiché viene fatta l'unione tra il Set di identificativi corrente e quello contenente gli ID da aggiungere.

#### Metodo `remove_topics_from_scope`

> Rimuove uno o più topic dallo Scope.

<note>
    <format style="bold">Parametri</format>
    <list>
        <li><code>topics_to_remove: Union[Set[int], int]</code> – Intero <format style="bold">o</format> set di interi 
        corrispondenti all'identificativo dei topic da rimuovere dallo Scope.</li>
    </list>
</note>

La funzione fa un test sul tipo del parametro: se è un intero, viene trasformato in un Set contenente se stesso;
dopodiché viene fatta la sottrazione tra il Set di identificativi corrente e quello contenente gli ID da rimuovere.

## Classe `Scopes`

> Contiene gli Scope di default, ovvero:
> 
> - **Forum Scope** – Lo scope che contiene tutti i topic.
> - **Requests Scope** – Lo scope che contiene tutti i topic delle richieste.
> - **Assistence Scope** – Lo scope che contiene tutti i topic dell'assistenza.
> - **Off Topic Scope** – Lo scope che contiene l'off topic.
> - _Single Topic Scopes_ – Uno scope per ogni singolo topic.
>   <warning>Serve? Potrebbe invece essere utile usare la classe come contenitore di tutti gli Scope (ovvero una
>   classe che contiene gli Scope di default e quelli personalizzati).</warning>

### Metodi di `Scopes`

#### Metodo `create_single_topic_scope`

> È un metodo di servizio usato dal modulo per creare tutti gli Scope a singolo topic e aggiungerli all'istanza di 
> Scopes.

<note>
    <format style="bold">Parametri</format>
    <list>
        <li>
            <code>name: str</code> – Nome del topic, ovvero nome del nuovo attributo dell'istanza della classe 
            <code>Scopes</code>.
        </li>
        <li>
            <code>topic_name: str</code> – Il nome attuale del topic (appreso dalla variabile <code>TOPICS</code>).
        </li>
    </list>
</note>

In particolare, il metodo viene usato in questo modo: per ogni elemento rappresentante un topic all'interno della
variabile TOPIC, che contiene le informazioni su tutti i topic, viene creato un attributo che possiede, come nome, il
nome del topic (`scope_name`). Il metodo `setattr` consente di creare un nuovo attributo all'interno di una classe.
Tale metodo viene chiamato specificando:

- la variabile cui aggiungere l'attributo (`Scopes`);
- il nome che avrà l'attributo (`scope_name`);
- l'istanza di <code>[Scope](#classe-scope)</code> (creata tramite il metodo `create_single_topic_scope`) che 
rappresenterà il valore dell'attributo.

## Classe `Permissions`

> Questa classe rappresenta le limitazioni utili applicabili ad un utente. La loro utilità risiede nel fatto che 
> vi sia una corrispondenza biunivoca tra intero e nome della limitazione.

È una sottoclasse di `IntEnum` ed è costituita ad una serie di interi corrispondenti ad una limitazione:

- `SEND_MESSAGE`: limitazione sull'invio dei messaggi.
- `SEND_ALL_MEDIA`: limitazione sull'invio di tutti i media.
- `SEND_PHOTO`: limitazione sull'invio di foto.
- `SEND_VIDEO_FILES`: limitazione sull'invio di file video.
- `SEND_VIDEO_MESSAGES`: limitazione sull'invio di video messaggi (quelli istantanei).
- `SEND_MUSIC`: limitazione sull'invio di file audio.
- `SEND_FILES`: limitazione sull'invio di ogni tipo di documento.
- `SEND_STICKERS_GIFS`: limitazione sull'invio di sticker e gift.
- `SEND_EMBEDDED_LINKS`: limitazione sull'invio di link.
- `SEND_POOLS`: limitazione sull'invio di sondaggi.
- `ADD_MEMBERS`: limitazione sull'aggiunta di membri.
- `CREATE_TOPICS`: limitazione sulla creazione di topic.
- `CHANGE_GROUP_INFO`: limitazione sulla modifica delle informazioni del gruppo.



