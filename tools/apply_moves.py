#!/usr/bin/env python3
"""
Applica tools/restructure_moves.txt un passo alla volta: sposta, controlla, committa.

    python tools/apply_moves.py                  # tutto, dal primo passo non ancora fatto
    python tools/apply_moves.py --phase 1a       # solo la fase indicata
    python tools/apply_moves.py --dry-run        # mostra cosa farebbe

Dopo OGNI passo:
  - pytest (compreso test_imports.py, che importa ogni modulo di src/)
  - pyflakes su src/ non oltre la linea di base (--baseline, default 7)
  e solo se è tutto verde, un commit "refactor: ...". Al primo errore si ferma
  senza committare: il passo fallito resta nella working tree da guardare.

Riprende da solo: un passo già fatto (vecchio assente, nuovo presente) si salta.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "aimods_bot" / "src"
MOVES = REPO / "tools" / "restructure_moves.txt"
PY = sys.executable
OLD_ROOTS = ("callbacks", "helpers", "handlers", "tasks", "main")


def run(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if check and r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        sys.exit(f"FERMO: fallito `{' '.join(cmd)}`")
    return r


def exists(dotted: str) -> bool:
    p = SRC.joinpath(*dotted.split("."))
    return p.with_suffix(".py").is_file() or (p / "__init__.py").is_file()


def defines(dotted: str, name: str) -> bool:
    p = SRC.joinpath(*dotted.split(".")).with_suffix(".py")
    return p.is_file() and re.search(rf"^(async def|def|class) {re.escape(name)}\b|^{re.escape(name)}\s*[:=]",
                                     p.read_text(encoding="utf-8"), re.M) is not None


def checks(label: str, baseline: int) -> None:
    t = run(PY, "-m", "pytest", "aimods_bot/tests", "-q", "-x", "-p", "no:cacheprovider", check=False)
    if t.returncode:
        print(t.stdout[-4000:])
        sys.exit(f"FERMO: test rossi dopo `{label}` (niente commit)")
    f = run(PY, "-m", "pyflakes", "aimods_bot/src", check=False)
    n = len(f.stdout.strip().splitlines())
    if n > baseline:
        print(f.stdout)
        sys.exit(f"FERMO: pyflakes {n} righe (> {baseline}) dopo `{label}` (niente commit)")
    print(f"  ok  {label:72s} {t.stdout.strip().splitlines()[-1].split(' in ')[0]} · pyflakes {n}")


def commit(msg: str) -> None:
    run("git", "add", "-A", "aimods_bot", "Dockerfile", "docker-compose.yml", "tools")
    if run("git", "diff", "--cached", "--quiet", check=False).returncode:
        run("git", "commit", "-q", "-m", msg)


def manual_paths() -> bool:
    p = SRC / "core" / "paths.py"
    text = p.read_text(encoding="utf-8")
    if "parents[3]" not in text:
        return False
    p.write_text(text.replace("parents[3]", "parents[2]")
                 .replace("# constants/ → helpers/ → src/ → aimods_bot/", "# core/ → src/ → aimods_bot/"),
                 encoding="utf-8")
    run(PY, "-c", "from aimods_bot.src.core.paths import MISC_DIR, MINIAPP_STATIC_DIR; "
                  "assert MISC_DIR.is_dir() and MINIAPP_STATIC_DIR.is_dir(), MISC_DIR")
    return True


def manual_cleanup() -> bool:
    did = False
    for root in OLD_ROOTS:
        d = SRC / root
        if not d.exists():
            continue
        files = [p for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        real = [p for p in files if not (p.name == "__init__.py" and not p.read_text(encoding="utf-8").strip())]
        if real:
            sys.exit(f"FERMO: in {root}/ restano file veri: {[str(p.relative_to(SRC)) for p in real]}")
        run("git", "rm", "-q", "-r", str(d.relative_to(REPO)))
        subprocess.run(["rm", "-rf", str(d)])
        did = True
    return did


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", help="esegue solo la fase indicata (es. 1a, 2b)")
    ap.add_argument("--baseline", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if run("git", "status", "--porcelain", "--", "aimods_bot", "Dockerfile", check=False).stdout.strip():
        sys.exit("FERMO: ci sono modifiche non committate in aimods_bot/ o nel Dockerfile")

    phase = None
    for raw in MOVES.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        m = re.match(r"^## FASE (\w+)", line)
        if m:
            phase = m.group(1)
            continue
        if not line or line.startswith("#"):
            continue
        if args.phase and phase != args.phase:
            continue

        if line.startswith("!"):
            step = line[1:].strip()
            if args.dry_run:
                print(f"  [a mano] {step}")
                continue
            did = manual_paths() if step.startswith("paths") else manual_cleanup() if step.startswith("pulizia") \
                else sys.exit(f"FERMO: passo a mano sconosciuto: {step}")
            if did:
                checks(step, args.baseline)
                commit(f"refactor: {step}")
            continue

        if line.startswith("@symbols"):
            _, old, new, *names = line.split()
            if all(defines(new, n) for n in names) and not any(defines(old, n) for n in names):
                continue
            label = f"{old} → {new}: {', '.join(names)}"
            if args.dry_run:
                print(f"  [simboli] {label}")
                continue
            run(PY, "tools/move_symbols.py", old, new, *names)
            checks(label, args.baseline)
            commit(f"refactor: sposta {', '.join(names)} da {old} a {new}")
            continue

        old, new, *flags = line.split()
        if not exists(old) and exists(new):
            continue
        if args.dry_run:
            print(f"  {old} → {new} {' '.join(flags)}")
            continue
        run(PY, "tools/move_module.py", old, new, *flags)
        checks(f"{old} → {new}", args.baseline)
        commit(f"refactor: sposta {old} in {new}")

    if not args.dry_run:
        layers = run(PY, "tools/check_layers.py", check=False)
        print("\n" + layers.stdout.strip().splitlines()[-1])
    print("fine")


if __name__ == "__main__":
    main()
