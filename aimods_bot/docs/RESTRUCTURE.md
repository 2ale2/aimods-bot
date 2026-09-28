# Ristrutturazione di `aimods_bot/src`

Stato: **piano verificato il 28 settembre 2026** su `master` `6cd4c46`.
Applicato per intero su una copia, da zero, con i soli strumenti di `tools/`:
84 commit, **329 test verdi dopo ogni singolo passo**, pyflakes fermo a 7 righe,
avvio del bot identico a prima, 0 violazioni delle regole di dipendenza.
L'unica riga di `src/` che cambia oltre agli import è l'indice di `paths.py`.

Tempo di esecuzione: circa 3 minuti, quasi tutti di test.

---

## In breve

Oggi `helpers/` è un contenitore di tutto e una funzionalità è sparsa in
6-7 cartelle (le richieste: `helpers/models`, `helpers/utils`, `core`,
`callbacks/panels/user`, `callbacks/panels/admin`, `bulk_sender`...).

Dopo:

- **`infra/` `core/` `ui/` `shared/`** — la base, divisa per *cosa è*;
- **`features/<nome>/`** — tutto quello che riguarda una funzionalità, insieme:
  modelli, repository, job, pannelli utente e admin;
- **`app/`** — avvio, registrazione degli handler e menù principali.

Il comportamento del bot non cambia. Cambiano solo i percorsi.

---

## Struttura finale

```
aimods_bot/src/
├── app/                        avvio e cablaggio — può importare tutto
│   ├── main.py                 entrypoint (Dockerfile: CMD aimods_bot/src/app/main.py)
│   ├── setup.py                caricamento dati e ripianificazione job al boot
│   ├── shutdown.py
│   ├── handlers/               registrazione degli handler PTB
│   │   ├── conversation.py     ConversationHandler principale
│   │   ├── channel.py          post del canale → recap
│   │   └── commands/           handler dei comandi (DORMIENTI, vedi sotto)
│   └── menus/                  i punti d'ingresso della navigazione
│       ├── start.py            /start e pannello principale
│       ├── admin.py            admin_main_router
│       ├── user.py             user_main_router
│       ├── general.py          general_router
│       └── tools/              menù "Strumenti"
│
├── core/                       nucleo condiviso
│   ├── customcontext.py        CustomContext + BotData/ChatData/UserData
│   ├── constants.py            costanti ed enum
│   ├── config/                 models.py (ex core/pydantic.py), loader.py, accessor.py
│   ├── exceptions.py  media.py  permissions.py  paths.py
│   └── models.py               MediaItem, CanUserRequest, MessageTemplate
│
├── infra/                      tutto ciò che parla col mondo esterno
│   ├── log.py                  il logger "bot" (ex helpers/loggers.py)
│   ├── files.py                file, JSON, YAML, LaTeX → PDF
│   ├── db/                     pool.py, queries.py (ex helpers/database.py), persistence.py
│   ├── scheduling/             job_queue.py (job generici), job_names.py, jobs.py
│   └── telegram/               utils.py, botapi_10_1.py, chat.py, filters.py,
│                               command_parser.py, auth.py
│
├── ui/                         mattoni dei pannelli
│   ├── panel.py                Panel, PanelConfig, ButtonItem (ex helpers/models/ui.py)
│   ├── helpers.py              create_and_render_panel, chunk_buttons, pannelli di errore...
│   ├── routing.py              PathBuilder
│   ├── callback_data.py  alerts.py
│   ├── path_navigation/        segmenti dei path
│   └── conversation_states/    stati delle conversazioni
│
├── shared/                     funzioni pure: text_utils.py, time_utils.py
│
└── features/
    ├── requests/               RICHIESTE
    │   ├── models.py  section.py  repository.py  notifications.py
    │   ├── jobs.py             callback dei job (cooldown, limitazioni, rimozione, riapertura)
    │   ├── scheduling.py       chi pianifica quei job
    │   ├── user/               wizard e gestione lato utente (+ management/)
    │   ├── admin/              gestione lato admin (+ limit/, sections_management/)
    │   └── archive/            archivio richieste di un utente + PDF (latex.py)
    ├── reminders/              PROMEMORIA: models, repository, schedule, jobs, panels/
    ├── moderation/             MODERAZIONE
    │   ├── members.py          ban, avvisi, membro in cache, check_auth (ex user_utils)
    │   ├── event_log.py        log ingressi/ban nel canale (ex core/logger.py)
    │   ├── commands/           ban, kick, limit, mute, warn, router
    │   └── panels/             antispam, antiflood, punizioni, whitelist...
    ├── service/                comandi di servizio: echo, test, troubleshooting, check, reboot
    ├── onboarding/             INGRESSO NEL GRUPPO: join request (Guard Mode),
    │                           sweeper, Mini App di verifica, benvenuto, regole
    ├── recap/                  channel_recap.py
    └── settings/               impostazioni notifiche: admin/, user/
```

