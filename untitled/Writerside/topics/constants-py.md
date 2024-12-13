# constants.py

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