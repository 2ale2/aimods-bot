# 🤚 handlers.py

> Il modulo comprende un'unica funzione `create_handlers` che crea e ritorna gli 
> handler necessari all'istanza di `Application` per funzionare.

## Funzione `create_handlers`

> Crea e ritorna una lista di _handlers_.

### Handlers per i comandi

Questi handlers possiedono generalmente due parametri:
- `command` – Il comando da gestire.
- `callback` – La funzione da eseguire.

1. **Avvio di una conversazione**: comando `/start`
<code-block>
handlers.append(
    CommandHandler(
        command="start", 
        callback=handlers_function.start_command
    )
)
</code-block>
2. **Stampa delle regole del gruppo**: comando `/rules`
<code-block>
handlers.append(
    CommandHandler(
        command="rules", 
        callback=handlers_function.send_rules
    )
)
</code-block>
3. **Cancellazione di un messaggio**: comando `/del`
<code-block>
handlers.append(
    CommandHandler(
        command="del", 
        callback=handlers_function.delete_group_message
    )
)
</code-block>
4. **Cambio dei permessi di un utente**: comando `/limit`
<code-block>
handlers.append(
    CommandHandler(
        command="limit", 
        callback=handlers_function.limit_user
    )
)
</code-block>

### Handlers di servizio

Questi handlers possiedono generalmente due parametri:
- `pattern` – Il pattern regex da gestire.
- `callback` – La funzione da eseguire.

1. **Handler per aprire i messaggi leggibili solo da un utente**.
<code-block>
handlers.append(
    CallbackQueryHandler(
        pattern="^open_private_alert.+$", 
        callback=handlers_function.alert_del_message_not_selected
    )
)
</code-block>
2. **Handler per la chiusura di un messaggio tramite inline keyboard**.
<code-block>
handlers.append(
    CallbackQueryHandler(
        pattern="^close.+$", 
        callback=handlers_function.callback_close_message
    )
)
</code-block>

### Conversation Handlers
<note>
    Questi handlers gestisco un flusso di conversazione. Sono in genere più complessi e hanno compiti molto specifici,
    come guidare un utente o un admin a compiere una determinata azione.
</note>