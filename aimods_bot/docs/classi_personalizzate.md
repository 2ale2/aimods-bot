# Custom Classes

Ho creato alcune classi personalizzate. In questo file viene descritta la loro struttura e implementazione all'interno
del bot.

La classi personalizzate sono:
- _Scope_ (assieme alla classe _Scopes_);
- _Limitations_.

## Classi _Scope_ e _Scopes_
Tale classe rappresenta un contesto ("scope", non "context" per non confonderlo con una classe già presente in PTB), 
ovvero un insieme di uno o più topic all'interno del quale un'azione di moderazione
ha effetto. Ogni istanza è costituita da un nome, `name` (stringa) e dall'insieme di topic `topics` (set di interi).
`topics` contiene gli identificativi dei topic di riferimento.

La classe _Scopes_ contiene le istanze _Scope_ create di default all'avvio del bot. In particolare:
- `FORUM_SCOPE`: il contesto che include tutti i topic all'interno del forum – è il contesto di default;
- `REQUESTS_SCOPE`: il contesto che include i topic relativi alle richieste;
- `ASSISTENCE_SCOPE`: il contesto che include i topic relatici all'assistenza;
- `OFF_TOPIC_SCOPE`: il contesto che include i topic off-topic.

Oltre a questi, vengono automaticamente creati tanti contesti (ovvero tante istanze di _Scope_) quanti sono i topic
all'interno del forum. Ciò è realizzato assumendo l'elenco dei topic dal file `data.json` nel sotto gruppo
`[forum_topics][all]`. Per ogni nome (`name`) del topic in tale elenco, viene creato un contesto contenente solamente
quest'ultimo.

### Nel dettaglio
La creazione automatica dei contesti prende la lista dei topic e ne fa sue istanze, contenute in variabili di default.
Tali variabili sono chiamate prendendo il nome del topic (`name`), aggiungendo a esso la stringa "_TOPIC_SCOPE".
In python è possibile, infatti, creare una variabile con un nome contenuto in un'altra variabile usando il metodo
`globals()[NOMEVARIABILE]`; per esempio `globals()[pippo] = 2` crea una variabile che ha, come nome, il contenuto della
variabile `pippo` e vi assegna il valore intero 2 (`pippo` deve contenere una stringa).

La classe _Scope_ può essere istanziata anche per creare contesti personalizzati; è anche possibile aggiungere o 
togliere topic all'interno di un contesto, se esso è personalizzato e non di default.

## Classe _Limitations_
Questa è una sottoclasse di `IntEnum`: ogni intero (da 0 a 13) ne è un'istanza, che rappresenta una limitazione, 
che sono quelle editabili all'interno della finestra di gestione dei permessi all'interno di un gruppo Telegram. 
Quando un utente viene limitato, si può indicare un valore (per esempio _SEND_MESSAGES_) per limitare tale utente in 
relazione all'invio dei messaggi. È anche possibile indicare più istanze per limitare più azioni.

### Note
Se viene limitato un utente indicando solo una limitazione, le altre devono restare invariate. Il bot deve agire 
**solamente** sulle limitazioni indicate.