`misc/`, `docs/`, `tests/` restano dove sono: `docker-compose.yml` monta un file
dentro `aimods_bot/misc/` e vari percorsi sono scritti a mano (vedi Trappole).

La corrispondenza vecchio → nuovo, file per file, è `tools/restructure_moves.txt`:
è anche il riferimento per aggiornare i percorsi citati in HANDOFF e DESIGN.

---

## Regole di dipendenza

Chi può importare chi, dal basso verso l'alto:

| Package      | Può importare                                                      |
|--------------|--------------------------------------------------------------------|
| `shared`     | solo `core.constants`                                              |
| `core`,`infra` | `shared`, `core`, `infra` — sono la base, si usano a vicenda. `core` può importare anche i **modelli** delle feature: `customcontext` e la config ne contengono lo stato persistito |
| `ui`         | `shared`, `core`, `infra`, `ui`                                    |
| `features.X` | la base, `ui`, la propria feature, più `moderation.members`, `moderation.event_log`, `requests.models`, `requests.section` |
| `app`        | tutto                                                              |

Eccezioni accettate, ognuna col suo perché, in `tools/check_layers.py`:

- `features.requests.user.handle → app.menus.start`: dal wizard si torna al menù;
- `infra.scheduling.job_names` / `jobs → features.requests.section`: registro
  centrale dei job, al riavvio li rilegge tutti;
- `core.customcontext → features.requests.jobs`: import ritardato dentro
  `edit_request_status`, esiste proprio per evitare un ciclo.

**A ristrutturazione finita, `python tools/check_layers.py` deve dare 0
violazioni, e restarci.** Durante le fasi intermedie ne dà molte, perché le
vecchie cartelle (`helpers/`, `callbacks/`...) non rientrano in nessuna regola:
è normale, conta solo il risultato dopo la 2g. Aggiungere un'eccezione è lecito,
ma con il motivo scritto accanto.

---

## Gli strumenti

Tutti in `tools/`, tutti senza commit automatici salvo `apply_moves.py`.

| File | Cosa fa |
|------|---------|
| `move_module.py OLD NEW [--init-only]` | `git mv` di un modulo o package + riscrittura di tutti gli import in `src/` e `tests/`, e dei percorsi nel Dockerfile. Si rifiuta di partire se trova `from <package> import <modulo>` |
| `move_symbols.py OLD NEW nomi...` | sposta funzioni/classi fra moduli, sistema gli import del vecchio e del nuovo, spezza le righe d'import di chi le usa |
| `apply_moves.py [--phase X] [--dry-run]` | esegue `restructure_moves.txt` un passo alla volta: sposta → pytest → pyflakes → commit. Si ferma al primo errore **senza** committare. Riprende da dove era rimasto |
| `check_layers.py` | controlla le regole di dipendenza |
| `restructure_moves.txt` | la mappa: una riga, un commit |

E un test nuovo: **`tests/test_imports.py`** importa *ogni* modulo di `src/`.
Senza, `pytest` controlla solo i moduli che i test toccano: l'import circolare
di `requests_management` è uscito solo all'avvio proprio per questo. Va tenuto
anche dopo la ristrutturazione.

---

## Procedura

### 0. Prima di cominciare

```bash
git switch development && git pull origin development
git status                                   # deve essere pulito
git tag pre-restructure-20260928 && git push origin pre-restructure-20260928
git switch -c refactor/structure
```

Durante la ristrutturazione **non si sviluppa altro**, su nessun branch: ogni
modifica fatta in parallelo a un file che si sposta diventa un conflitto.

### Fase 0 — preparazione (a mano, un commit)

1. Copia i file nuovi: `tools/` (i cinque file) e `aimods_bot/tests/test_imports.py`.
2. Le forme d'import che una sostituzione di testo non sa riscrivere:
   - `callbacks/commands/admin/kick.py`, `warn.py`, `limit.py`:
     `from aimods_bot.src.helpers.constants import constants` (con o senza
     `as constants`) → `import aimods_bot.src.helpers.constants.constants as constants`
   - `tests/test_channel_membership.py`: le righe
     `from aimods_bot.src.callbacks.panels.admin.requests_management import render as admin_render, handle`,
     `... import route as admin_route` e `from aimods_bot.src.core import customcontext`
     diventano `import <percorso completo del modulo> as <nome>`. `admin_route`
     non è più usato: toglilo.
   - `callbacks/panels/user/request/handle.py`: `user_requests_management_route`
     va importato da `...callbacks.panels.user.request.route`, non da
     `...callbacks.panels.user` (è un re-export del package, che diventerà un menù).
