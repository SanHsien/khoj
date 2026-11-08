"""Helpers for running the embedded Postgres (pgserver) that `USE_EMBEDDED_DB=true` starts.

Stdlib only, so the Django settings module can import it before anything else is configured.
"""

import shutil
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse


def connection_from_uri(uri: str, data_dir: str) -> Tuple[str, str]:
    """Host and port Django should use for a pgserver URI.

    pgserver on Windows has no Unix sockets and listens on 127.0.0.1 and a random TCP port.
    Elsewhere its URI has no host or port and Postgres listens on a Unix socket in `data_dir`.
    """
    parsed = urlparse(uri)
    return parsed.hostname or data_dir, str(parsed.port) if parsed.port else ""


def ensure_timezone_data(pgserver_dir: Path, tzdata_dir: Optional[Path] = None) -> bool:
    """Give the pgserver Postgres a timezone database if its wheel shipped without one.

    The pgserver 0.1.4 Windows wheel has no `share/postgresql/timezone`. Postgres then rejects
    `SET TIME ZONE 'UTC'`, which Django runs on every connection, and the server never starts.
    The `tzdata` package (a Khoj dependency) holds the same compiled zone files, so copy them in.
    Returns True if it copied them, False if the install already had a timezone database.
    """
    target = pgserver_dir / "pginstall" / "share" / "postgresql" / "timezone"
    if target.is_dir():
        return False
    if tzdata_dir is None:
        import tzdata

        tzdata_dir = Path(tzdata.__file__).parent / "zoneinfo"
    shutil.copytree(tzdata_dir, target)
    return True
