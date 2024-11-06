# Database

Il bot di _A&I Mods_, per le
[funzionalità previste](https://jolly-parade-086.notion.site/A-I-Mods-Bot-9fb0cfd3da114cf28a89a0faa4c6d5b6?pvs=4), 
richiede l'uso della persistenza implementata in PTB unitamente all'uso di un database.

La scelta di quali informazioni vadano salvate in una o nell'altra struttura dati dipende dalla natura dei dati stessi 
e dalla frequenza di aggiornamento.

### Cosa si Vuole Memorizzare

Le informazioni da raccogliere riguardano tutte (o quasi) le funzioni specificate; nel dettaglio:
- Topic Generale _A&I Mods_
  - _Moderare la chat_
    - **limitazioni** (data, from, cosa, causa, utente, admin, scadenza);
    - **messaggi rimossi** (data, causa, utente, admin);
    - **ammonizioni** (data, from, causa, utente, admin, scadenza);
    - **kick** (data, causa, utente, admin);
    - **ban** (data, causa, utente, admin);
  - _Gestione dei topic e dei post_
    - ~~**post** (identificativo, data, piattaforma, app/sw/plugin, versione, link, stato, contenuto);~~ **da definire**
    - **richieste** (identificativo, utente, data, piattaforma, app/sw/plugin, versione, funzionalità richieste, stato);
    - **chiusura topic** (topic, data chiusura, data riapertura, causa, admin);
- Canale _Android&iOS Modding_
  - **raccolta statistiche** (numero post (per giorno, mese, anno));
  - **verifica numero downloads file**;
  - **lista file up**;
  - **lista file eliminati**.
- Integrazione altri servizi
  - **Bestemmiometro** (data, admin, bestemmia, parziale)

Oltre a ciò, ci sono alcune informazioni che non riguardano propriamente le funzioni del bot, ma sono fondamentali o
utili a un coerente funzionamento:

- **Admin** (user_id, nome_utente, ruolo, data join, stato, permessi);
- **Ruoli** (id, nome, lista_admin, descrizione);
- **Permessi** (id, nome, descrizione).

