#!/usr/bin/env python3
"""
Sposta un modulo o un package di `aimods_bot/src` e riscrive tutti gli import.

    python tools/move_module.py helpers.database infra.db.queries
    python tools/move_module.py helpers.constants.path_navigation ui.path_navigation
    python tools/move_module.py --init-only callbacks.panels.admin app.menus.admin

I percorsi sono puntati e relativi ad `aimods_bot.src`.

- modulo (`x/y.py`)          → sposta il file;
- package (`x/y/`)           → sposta tutta la cartella, sottomoduli compresi;
- `--init-only` (package)    → sposta SOLO il codice di `x/y/__init__.py` in un
                               modulo; la cartella deve essere già vuota di
                               sottomoduli (spostali prima).

Cosa fa: `git mv`, crea gli `__init__.py` mancanti nella destinazione, riscrive
`aimods_bot.src.<vecchio>` → `aimods_bot.src.<nuovo>` in tutti i .py di
`aimods_bot/src` e `aimods_bot/tests`, e la forma con le barre in Dockerfile e
docker-compose.yml. NON fa commit: si controlla e si committa a mano.

Si ferma prima di toccare qualunque cosa se trova un import nella forma
`from aimods_bot.src.<padre> import <modulo>`, che una sostituzione di testo non
può riscrivere correttamente (vedi la fase 0 di aimods_bot/docs/RESTRUCTURE.md).
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "aimods_bot" / "src"
PREFIX = "aimods_bot.src"
CODE_DIRS = [REPO / "aimods_bot" / "src", REPO / "aimods_bot" / "tests"]
SLASH_FILES = [REPO / "Dockerfile", REPO / "docker-compose.yml"]


def die(msg: str) -> None:
    print(f"ERRORE: {msg}", file=sys.stderr)
    sys.exit(1)


def to_path(dotted: str) -> Path:
    return SRC.joinpath(*dotted.split("."))


def git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO, check=True)


def py_files() -> list[Path]:
    files: list[Path] = []
    for d in CODE_DIRS:
        files += [p for p in d.rglob("*.py") if "__pycache__" not in p.parts]
    return files


def ensure_packages(target_dir: Path) -> None:
    """Crea gli `__init__.py` mancanti da `src/` fino a `target_dir` compresa."""
    d = target_dir
    chain = []
    while d != SRC and SRC in d.parents:
        chain.append(d)
        d = d.parent
    for pkg in reversed(chain):
        pkg.mkdir(exist_ok=True)
        init = pkg / "__init__.py"
        if not init.exists():
            init.touch()
            git("add", str(init.relative_to(REPO)))


def check_parent_imports(old: str) -> None:
    """Blocca `from aimods_bot.src.<padre> import <vecchio_nome>`."""
    parent, _, name = old.rpartition(".")
    pat = re.compile(
        rf"^\s*from\s+{re.escape(PREFIX)}\.{re.escape(parent)}\s+import\s+[^\n]*\b{re.escape(name)}\b",
        re.M,
    )
    offenders = [p for p in py_files() if pat.search(p.read_text(encoding="utf-8"))]
    if offenders:
        lines = "\n  ".join(str(p.relative_to(REPO)) for p in offenders)
        die(
            f"import nella forma `from {PREFIX}.{parent} import {name}` in:\n  {lines}\n"
            f"Riscrivili prima come `import {PREFIX}.{old} as {name}` (fase 0)."
        )


def rewrite(old: str, new: str, exact: bool) -> list[Path]:
    # exact: il vecchio nome non deve essere seguito da `.` (serve per --init-only,
    # dove i sottomoduli con lo stesso prefisso NON si spostano).
    tail = r"(?![\w.])" if exact else r"(?!\w)"
    dotted = re.compile(rf"\b{re.escape(PREFIX)}\.{re.escape(old)}{tail}")
    changed = []
    for p in py_files():
        text = p.read_text(encoding="utf-8")
        new_text = dotted.sub(f"{PREFIX}.{new}", text)
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
            changed.append(p)

    old_slash = "aimods_bot/src/" + old.replace(".", "/")
    new_slash = "aimods_bot/src/" + new.replace(".", "/")
    slash = re.compile(rf"{re.escape(old_slash)}(?=[/.\"'\s])")
    for f in SLASH_FILES:
        if f.exists():
            text = f.read_text(encoding="utf-8")
            new_text = slash.sub(new_slash, text)
            if new_text != text:
                f.write_text(new_text, encoding="utf-8")
                changed.append(f)
    return changed


def remove_empty_dirs(start: Path) -> None:
    """
    Risalendo verso src/, toglie le cartelle rimaste vuote e i package rimasti
    con il solo `__init__.py` VUOTO. Un `__init__.py` con del codice non si tocca.
    """
    d = start
    while d != SRC and d.exists():
        leftovers = [c for c in d.iterdir() if c.name != "__pycache__"]
        if leftovers == [d / "__init__.py"] and not (d / "__init__.py").read_text(encoding="utf-8").strip():
            git("rm", "-q", str((d / "__init__.py").relative_to(REPO)))
            leftovers = []
        if leftovers:
            break
        shutil.rmtree(d, ignore_errors=True)
        d = d.parent


def warn_fragile(paths: list[Path]) -> None:
    for p in paths:
        text = p.read_text(encoding="utf-8")
        if "__file__" in text or ".parents[" in text:
            print(f"ATTENZIONE: {p.relative_to(REPO)} usa __file__/parents[]: "
                  f"controlla i percorsi calcolati, ora che il file è a un altro livello.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--init-only", action="store_true")
    args = ap.parse_args()
    old, new = args.old.strip("."), args.new.strip(".")

    src_path = to_path(old)
    is_pkg = src_path.is_dir() and (src_path / "__init__.py").exists()
    is_mod = src_path.with_suffix(".py").is_file()
    if not (is_pkg or is_mod):
        die(f"{old}: né modulo né package in {SRC.relative_to(REPO)}")
    if args.init_only and not is_pkg:
        die("--init-only vale solo per un package")

    dst = to_path(new)
    if dst.is_dir() and not [c for c in dst.rglob("*") if c.is_file() and "__pycache__" not in c.parts]:
        shutil.rmtree(dst)  # resti di __pycache__ di una prova precedente: git mv ci finirebbe DENTRO
    if dst.exists() or dst.with_suffix(".py").exists():
        die(f"{new}: la destinazione esiste già")

    check_parent_imports(old)

    if args.init_only:
        subs = [c for c in src_path.iterdir() if c.name not in ("__init__.py", "__pycache__")]
        if subs:
            die(f"{old} contiene ancora {[c.name for c in subs]}: spostali prima")
        ensure_packages(dst.parent)
        git("mv", str((src_path / "__init__.py").relative_to(REPO)),
            str(dst.with_suffix(".py").relative_to(REPO)))
        moved = [dst.with_suffix(".py")]
        remove_empty_dirs(src_path)
    elif is_pkg:
        ensure_packages(dst.parent)
        git("mv", str(src_path.relative_to(REPO)), str(dst.relative_to(REPO)))
        moved = [p for p in dst.rglob("*.py") if "__pycache__" not in p.parts]
        remove_empty_dirs(src_path.parent)
    else:
        ensure_packages(dst.parent)
        git("mv", str(src_path.with_suffix(".py").relative_to(REPO)),
            str(dst.with_suffix(".py").relative_to(REPO)))
        moved = [dst.with_suffix(".py")]
        remove_empty_dirs(src_path.parent)

    changed = rewrite(old, new, exact=args.init_only)
    print(f"Spostato {old} → {new}; riscritti {len(changed)} file.")
    warn_fragile(moved)


if __name__ == "__main__":
    main()