3. `callbacks/panels/admin/requests_management/route.py`: nell'import da
   `handle`, togli `log` (`import handle_membership_op, log` → `import handle_membership_op`).
   È l'ottava riga di pyflakes: riporta la linea di base a 7.
4. Controlla e committa:
   ```bash
   python -m pytest aimods_bot/tests/ -q        # tutti verdi, test_imports compreso
   python -m pyflakes aimods_bot/src/ | wc -l   # 7
   git add -A tools aimods_bot && git commit -m "fase 0: test di import totale, strumenti, import normalizzati"
   ```

Se dimentichi un punto del passo 2, `move_module.py` si ferma da solo e dice quale file.

### Fasi 1 e 2 — gli spostamenti

```bash
python tools/apply_moves.py --dry-run     # l'elenco di cosa farà
python tools/apply_moves.py --phase 1a    # una fase alla volta, guardando il risultato
python tools/apply_moves.py --phase 1b
...                                        # 1a 1b 1c 1d 2a 2b 2c 2d 2e 2f 2g
```

oppure tutto in una volta con `python tools/apply_moves.py`. Ogni passo è un
commit `refactor: sposta X in Y`, quindi `git log` racconta cosa è successo e
`git log --follow` ritrova la storia di ogni file: git riconosce 189 file come
rinominati. Gli altri sono i 3 file nuovi della fase 2g e qualche file vuoto,
che non ha storia da perdere.

I due passi segnati `!` nella mappa li fa lo strumento da solo:
- `paths.py`: `parents[3]` → `parents[2]`, e verifica che `MISC_DIR` esista;
- pulizia: toglie `helpers/`, `callbacks/`, `handlers/`, `tasks/`, `main/`, ma
  solo se contengono esclusivamente `__init__.py` vuoti.

La fase **2g** è quella che sposta funzioni invece di file: i job di richieste e
promemoria escono da `infra/scheduling/job_queue.py`, gli helper dei pannelli
escono da `infra/telegram/utils.py`. Dopo la 2g, `check_layers.py` dà 0.

**Se un passo si ferma:** il passo fallito resta nella working tree, non
committato. Guardalo con `git status` / `git diff`; per scartarlo
`git reset --hard && git clean -fd aimods_bot`, poi correggi e rilancia:
riparte dal passo fallito.

### Dopo

1. Ritocchi facoltativi, a mano, in commit separati:
   - in `infra/scheduling/job_queue.py` restano le intestazioni di sezione
     `# ========== JOB: ...` ormai vuote;
   - gli import riscritti da `move_symbols.py` hanno perso le righe vuote fra i
     gruppi e sono ordinati come capita.
2. Aggiorna i percorsi citati in HANDOFF e DESIGN usando `restructure_moves.txt`.
3. Merge e deploy come sempre (`--build` obbligatorio: è cambiato il `CMD`).
   Nei log cambiano i **nomi** dei logger (`bot.aimods_bot.src.helpers...` →
   `bot.aimods_bot.src.infra...`), non i messaggi: le righe da cercare al primo
   avvio restano le stesse.
4. Tieni il tag `pre-restructure-20260928` finché non sei sicuro, poi toglilo.

---

## Trappole

Cose che nessun import segnala e che la procedura già gestisce. Da tenere a
mente per gli spostamenti futuri.

- **`core/paths.py` calcola la radice con `Path(__file__).parents[N]`.** Se lo
  sposti di livello, `N` va cambiato; `move_module.py` avvisa per ogni file che
  usa `__file__`.
- **`docker-compose.yml` monta `BotConfigurationStructure.yml` dentro
  `aimods_bot/misc/`.** Se un giorno si sposta `misc/`, Docker crea una
  *cartella* vuota al posto del file e la configurazione sparisce. Per questo
  `misc/` non si tocca.
- **Percorsi scritti a mano, relativi alla radice del repo:**
  `"aimods_bot/misc/data.json"` (`infra/files.py`), `YAML_CONFIG_PATH`
  (`core/constants.py`), `/app/aimods_bot/misc/images/...`
  (`features/recap/channel_recap.py`). Funzionano perché nel container la
  cartella corrente è `/app`. `test_imports.py` fa lo stesso con `os.chdir`.
