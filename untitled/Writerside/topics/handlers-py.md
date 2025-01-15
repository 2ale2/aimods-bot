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
<note>
    Per avere più informazioni, leggi la documentazione dei 
    <a href="https://docs.python-telegram-bot.org/en/stable/telegram.ext.conversationhandler.html">
    Conversation Handlers</a>.
</note>

1. **Handler per la Doppia Verifica al Join** – Gestisce il flusso della conversazione che guida l'utente nella doppia
verifica e nella lettura delle regole prima che la richiesta venga accettata (automaticamente).

<code-block>
ConversationHandler(
    entry_points=[
        ChatJoinRequestHandler(
            callback=handlers_function.new_member_joined_forum
        ),
        CommandHandler(
            "request", callback=handlers_function.new_member_joined_forum
        )
    ],
    states={
        RULES_ACCEPTED: [
            CallbackQueryHandler(
                callback=handlers_function.new_member_accepted_the_rules,
                pattern="^accept_rules.+$"
            )
        ]
    },
    fallbacks=[
        CommandHandler(
            "request", 
            callback=handlers_function.new_member_joined_forum)
    ],
    per_chat=False,
    name="join_handler",
    persistent=True
)
</code-block>

Gli `entry_points` contengono:
- `ChatJoinRequestHandler`: risponde quando un utente chiede di entrare nel gruppo; lancia la funzione 
`new_member_joined_forum` che invia un messaggio in privato all'utente (vedi in dettaglio nel doc dedicato).
- `CommandHandler`: risponde al comando `/request`, che può essere usato da un utente se non completa la doppia verifica
nel tempo prestabilito (vedi in dettaglio nel doc dedicato).

Gli `states` contengono:
- `RULES_ACCEPTED`: lo stato che identifica fa corrispondere l'accettazione delle regole ad una risposta dal bot,
sulla base dei casi possibili, gestiti dai vari handler; in questo caso, il `CallbackQueryHandler` gestisce la pressione
del tasto per accettare le regole.

I `fallbacks` contengono:
- `CommandHandler`: risponde al comando `/request`, che può essere usato da un utente se non completa la doppia verifica
nel tempo prestabilito. È un duplicato dell'_entry point_, che serve a gestire il caso in cui l'utente invii il comando
nello step errato.