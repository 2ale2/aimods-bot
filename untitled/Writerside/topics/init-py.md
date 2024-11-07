# 🐭 init.py

1️⃣ Crea un logger specifico di nome "`httpx`" e setta il livello minimo 
a `WARNING`. Questo logger viene usato per gestire i log relativi alle 
richieste HTTP. Se il livello fosse più basso, verremmo spammati log che,
alla fine, sono inutili.

2️⃣ Crea un'istanza di `Scopes` (per i dettagli, vedi [_Scopes_](Scopes.md)).

<note>È davvero necessario crearla qui?</note>

3️⃣ Definisce il `main`, che crea l'istanza di `Application`; per farlo:

- assume il token da una variabile d'ambiente;
- inizializza la persistenza instaurando una connessione con il database Postgres;
- lancia la funzione di _post-init_ `set_application_data` (per i dettagli vedi 
il modulo _Core_)

Dopo aver creato l'istanza, vengono aggiunti gli handlers creati da una 
funzione specifica nel modulo `handlers.py` (per i dettagli vedi 
`handlers.create_handlers()`) e infine pone l'applicazione in attesa.