- **`python aimods_bot/src/app/main.py` mette `aimods_bot/src/app/` in testa a
  `sys.path`**, e lì ora ci sono `setup.py`, `handlers/`, `menus/`. Oggi nessun
  pacchetto installato ha quei nomi (verificato); se un giorno una dipendenza
  si chiamasse `handlers`, passare a `CMD ["python", "-m", "aimods_bot.src.app.main"]`.
- **`core.constants.pyro_instance` è stato mutabile**, assegnato a runtime. Si
  legge come `constants.pyro_instance` dopo `import ... constants as constants`:
  un `from ...constants import pyro_instance` catturerebbe il `None` iniziale.
  Se un giorno lo si sposta, va spostato **come modulo**, non come nome.
- **Le cartelle con il solo `__pycache__`** (resti di un'esecuzione precedente)
  confondono `git mv`: `move_module.py` le toglie prima di spostare.
- **I package segnaposto vuoti** (`moderation/panels/banned_words`,
  `controls`, `forbidden_content`, `message_lenght`, `antispam/media`,
  `conversation_states/group_settings`...) si spostano insieme al padre e restano.

---

## Codice dormiente — da decidere

`app/main.py` registra solo: la conversazione privata, `close_menu_handler`, i
post del canale e le join request. **Nessuno registra**:

- `app/handlers/commands/admin/moderation_handler.py` — `/ban /kick /mute /warn /limit`...
- `app/handlers/commands/admin/service_handler.py` — echo e `/test`
- `app/handlers/commands/admin/troubleshooting_handlers.py`
- `app/handlers/commands/check_command_handler.py`
- `features/onboarding/new_member.py`, `accept_rules.py` — benvenuto e regole

Il codice c'è e si importa (lo verifica `test_imports.py`), ma in produzione è
fermo. Nella storia di git non risulta un momento in cui fosse collegato da
`main`. La ristrutturazione li sposta senza cambiarne lo stato; decidere dopo
se ricollegarli o toglierli. Attenzione: `service_handler.py` all'import legge
`MYID` e `data.json`, e `event_log.py` legge `CHANNEL_LOGGER_ID`.

---

## Cosa NON fa questa ristrutturazione (volutamente)

- **Non tocca la logica.** Nessun metodo cambia firma, nessuna funzione cambia
  corpo. `CustomContext` resta il punto centrale, con i suoi metodi di dominio
  (cooldown, limitazioni, stato delle richieste, iscrizione al canale).
  Portarli in `features/requests/` come funzioni cambierebbe centinaia di
  chiamate `context.x()`: è un refactor, non uno spostamento, e va fatto a parte.
- **Non divide `core/constants.py`** (enum di richieste e promemoria insieme alle
  costanti generali) né toglie i wizard da `customcontext.py`. Sono file misti ma
  non violano le regole di dipendenza: dividerli è possibile in seguito con
  `move_symbols.py`, un file alla volta.
- **Non rinomina i segmenti dei path dei bottoni** (`admin/tools/reminder`...):
  quelli vivono nella cache dei callback e nei messaggi già inviati. Cambia la
  posizione dei file, non le stringhe dei path.

---

## Per Claude Code

Da incollare all'inizio della sessione:

> Stiamo applicando `aimods_bot/docs/RESTRUCTURE.md`. Leggilo tutto prima di fare qualunque cosa.
> Regole:
> - gli spostamenti si fanno SOLO con `tools/apply_moves.py` (una fase alla
>   volta) o, fuori mappa, con `tools/move_module.py` / `tools/move_symbols.py`;
>   mai a mano, mai riscrivendo gli import con editor o sed;
> - un passo = un commit; mai spostamenti e modifiche di logica nello stesso commit;
> - dopo ogni passo: `python -m pytest aimods_bot/tests/ -q` verde e
>   `python -m pyflakes aimods_bot/src/ | wc -l` ≤ 7 (lo fa già `apply_moves.py`);
>   alla fine di tutto `python tools/check_layers.py` deve dare 0 violazioni;
> - se uno strumento si ferma, NON aggirarlo: mostrami l'errore e fermati;
> - non fare push e non toccare `master`.

---

## Tornare indietro

- **Durante il lavoro** (un passo andato male): `git reset --hard HEAD` torna
  all'ultimo passo riuscito, dato che ogni passo è un commit.
- **Tutto il lavoro**: `git switch development` e `git branch -D refactor/structure`;
  `development` non è mai stato toccato.
- **Dopo il merge**: `git reset --hard pre-restructure-20260928` su un branch
  nuovo, oppure `git revert` del merge. In produzione basta rifare il deploy dal
  tag: il database e la persistenza non contengono percorsi di moduli
  (verificato: `chat_data`/`bot_data` sono JSON per nome di campo, la cache dei
  callback contiene stringhe di path, i job non sono persistiti).
