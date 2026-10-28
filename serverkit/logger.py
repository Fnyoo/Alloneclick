import logging
import os
from pathlib import Path

_logger = None


def data_dir() -> Path:
    env = os.environ.get("SERVERKIT_HOME")
    if env:
        base = Path(env)
    elif os.geteuid() == 0:
        base = Path("/var/lib/serverkit")
    else:
        base = Path.home() / ".local" / "share" / "serverkit"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_logger() -> logging.Logger:
    global _logger
    if _logger:
        return _logger
    logger = logging.getLogger("serverkit")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        try:
            handler = logging.FileHandler(data_dir() / "serverkit.log")
        except OSError:
            handler = logging.NullHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    _logger = logger
    return logger
