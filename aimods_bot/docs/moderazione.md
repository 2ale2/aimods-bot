# Moderazione

La moderazione include l'**applicazione di limitazioni, ammonizioni, kick e ban a utenti** appartenenti alla community.
Tale applicazione può essere **manuale** (applicata da un moderatore) oppure **automatica** (nel caso di parole bandite o 
meccanismi più complessi come il _Machine Learning_).


## Limitazioni, Ammonizioni, Kick, Ban

Il bot ausilierà nella moderazione dei topic. Le misure sono le stesse disponili in tutti i gruppi o canali:
- **Limitazioni**: un utente può essere limitato nel compiere una o più azioni all'interno del gruppo per un periodo di
tempo limitato o a tempo indeterminato.
- **Ammonzioni**: un utente può essere ammonito; un certo numero di ammonizioni può comportare contromisure aggiuntive,
come un _kick_, una _limitazione_ o un _ban_ a tempo indeterminato. Un'ammonizione potrà avere una scadenza, dopo la
quale essa viene rimossa.
- **Kick**: un utente può essere "kickato" (cacciato) dal gruppo o dal canale, ma ha la possibilità di rientrare.
- **Ban**: un utente può essere bannato dal gruppo o dal canale e non ha la possibilità di rientrare.

### Comandi

#### Limitazioni

Il comando delle limitazioni è il più complesso da implementare: bisogna specificare l'utente sul quale applicare la
limitazione, quali azioni limitare, fino a quando e, facoltativamente, il motivo.

La cosa più semplice potrebbe essere 

`/limit @username tempo [azioni] [scope] [motivo]`

Il formato del tempo potrebbe essere il seguente:
- `1s` per un secondo;
- `1m` per un minuto;
- `1h` per un'ora;
- `1d` per un giorno;
- `1y` per un anno.

Per esempio: `30d12h30m20s` indica 30 giorni, 12 ore, 30 minuti e 20 secondi.

Le `[azioni]` potrebbero essere specificate sotto forma di interi separati da virgole; ogni intero corrisponde a una
azione:
- **SEND_MESAGGES**: 0
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

Lo `[scope]` è il contesto nel quale la limitazione è applicata. Di default è `FORUM_SCOPE`. Leggi 
_[Classi Peronalizzate](classi_personalizzate.md)_ per ulteriori dettagli sui contesti di moderazione.

Ecco un esempio di comando completo:

`/limit @user1 1d12h 2,10 REQUESTS_SCOPE Motivo`

Questo comando limita `@user1` per _1 giorno e 12 ore_ impedendogli di _inviare foto_ o _aggiungere altri membri_ 
nel _contesto dei topic delle richieste_ per il motivo '_Motivo_'.

#### Ammonizioni

Per ammonire un utente, il comando può essere più semplice:

`/warn @user1 tempo [scope] [motivo]`

Il formato del tempo potrebbe essere il seguente:
- `1s` per un secondo;
- `1m` per un minuto;
- `1h` per un'ora;
- `1d` per un giorno;
- `1y` per un anno.

Per esempio: `30d12h30m20s` indica 30 giorni, 12 ore, 30 minuti e 20 secondi.

Lo `[scope]` è il contesto nel quale la limitazione è applicata. Di default è `FORUM_SCOPE`. Leggi 
_[Classi Peronalizzate](classi_personalizzate.md)_ per ulteriori dettagli sui contesti di moderazione.

Ecco un esempio di comando completo:

`/warn @user1 1d12h REQUESTS_SCOPE Motivo`

Questo comando ammonisce `@user1` per _1 giorno e 12 ore_ nel _contesto dei topic delle richieste_ per il motivo 
_'Motivo'_. Dopo la durata dell'ammonizione, il contatore dei warn viene ridotto di 1.

## Limitazioni, Ammonizioni, Kick, Ban – Moderazione Circoscritta

La limitazione circoscritta offrirebbe la possibilità di **agire su un utente limitando le sue azioni all'interno di un
contesto ristretto a uno o più topic**. Ciò sarà possibile per le _limitazioni_ e le _ammonizioni_. 
Le limitazioni circoscritte possono essere applicate a contesti specifici, come richieste di applicazioni o richieste 
d'assistenza. Questo consente più modularità e controllo sui singoli topic.

Di default, il contesto sarà di applicazione sarà il generico su tutti i topic (`FORUM_SCOPE`); se il moderatore
desidera eseguire un'azione su un altro contesto, lo può fare specificandolo tramite un **comando che indichi il contesto**.

