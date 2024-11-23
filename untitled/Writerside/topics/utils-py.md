# 🔧 utils.py

> Contiene funzioni che possono tornare utili a tutti gli altri moduli. È come se fosse
> una cassetta degli attrezzi.

## Funzione `get_file`

> Questa funzione è stata pensata per ritornare un'immagine mandata da un utente. 
> **È probabile che in futuro venga integrata per gestire ogni tipo di file**.

<note>
    <format style="bold">Parametri</format>
    <list>
    <li><code>file: Any</code> – Elemento contenente il file da estrarre.</li>
    </list>
</note>

Allo stato attuale, la funzione, che è ricorsiva, ritorna l'immagine a qualità più alta dal 
parametro; per fare questo, viene fatta una verifica per controllare se la variabile `file` sia 
iterabile: se lo è, allora la funzione rilancia se stessa sull'ultimo elemento dell'iterabile,
altrimenti chiama il metodo per ritornare il file.

Questo approccio ricorsivo consente di assumere file anche se contenuti in liste di liste o lista di 
set e così via.

## Funzione `get_attachment_type`

> Ritorna il tipo di allegato, che viene passato come parametro.

<note>
    <format style="bold">Parametri</format>
    <list>
    <li><code>attachment: Any</code> – Allegato da esaminare.</li>
    </list>
</note>

La funzione implementa semplicemente uno switch case sui vari tipi di allegato. Se 
c'è un riscontro, ritorna il corrispondente valore della _custom class_ `AttachmentType`,
che contiene una serie di interi, ognuno dei quali identifica un tipo di allegato.