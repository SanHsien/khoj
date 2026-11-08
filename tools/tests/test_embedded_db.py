"""What the embedded Postgres setup must do for `USE_EMBEDDED_DB=true` to start a server.

Two defects of the pgserver 0.1.4 Windows wheel made the Khoj server exit at startup, and
only a real server start shows them (see docs/DECISIONS.md, 2026-11-08):

* it listens on a TCP port, but settings pointed Django at a Unix socket path;
* its install has no timezone database, so `SET TIME ZONE 'UTC'` fails on every connection.

`khoj.utils.embedded_db` is stdlib only, so these tests need nothing but `requirements-dev.txt`.
"""

from __future__ import annotations

import importlib.util
import runpy
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "src" / "khoj" / "utils" / "embedded_db.py"

spec = importlib.util.spec_from_file_location("embedded_db_under_test", MODULE_PATH)
assert spec is not None and spec.loader is not None
embedded_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(embedded_db)


def _install_without_timezone(tmp_path: Path) -> Path:
    pgserver_dir = tmp_path / "pgserver"
    (pgserver_dir / "pginstall" / "share" / "postgresql" / "timezonesets").mkdir(parents=True)
    return pgserver_dir


def _fake_tzdata(tmp_path: Path) -> Path:
    zoneinfo = tmp_path / "tzdata" / "zoneinfo"
    (zoneinfo / "Asia").mkdir(parents=True)
    (zoneinfo / "UTC").write_bytes(b"TZif-utc")
    (zoneinfo / "Asia" / "Taipei").write_bytes(b"TZif-taipei")
    return zoneinfo


def test_tcp_uri_gives_django_the_host_and_port_pgserver_listens_on():
    host, port = embedded_db.connection_from_uri("postgresql://postgres:@127.0.0.1:64985/postgres", "C:/data")
    assert (host, port) == ("127.0.0.1", "64985")


def test_unix_socket_uri_keeps_the_data_directory_as_host_and_no_port():
    host, port = embedded_db.connection_from_uri("postgresql://postgres:@/postgres?host=/srv/data", "/srv/data")
    assert (host, port) == ("/srv/data", "")


def test_install_without_timezone_database_gets_the_tzdata_zone_files(tmp_path):
    pgserver_dir = _install_without_timezone(tmp_path)

    copied = embedded_db.ensure_timezone_data(pgserver_dir, _fake_tzdata(tmp_path))

    timezone_dir = pgserver_dir / "pginstall" / "share" / "postgresql" / "timezone"
    assert copied is True
    assert (timezone_dir / "UTC").read_bytes() == b"TZif-utc"
    assert (timezone_dir / "Asia" / "Taipei").read_bytes() == b"TZif-taipei"


def test_install_that_already_has_a_timezone_database_is_left_alone(tmp_path):
    pgserver_dir = _install_without_timezone(tmp_path)
    timezone_dir = pgserver_dir / "pginstall" / "share" / "postgresql" / "timezone"
    timezone_dir.mkdir()
    (timezone_dir / "UTC").write_bytes(b"TZif-bundled")

    copied = embedded_db.ensure_timezone_data(pgserver_dir, _fake_tzdata(tmp_path))

    assert copied is False
    assert (timezone_dir / "UTC").read_bytes() == b"TZif-bundled"
    assert not (timezone_dir / "Asia").exists()


SETTINGS_PATH = ROOT / "src" / "khoj" / "app" / "settings.py"


def _run_settings(monkeypatch, tmp_path, use_embedded_db: bool):
    """Execute settings.py with fake Django, pgserver and embedded_db modules.

    Returns the settings namespace and the order in which the fakes were called.
    """
    calls: list[tuple] = []

    class FakeServer:
        def psql(self, sql):
            return "(1 row)"

        def get_uri(self):
            return "postgresql://postgres:@127.0.0.1:64985/postgres"

        def cleanup(self):
            pass

    fake_pgserver = types.ModuleType("pgserver")
    fake_pgserver.__file__ = str(tmp_path / "pgserver" / "__init__.py")
    fake_pgserver.get_server = lambda data_dir: calls.append(("get_server", data_dir)) or FakeServer()

    fake_embedded_db = types.ModuleType("khoj.utils.embedded_db")
    fake_embedded_db.ensure_timezone_data = lambda pgserver_dir: calls.append(("ensure_timezone_data", pgserver_dir))
    fake_embedded_db.connection_from_uri = lambda uri, data_dir: calls.append(
        ("connection_from_uri", uri, data_dir)
    ) or (
        "fake-host",
        "5555",
    )

    fake_helpers = types.ModuleType("khoj.utils.helpers")
    fake_helpers.is_env_var_true = lambda name: name == "USE_EMBEDDED_DB" and use_embedded_db

    fake_static = types.ModuleType("django.templatetags.static")
    fake_static.static = lambda path: path

    for name, module in {
        "pgserver": fake_pgserver,
        "khoj": types.ModuleType("khoj"),
        "khoj.utils": types.ModuleType("khoj.utils"),
        "khoj.utils.embedded_db": fake_embedded_db,
        "khoj.utils.helpers": fake_helpers,
        "django": types.ModuleType("django"),
        "django.templatetags": types.ModuleType("django.templatetags"),
        "django.templatetags.static": fake_static,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setenv("PGSERVER_DATA_DIR", str(tmp_path / "pgdata"))

    return runpy.run_path(str(SETTINGS_PATH)), calls


def test_settings_gives_django_the_pgserver_connection_after_fixing_its_timezone_data(monkeypatch, tmp_path):
    settings, calls = _run_settings(monkeypatch, tmp_path, use_embedded_db=True)

    names = [call[0] for call in calls]
    assert names.index("ensure_timezone_data") < names.index("get_server")
    assert ("ensure_timezone_data", tmp_path / "pgserver") in calls
    assert ("connection_from_uri", "postgresql://postgres:@127.0.0.1:64985/postgres", str(tmp_path / "pgdata")) in calls
    assert settings["DATABASES"]["default"]["HOST"] == "fake-host"
    assert settings["DATABASES"]["default"]["PORT"] == "5555"


def test_settings_leave_the_database_alone_without_use_embedded_db(monkeypatch, tmp_path):
    settings, calls = _run_settings(monkeypatch, tmp_path, use_embedded_db=False)

    assert calls == []
    assert settings["DATABASES"]["default"]["HOST"] == "localhost"
