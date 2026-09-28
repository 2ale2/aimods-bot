#!/usr/bin/env python3
"""
Sposta funzioni/classi/costanti di primo livello da un modulo a un altro e
riscrive gli import di chi le usa.

    python tools/move_symbols.py infra.telegram.utils ui.helpers create_and_render_panel chunk_buttons

I moduli sono puntati e relativi ad `aimods_bot.src`.

Cosa fa:
  1. toglie le definizioni dal modulo vecchio (decoratori compresi) e le aggiunge
     in fondo al nuovo, che viene creato se non esiste;
  2. nel modulo nuovo copia gli import del vecchio e poi toglie quelli inutili
     (chiedendo a pyflakes); nel vecchio toglie quelli rimasti inutili;
  3. in tutti i .py di src/ e tests/, ogni `from <vecchio> import a, b, x`
     diventa `from <vecchio> import a, b` + `from <nuovo> import x`.

Si ferma prima di scrivere se:
  - un nome non è una definizione di primo livello del modulo vecchio;
  - qualcuno usa il modulo vecchio come oggetto (`import ... as m` + `m.x`):
    quegli usi vanno sistemati a mano;
  - il modulo vecchio usa ancora internamente un nome spostato (servirebbe un
    import all'indietro, probabile ciclo).

Gli import riscritti perdono l'eventuale a-capo originale: vengono rigenerati su
una riga, spezzata con `\\` se supera 120 caratteri. NON fa commit.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "aimods_bot" / "src"
PREFIX = "aimods_bot.src"
CODE_DIRS = [SRC, REPO / "aimods_bot" / "tests"]


def die(msg: str) -> None:
    print(f"ERRORE: {msg}", file=sys.stderr)
    sys.exit(1)


def path_of(dotted: str) -> Path:
    return SRC.joinpath(*dotted.split(".")).with_suffix(".py")


def py_files() -> list[Path]:
    return [p for d in CODE_DIRS for p in d.rglob("*.py") if "__pycache__" not in p.parts]


def top_level_blocks(source: str, names: set[str]) -> dict[str, tuple[int, int]]:
    """nome → (riga iniziale 0-based, riga finale esclusa), decoratori compresi."""
    found = {}
    for node in ast.parse(source).body:
        defined = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined = [node.name]
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            defined = [t.id for t in targets if isinstance(t, ast.Name)]
        for name in defined:
            if name in names:
                start = min([d.lineno for d in getattr(node, "decorator_list", [])] + [node.lineno]) - 1
                found[name] = (start, node.end_lineno)
    return found


def import_block(source: str) -> str:
    """Tutti gli import di primo livello del modulo, testo originale."""
    lines = source.splitlines(keepends=True)
    out = []
    for node in ast.parse(source).body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            out.append("".join(lines[node.lineno - 1:node.end_lineno]))
    return "".join(out)


def format_from(module: str, names: list[str]) -> str:
    line = f"from {module} import {', '.join(names)}"
    if len(line) <= 120:
        return line + "\n"
    head, parts, rows, cur = f"from {module} import ", names, [], ""
    for n in parts:
        piece = n if not cur else f", {n}"
        if len(head) + len(cur) + len(piece) > 115 and cur:
            rows.append(cur + ",")
            cur = n
        else:
            cur += piece
    rows.append(cur)
    return head + " \\\n    ".join(rows) + "\n"


def alias_str(a: ast.alias) -> str:
    return f"{a.name} as {a.asname}" if a.asname else a.name


def pyflakes_unused(path: Path) -> set[tuple[int, str]]:
    r = subprocess.run([sys.executable, "-m", "pyflakes", str(path)], capture_output=True, text=True)
    out = set()
    for line in r.stdout.splitlines():
        m = re.match(rf"{re.escape(str(path))}:(\d+):\d+:? '([^']+)' imported but unused", line)
        if m:
            out.add((int(m.group(1)), m.group(2)))
    return out


def prune_unused_imports(path: Path) -> None:
    unused = pyflakes_unused(path)
    if not unused:
        return
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    edits = []
    for node in ast.parse(source).body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        dead = {name for ln, name in unused if ln == node.lineno}
        if not dead:
            continue

        def spellings(a: ast.alias) -> set[str]:
            # pyflakes scrive `mod.nome`, `mod.nome as alias` o solo `mod` a seconda della forma
            base = f"{node.module}.{a.name}" if isinstance(node, ast.ImportFrom) else a.name
            out = {base, a.asname or a.name}
            if a.asname:
                out.add(f"{base} as {a.asname}")
            return out

        keep = [a for a in node.names if not (spellings(a) & dead)]
        if isinstance(node, ast.ImportFrom):
            new = format_from("." * node.level + (node.module or ""), [alias_str(a) for a in keep]) if keep else ""
        else:
            new = "".join(f"import {alias_str(a)}\n" for a in keep)
        edits.append((node.lineno - 1, node.end_lineno, new))
    for start, end, new in sorted(edits, reverse=True):
        lines[start:end] = [new] if new else []
    path.write_text("".join(lines), encoding="utf-8")


def pyflakes_undefined(path: Path) -> set[str]:
    r = subprocess.run([sys.executable, "-m", "pyflakes", str(path)], capture_output=True, text=True)
    return set(re.findall(r"undefined name '(\w+)'", r.stdout))


def main() -> None:
    if len(sys.argv) < 4:
        die("uso: move_symbols.py VECCHIO NUOVO nome [nome ...]")
    old, new, names = sys.argv[1], sys.argv[2], sys.argv[3:]
    old_full, new_full = f"{PREFIX}.{old}", f"{PREFIX}.{new}"
    old_path, new_path = path_of(old), path_of(new)
    if not old_path.exists():
        die(f"{old_path} non esiste")

    old_src = old_path.read_text(encoding="utf-8")
    blocks = top_level_blocks(old_src, set(names))
    missing = set(names) - blocks.keys()
    if missing:
        die(f"non sono definizioni di primo livello in {old}: {sorted(missing)}")

    # usi come oggetto modulo: `import aimods_bot.src.old as m` / `from pkg import old`
    alias_pat = re.compile(rf"^\s*import\s+{re.escape(old_full)}\s+as\s+(\w+)", re.M)
    parent, _, leaf = old_full.rpartition(".")
    from_pkg_pat = re.compile(rf"^\s*from\s+{re.escape(parent)}\s+import\s+[^\n]*\b{re.escape(leaf)}\b", re.M)
    offenders = []
    for p in py_files():
        text = p.read_text(encoding="utf-8")
        for m in alias_pat.finditer(text):
            if re.search(rf"\b{m.group(1)}\.({'|'.join(map(re.escape, names))})\b", text):
                offenders.append(str(p.relative_to(REPO)))
        if from_pkg_pat.search(text):
            offenders.append(str(p.relative_to(REPO)))
    if offenders:
        die("il modulo vecchio è usato come oggetto in:\n  " + "\n  ".join(sorted(set(offenders))))

    lines = old_src.splitlines(keepends=True)
    moved_code = "\n\n".join("".join(lines[s:e]).rstrip() + "\n" for s, e in
                             sorted(blocks.values()))
    for s, e in sorted(blocks.values(), reverse=True):
        del lines[s:e]
    remaining = re.sub(r"\n{4,}", "\n\n\n", "".join(lines))

    # il vecchio usa ancora qualcosa che se ne va?
    still_used = [n for n in names if re.search(rf"\b{re.escape(n)}\b", remaining)]
    if still_used:
        die(f"{old} usa ancora internamente {still_used}: sposta anche chi li usa, o lasciali dove sono")

    # 1-2. scrivi i due moduli
    if new_path.exists():
        new_src = new_path.read_text(encoding="utf-8").rstrip() + "\n\n\n" + moved_code
        head = import_block(old_src)
        new_src = head + new_src  # import in cima: i doppioni li toglie pyflakes sotto
    else:
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_src = import_block(old_src) + "\n" + (
            "log = logger.getChild(__name__)\n\n\n"
            if "log = logger.getChild(__name__)" in old_src and re.search(r"\blog\.", moved_code) else "\n"
        ) + moved_code
    old_path.write_text(remaining, encoding="utf-8")
    new_path.write_text(new_src, encoding="utf-8")
    # il codice spostato può usare definizioni rimaste nel vecchio modulo:
    # le importa dal vecchio (direzione nuovo → vecchio, quella già prevista)
    old_defs = set(top_level_blocks(remaining, pyflakes_undefined(new_path)))
    if old_defs:
        text = new_path.read_text(encoding="utf-8")
        head_end = max((n.end_lineno for n in ast.parse(text).body
                        if isinstance(n, (ast.Import, ast.ImportFrom))), default=0)
        tl = text.splitlines(keepends=True)
        tl.insert(head_end, format_from(old_full, sorted(old_defs)))
        new_path.write_text("".join(tl), encoding="utf-8")
    left = pyflakes_undefined(new_path)
    if left:
        print(f"ATTENZIONE: in {new} restano nomi non definiti: {sorted(left)}")
    prune_unused_imports(new_path)
    prune_unused_imports(old_path)
    subprocess.run(["git", "add", str(new_path.relative_to(REPO))], cwd=REPO, check=True)

    # 3. riscrivi gli importatori
    moved = set(names)
    changed = 0
    for p in py_files():
        if p in (old_path,):
            continue
        source = p.read_text(encoding="utf-8")
        if old_full not in source:
            continue
        src_lines = source.splitlines(keepends=True)
        edits = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom) and node.module == old_full and node.level == 0:
                go = [a for a in node.names if a.name in moved]
                if not go:
                    continue
                stay = [a for a in node.names if a.name not in moved]
                indent = re.match(r"\s*", src_lines[node.lineno - 1]).group(0)
                text = ""
                if stay:
                    text += indent + format_from(old_full, [alias_str(a) for a in stay])
                if p != new_path:
                    text += indent + format_from(new_full, [alias_str(a) for a in go])
                edits.append((node.lineno - 1, node.end_lineno, text))
        if edits:
            for s, e, t in sorted(edits, reverse=True):
                src_lines[s:e] = [t]
            p.write_text("".join(src_lines), encoding="utf-8")
            changed += 1
    print(f"Spostati {len(names)} nomi da {old} a {new}; riscritti gli import in {changed} file.")


if __name__ == "__main__":
    main()
