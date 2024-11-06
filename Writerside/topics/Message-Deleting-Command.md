# Message Deleting Command
Il comando `/del` rimuove il messaggio allegato dal canale.

## Funzionamento
Un moderatore o chi ha la possibilità di farlo fornisce il comando `/del`, unito a motivazione obbligatoria,
allegando un messaggio di un altro utente che **non deve essere un altro moderatore o admin**.

Il messaggio allegato viene rimosso e viene mostrato un feedback pubblico contenente il mittente del messaggio originale
e la motivazione indicata.

### Sul Database
Il messaggio viene salvato all'interno della tabella _deleted_messages_:
- `message_id`: l'identificativo del messaggio rimosso;
- `admin`: l'id di chi ha compiuto l'azione;
- `deletion_time`: il tempo di esecuzione della rimozione;
- `user_id`: mittente del messaggio rimosso;
- `telegram_message`: contenuto del messaggio (**se testuale**);
- `reason`: la motivazione specificata.

#### Nota
Il salvataggio dei messaggi nella tabella _deleted_messages_ riguarda **solo** i messaggi rimossi tramite comando;
rimozioni automatiche del bot o manuali da parte di admin o moderatori non vengono salvate.