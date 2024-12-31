# 🤚 handlers.py

> Il modulo comprende un'unica funzione `create_handlers` che crea e ritorna gli 
> handler necessari all'istanza di `Application` per funzionare.

## Funzione `create_handlers`

> Crea e ritorna una lista di _handlers_.

### Handlers per i comandi
1. **Avvio di una conversazione**: comando `/start`
2. **Stampa delle regole del gruppo**: comando `/rules`
3. **Cancellazione di un messaggio**: comando `/del`
4. **Cambio dei permessi di un utente**: comando `/limit`