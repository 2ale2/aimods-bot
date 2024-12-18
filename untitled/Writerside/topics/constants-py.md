# #️⃣ constants.py

> Questo modulo definisce oggetti personalizzati usati dal bot per la gestione delle eccezioni, limitazione e contesti.

Il modulo assume dapprima i dati dei topic contenuti nel file `data.json`.

<note>
    <format style="bold">File di configurazione <code>data.json</code></format>
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

#### Metodo `remove_topics_to_scope`

> Rimuove uno o più topic allo Scope.

<note>
    <format style="bold">Parametri</format>
    <list>
        <li><code>topics_to_remove: Union[Set[int], int]</code> – Intero <format style="bold">o</format> set di interi 
        corrispondenti all'identificativo dei topic da rimuovere allo Scope.</li>
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

#### Metodo 
