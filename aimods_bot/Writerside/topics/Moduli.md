# Moduli

In questa sotto categoria spiegherò nel dettaglio la funzione di ciascun 
modulo, le funzioni (e ci che fanno) o le classi (e qual è la loro utilità) 
o le costanti che contiene.

## Struttura Generale

Ogni modulo contiene funzioni, classi e costanti specifiche che riguardano 
un aspetto specifico del funzionamento del bot:

- `core.py`: contiene tutte le funzioni che servono allo script per creare 
l'istanza completa di _Application_:
  - assume le variabili d'ambiente;
  - imposta `bot_data`.

  Questo modulo viene importato da `init.py` per creare l'istanza di 
  _Application_.
- `handlers.py`: crea gli handlers che poi saranno aggiunti all'istanza di
Application.
- `handlers_functions.py`: per ogni handler crea la sua funzione di callback.
- `init.py`: genera gli _[SCOPES](Scopes.md)_, crea l'istanza di _Application_
usando la persistenza e chiamando il modulo `core.py` per impostare `bot_data`,
dopodiché vi aggiunge gli handlers.
- `database_functions.py`: contiene tutte le funzioni che prevedono 
l'interazione tra AIMods Bot e il Database Postgres.
- `constants.py`: definisce le classi:
  - **Scope**: rappresenta uno _[Scope](Scopes.md)_;
  - **Scopes**: rappresenta un gruppo di _[Scope](Scopes.md)_.
  - **Limitations**: contiene degli interi che rappresentano dei permessi.
  - **DatabaseException**: rappresenta un errore generico durante un'interazione col
database.
  - **JobQueueException**: rappresenta un errore generico durante un'interazione con
la _JobQueue_.
  - **Exceptions**: raccoglie tutte le classi che rappresentano delle eccezioni.
  - **AttachmentType**: contiene degli interi che categorizzano un allegato di un 
messaggio.