# 🦊 core.py

> Questo modulo contiene tutte le funzioni che servono allo script per creare
> l'istanza completa di _Application_.

## Funzione `get_env`

> Ritorna il contenuto della variabile d'ambiente passata come parametro.
<note>
    <format style="bold">Parametri</format>
    <list>
    <li><code>env: str</code> – Nome della variabile desiderata.</li>
    </list>
</note>
<warning>Non è presente un controllo d'errore.</warning>

## Funzione `set_applicazion_data`

> Imposta il contenuto di bot_data all'avvio, qualora la persistenza 
> non sia aggiornata.

<note>
    <format style="bold">Parametri</format>
    <list>
    <li>
        <code>application: Application</code> – Istanza di <i>Application</i>.
    </li>
    </list>
</note>

La funzione crea una variabile `admins (dict)`:
<code-block>
{
    'id_utente1': 'nome_utente1',
    'id_utente2': 'nome_utente2',
    ...
}
</code-block>

Se `bot_data` non contiene la chiave '_admins_' oppure la contiene ma 
il contenuto è diverso da quello della variabile precedentemente creata 
`admins`, allora viene aggiornato il `bot_data`.

Viene quindi verificata la presenza della variabile contenente il gruppo 
della community dove opera il bot: 
1. viene posta in `group_chat_id` (`str`) la variabile d'ambiente corrispondente;
2. se la chiave 'group_chat_id' non è presente o c'è ma il valore è diverso
dal contenuto di `group_chat_id`, il valore viene aggiornato.

Vengono poi assunti, nella variabile `texts` (`dict`), i testi dei messaggi 
predefiniti e viene compiuta la medesima verifica fatta in precedenza per 
gli admin e per l'ID del gruppo.

## Funzione `get_data_from_json`

> Ritorna il contenuto desiderato (valore) del dizionario JSON, fornita la chiave.

<note>
    <format style="bold">Parametri</format>
    <list>
    <li>
        <code>data: str</code> – La chiave del dizionario di cui si vuole il valore.
    </li>
    </list>
</note>

## Funzione `get_admins_from_db`

> Ritorna un dizionario contenente le informazioni sugli admin della community.

La funzione interroga il db per ottenere gli ID e gli username degli admin 
dall'omonima tabella.

I record ottenuti vengono scompattati (tolte le parentesi graffe superflue) e posti 
in un dizionario del tipo:
<code-block>
{
    'id_utente1': '@username1',
    'id_utente2': '@username2',
    ...
}
</code-block>
Tale dizionario viene poi ritornato.

## Funzione `connect_to_database`

> Esegue una connessione al database Postgres.

Questa funzione viene usata da tutte le funzioni che richiedono una connessione al 
database. Il valore di ritorno è la variabile _Connection_ utilizzabile per compiere 
query.