"""selftest.py laesst sich mit dem normalen Python starten und wechselt selbst ins venv."""
import subprocess
import sys
from pathlib import Path

import selftest as S

ROOT = Path(__file__).resolve().parent.parent


def test_venv_python_paths(tmp_path):
    assert S.venv_python(tmp_path, windows=True) is None
    assert S.venv_python(tmp_path, windows=False) is None
    (tmp_path / "venv" / "Scripts").mkdir(parents=True)
    (tmp_path / "venv" / "Scripts" / "python.exe").write_text("")
    (tmp_path / "venv" / "bin").mkdir(parents=True)
    (tmp_path / "venv" / "bin" / "python").write_text("")
    assert S.venv_python(tmp_path, windows=True) == tmp_path / "venv" / "Scripts" / "python.exe"
    assert S.venv_python(tmp_path, windows=False) == tmp_path / "venv" / "bin" / "python"


def test_restarts_with_venv_python(tmp_path, monkeypatch):
    fake = tmp_path / "python.exe"
    fake.write_text("")
    monkeypatch.setattr(S, "in_venv", lambda: False)
    monkeypatch.setattr(S, "venv_python", lambda: fake)
    monkeypatch.delenv("HYPERSTEAD_SELFTEST_REEXEC", raising=False)
    calls = []

    def run(cmd, env):
        calls.append((cmd, env))
        return 7

    assert S.ensure_venv(["llm"], run=run) == 7
    cmd, env = calls[0]
    assert cmd[0] == str(fake) and cmd[1].endswith("selftest.py") and cmd[2:] == ["llm"]
    assert env["HYPERSTEAD_SELFTEST_REEXEC"] == "1"


def test_no_restart_when_in_venv_or_no_venv_or_loop(tmp_path, monkeypatch):
    fake = tmp_path / "python"
    fake.write_text("")
    boom = lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not restart"))  # noqa: E731
    monkeypatch.delenv("HYPERSTEAD_SELFTEST_REEXEC", raising=False)
    monkeypatch.setattr(S, "in_venv", lambda: True)
    monkeypatch.setattr(S, "venv_python", lambda: fake)
    assert S.ensure_venv([], run=boom) is None
    monkeypatch.setattr(S, "in_venv", lambda: False)
    monkeypatch.setattr(S, "venv_python", lambda: None)
    assert S.ensure_venv([], run=boom) is None
    monkeypatch.setattr(S, "venv_python", lambda: fake)
    monkeypatch.setenv("HYPERSTEAD_SELFTEST_REEXEC", "1")
    assert S.ensure_venv([], run=boom) is None


def test_hint_names_installer():
    assert "install.ps1" in S.missing_venv_hint(windows=True)
    assert "python selftest.py" in S.missing_venv_hint(windows=True)
    assert "./install.sh" in S.missing_venv_hint(windows=False)


def test_clear_message_without_requests_and_without_venv(tmp_path):
    # Kopie ohne venv daneben, Python ohne Zugriff auf installierte Pakete (-S -I): requests fehlt.
    (tmp_path / "selftest.py").write_text((ROOT / "selftest.py").read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run([sys.executable, "-S", "-I", str(tmp_path / "selftest.py")], capture_output=True, text=True, timeout=60)
    assert r.returncode == 2
    assert "requests" in r.stdout and ("install.sh" in r.stdout or "install.ps1" in r.stdout)
