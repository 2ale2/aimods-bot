# 📀 database_functions.py

> Contiene tutte le funzioni per interagire col database Postgres.

## Funzione `add_to_table`
> Aggiunge un record alla tabella indicata.

<note>
    <format style="bold">Parametri</format>
    <list>
    <li><code>table_name: str</code> – La tabella in cui aggiungere il record.</li>
    <li><code>content: Any</code> – Il contenuto da aggiungere.</li>
    </list>
</note>