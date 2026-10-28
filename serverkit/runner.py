"""Eksekusi perintah dengan aman: tanpa shell, argumen berupa list, mendukung dry-run."""
import os
import re
import shlex
import subprocess
from dataclasses import dataclass

from .logger import get_logger

log = get_logger()
PKG_RE = re.compile(r"^[a-z0-9][a-z0-9+.\-]{1,100}$")


class CommandError(RuntimeError):
    pass


def validate_package(name: str) -> str:
    if not PKG_RE.match(name):
        raise ValueError(f"Nama paket tidak valid: {name!r}")
    return name


@dataclass
class Result:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    dry: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class Runner:
    def __init__(self, dry_run: bool = False, console=None):
        self.dry_run = dry_run
        self.console = console

    def run(self, cmd, *, mutating=True, check=True, env_extra=None, timeout=1800) -> Result:
        if not isinstance(cmd, (list, tuple)) or not all(isinstance(c, str) and "\x00" not in c for c in cmd):
            raise TypeError("Perintah harus berupa list string (tanpa shell).")
        printable = shlex.join(cmd)
        if self.dry_run and mutating:
            log.info("DRY-RUN %s", printable)
            if self.console:
                self.console.print(f"[yellow][dry-run][/yellow] {printable}")
            return Result(0, dry=True)
        env = os.environ.copy()
        env.update(env_extra or {})
        log.info("RUN %s", printable)
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
        except FileNotFoundError:
            res = Result(127, "", f"perintah tidak ditemukan: {cmd[0]}")
        except subprocess.TimeoutExpired:
            res = Result(124, "", f"timeout: {printable}")
        else:
            res = Result(p.returncode, p.stdout, p.stderr)
        if res.returncode != 0:
            log.error("GAGAL (%s) %s: %s", res.returncode, printable, res.stderr.strip()[:500])
            if check:
                raise CommandError(f"{printable}\n{res.stderr.strip()[:500]}")
        return res
