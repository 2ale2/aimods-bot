# Custom Classes

Ho creato alcune classi personalizzate. In questo file viene descritta la loro struttura e implementazione all'interno
del bot.

La classi personalizzate sono:
- _Scope_ (assieme alla classe _Scopes_);
- _Limitations_.

## Classi _Scope_ e _Scopes_
La classe *Scope* rappresenta un contesto ("scope", non "context" per non confonderlo con una classe già presente in PTB), 
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

La classe Scopes viene istanziata all'avvio del bot, per consentire l'aggiunta di eventuali istanze di Scope aggiuntive
personalizzate. **Qualora una nuova istanza dovesse essere aggiunta, essa deve essere salvata all'interno del database o 
della persistenza, per poter essere poi ripresa in caso di arresto imprevisto del bot**.

## Classe _Limitations_
Questa è una sottoclasse di `IntEnum`: ogni intero (da 0 a 13) ne è un'istanza, che rappresenta una limitazione, 
che sono quelle editabili all'interno della finestra di gestione dei permessi all'interno di un gruppo Telegram. 
Quando un utente viene limitato, si può indicare un valore (per esempio _SEND_MESSAGES_) per limitare tale utente in 
relazione all'invio dei messaggi. È anche possibile indicare più istanze per limitare più azioni.

Le limitazioni nel dettaglio:
- **SEND_MESSAGES**: 0
- **SEND_ALL_MEDIA**: 1
- **SEND_PHOTO**: 2
- **SEND_VIDEO_FILES**: 3
- **SEND_VIDEO_MESSAGES**: 4
- **SEND_MUSIC**: 5
- **SEND_FILES**: 6
- **SEND_STICKERS_GIFTS**: 7
- **SEND_EMBEDDED_LINKS**: 8
- **SEND_POOLS**: 9
- **ADD_MEMBERS**: 10
- **CREATE_TOPICS**: 11
- **PIN_MESSAGES**: 12
- **CHANGE_GROUP_INFO**: 13

Questa classe non viene istanziata all'avvio del bot, perché immutabile. I valori al suo interno sono recuperabili, per
esempio, come `Limitation.SEND_MESSAGES`.

### Note
Se viene limitato un utente indicando solo una limitazione, le altre devono restare invariate. Il bot deve agire 
**solamente** sulle limitazioni indicate.