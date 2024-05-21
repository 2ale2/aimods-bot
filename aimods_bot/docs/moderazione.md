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

I comandi sono lo strumento tramite cui i moderatori possono eseguire azioni sul canale/gruppo. I comandi possono 
prevedere una sintassi che richiede l'indicazione di una durata (per ammonizioni e limitazioni) e di uno scope, ovvero
un contesto nel quale l'azione è eseguita. Il motivo è sempre facoltativo ma raccomandato.

#### Durata

Il formato del `[tempo]` potrebbe essere il seguente:
- `1s` per un secondo;
- `1m` per un minuto;
- `1h` per un'ora;
- `1d` per un giorno;
- `1y` per un anno.

Per esempio: `30d12h30m20s` indica 30 giorni, 12 ore, 30 minuti e 20 secondi.

#### Scope

Lo `[scope]` è il contesto nel quale la limitazione è applicata. Di default è `FORUM_SCOPE`. Leggi
_[Classi Personalizzate](classi_personalizzate.md)_ per ulteriori dettagli sui contesti di moderazione.

#### Limitazioni

Il comando delle limitazioni è il più complesso da implementare: bisogna specificare l'utente sul quale applicare la
limitazione, quali azioni limitare, fino a quando e il motivo.

La cosa più semplice potrebbe essere 

`/limit @username [tempo] [azioni] [scope] [motivo]`

La sintassi del `[tempo]` è [questa](#durata).

Le `[azioni]` potrebbero essere specificate sotto forma di interi separati da virgole; ogni intero corrisponde a una
azione; maggiori dettagli nel topic delle _[Classi Personalizzate](classi_personalizzate.md#classe-limitations)_.

I dettagli sullo `[scope]` si trovano [qui](#scope).

Ecco un esempio di comando completo:

`/limit @user1 1d12h 2,10 REQUESTS_SCOPE Motivo`

Questo comando limita `@user1` per _1 giorno e 12 ore_ impedendogli di _inviare foto_ o _aggiungere altri membri_ 
nel _contesto dei topic delle richieste_ per il motivo '_Motivo_'.

#### Ammonizioni

Per ammonire un utente, il comando può essere più semplice:

`/warn @user1 tempo [scope] [motivo]`

Ecco un esempio di comando completo:

`/warn @user1 1d12h REQUESTS_SCOPE Motivo`

Questo comando ammonisce `@user1` per _1 giorno e 12 ore_ nel _contesto dei topic delle richieste_ per il motivo 
_'Motivo'_. Dopo la durata dell'ammonizione, il contatore dei warn viene ridotto di 1.

#### Kick

Per kickare un utente il comando può essere:

`/kick @user1 [motivo]`

Questo comando kicka `@user1` per il motivo `[motivo]`.

#### Ban

Per bannare un utente il comando può essere:

`/ban @user1 [motivo]`

Questo comando banna `@user1` per il motivo `[motivo]`.

#### Comandi Inversi

Se è possibile eseguire un'azione di moderazione su un utente, è anche possibile annullarla con i relativi comandi:

- `/unlimit @user1 [azioni]`: toglie una o più limitazioni, se precedentemente applicate, a `@user1`;
- `/unwarn @user1`: toglie uno warn da `@user1`, se applicato;
- `/unban @user1`: toglie il ban da `@user1`, se applicato.

## Limitazioni, Ammonizioni, Kick, Ban – Moderazione Circoscritta

La limitazione circoscritta offrirebbe la possibilità di **agire su un utente limitando le sue azioni all'interno di un
contesto ristretto a uno o più topic**. Ciò sarà possibile per le _limitazioni_ e le _ammonizioni_. 
Le limitazioni circoscritte possono essere applicate a contesti specifici, come richieste di applicazioni o richieste 
d'assistenza. Questo consente più modularità e controllo sui singoli topic.

Di default, il contesto sarà di applicazione sarà il generico su tutti i topic (`FORUM_SCOPE`); se il moderatore
desidera eseguire un'azione su un altro contesto, lo può fare specificandolo tramite un **comando che indichi il 
contesto**.

