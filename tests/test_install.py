"""install.sh: Syntax und die Standard-Pakete (Browser, Piper, Rust) samt --update/--minimal."""
import shutil
import subprocess
from pathlib import Path

import pytest

SH = Path(__file__).resolve().parent.parent / "install.sh"


@pytest.mark.skipif(not shutil.which("bash"), reason="bash fehlt")
def test_install_sh_syntax():
    r = subprocess.run(["bash", "-n", str(SH)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_install_sh_standard_und_update():
    s = SH.read_text(encoding="utf-8")
    assert 'has --minimal || OPT="$OPT --browser --piper --rust --node "' in s
    assert "git pull --ff-only" in s and "--nach-pull" in s
    assert "rustup\" update stable" in s and "--profile minimal" in s
    for svc in ("hyperstead", "paperclip-lite"):
        assert svc in s
    # apt darf eingefuegte Terminal-Zeilen nicht verschlucken
    for line in s.splitlines():
        if "apt-get install" in line and not line.lstrip().startswith("#"):
            assert "</dev/null" in line, line
