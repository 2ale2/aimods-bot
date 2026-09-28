#!/usr/bin/env python3
"""
Controlla la direzione degli import fra i package di aimods_bot/src.

    python tools/check_layers.py          # elenca le violazioni, esce con 1 se ce ne sono

Regole (chi può importare chi), dal basso verso l'alto:

    shared      → solo core.constants
    core, infra → shared, core, infra             (sono la base: si usano a vicenda)
                  core può importare anche i MODELLI delle feature, perché
                  customcontext e config ne contengono lo stato persistito
    ui          → shared, core, infra, ui
    features.X  → shared, core, infra, ui, features.X
                  + i moduli di feature elencati in SHARED_FEATURE_MODULES
    app         → tutto

Le eccezioni note e accettate stanno in ALLOWED_EXCEPTIONS, ciascuna col suo perché.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "aimods_bot" / "src"
PREFIX = "aimods_bot.src."

# Moduli di feature che tutte le altre feature possono usare.
SHARED_FEATURE_MODULES = {
    "features.moderation.members",     # ban, avvisi, membro in cache: servono ovunque
    "features.moderation.event_log",   # log di ingressi/ban nel canale
    "features.requests.models",        # le impostazioni descrivono le sezioni delle richieste
    "features.requests.section",
}

# Moduli di feature che `core` può importare: lo stato persistito ne contiene i modelli.
CORE_MAY_IMPORT = {
    "features.requests.models",
    "features.requests.section",
    "features.reminders.models",
    "features.reminders.schedule",
}

# (importatore, importato) → motivo. Importatore/importato come prefissi puntati.
ALLOWED_EXCEPTIONS = {
    ("features.requests.user.handle", "app.menus.start"):
        "dal wizard si torna al menù principale; start è il punto d'ingresso di tutto",
    ("infra.scheduling.job_names", "features.requests.section"):
        "registro centrale dei nomi dei job: al riavvio li rilegge tutti, di ogni tipo",
    ("infra.scheduling.jobs", "features.requests.section"):
        "come sopra: dati dei job di tutte le feature",
    ("core.customcontext", "features.requests.jobs"):
        "import ritardato dentro edit_request_status, per evitare il ciclo di import",
}


def module_name(path: Path) -> str:
    rel = path.relative_to(SRC).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def layer(mod: str) -> str:
    parts = mod.split(".")
    return ".".join(parts[:2]) if parts[0] == "features" else parts[0]


def imports_of(path: Path, me: str) -> set[str]:
    out: set[str] = set()
    pkg = me if path.name == "__init__.py" else me.rpartition(".")[0]
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out |= {a.name[len(PREFIX):] for a in node.names if a.name.startswith(PREFIX)}
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = pkg
                for _ in range(node.level - 1):
                    base = base.rpartition(".")[0]
                out.add(base + ("." + node.module if node.module else ""))
            elif node.module and node.module.startswith(PREFIX):
                out.add(node.module[len(PREFIX):])
    return out


def allowed(src: str, dst: str) -> bool:
    a, b = layer(src), layer(dst)
    top_a, top_b = a.split(".")[0], b.split(".")[0]
    if a == b or top_a == "app":
        return True
    if any(src.startswith(i) and dst.startswith(d) for i, d in ALLOWED_EXCEPTIONS):
        return True
    if top_a == "shared":
        return dst == "core.constants"
    if top_a in ("core", "infra"):
        if top_b in ("shared", "core", "infra"):
            return True
        return top_a == "core" and any(dst.startswith(m) for m in CORE_MAY_IMPORT)
    if top_a == "ui":
        return top_b in ("shared", "core", "infra", "ui")
    if top_a == "features":
        if top_b in ("shared", "core", "infra", "ui"):
            return True
        return any(dst.startswith(m) for m in SHARED_FEATURE_MODULES)
    return False


def main() -> int:
    violations = []
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        me = module_name(path)
        if not me:
            continue
        for dst in sorted(imports_of(path, me)):
            if dst and not allowed(me, dst):
                violations.append((me, dst))
    for me, dst in violations:
        print(f"{layer(me):22s} {me}  →  {dst}")
    print(f"\n{len(violations)} violazioni")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
