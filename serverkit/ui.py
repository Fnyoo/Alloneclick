"""Helper tampilan terminal. Memakai `rich` bila terpasang, fallback ke teks biasa."""
from __future__ import annotations

import sys
from typing import Callable, Optional, Sequence

try:
    from rich import box
    from rich.console import Console
    from rich.table import Table

    _console = Console()
    HAS_RICH = True
except ImportError:  # pragma: no cover
    HAS_RICH = False

_COLOR = sys.stdout.isatty()


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def info(msg: str) -> None:
    print(_c("[i] ", "36") + msg)


def ok(msg: str) -> None:
    print(_c("[✓] ", "32") + msg)


def warn(msg: str) -> None:
    print(_c("[!] ", "33") + msg)


def error(msg: str) -> None:
    print(_c("[✗] ", "31") + msg)


def banner(title: str, width: int = 50) -> None:
    print()
    print("=" * width)
    print(title.center(width))
    print("=" * width)
    print()


def section(title: str, width: int = 50) -> None:
    print()
    print(f" {title} ".center(width, "="))
    print()


def menu(items: Sequence[tuple[str, str]]) -> None:
    for key, label in items:
        print(f"[{key}] {label}")
    print()


def table(title: str, columns: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    if HAS_RICH:
        t = Table(title=title, box=box.HEAVY_HEAD, title_justify="left")
        for col in columns:
            t.add_column(col)
        for row in rows:
            t.add_row(*[str(c) for c in row])
        _console.print(t)
        return
    rows = [[str(c) for c in r] for r in rows]
    widths = [max(len(columns[i]), *(len(r[i]) for r in rows)) if rows else len(columns[i])
              for i in range(len(columns))]
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    print(title)
    print(line)
    print("| " + " | ".join(c.ljust(w) for c, w in zip(columns, widths)) + " |")
    print(line)
    for r in rows:
        print("| " + " | ".join(c.ljust(w) for c, w in zip(r, widths)) + " |")
    print(line)


def ask(prompt: str, default: Optional[str] = None,
        validator: Optional[Callable[[str], str]] = None, width: int = 16,
        allow_empty: bool = False) -> str:
    """Tanya input; ulangi sampai valid. Enter = pakai default."""
    suffix = f" [{default}]" if default else ""
    while True:
        raw = input(f"{prompt:<{width}}{suffix} : ").strip()
        if not raw:
            if default is not None:
                raw = default
            elif allow_empty:
                return ""
            else:
                error("Wajib diisi.")
                continue
        if validator is None:
            return raw
        try:
            return validator(raw)
        except ValueError as exc:
            error(str(exc))


def confirm(prompt: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        raw = input(f"{prompt} {hint} ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "ya", "yes"):
            return True
        if raw in ("n", "no", "t", "tidak"):
            return False


def pause() -> None:
    input("\nTekan Enter untuk kembali ke menu...")
