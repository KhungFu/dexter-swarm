"""ZIP-Uploads: sicher entpacken nach input/<name>/, damit Agenten die Dateien lesen koennen (z. B. Animationsagentur)."""
import io
import zipfile

import agent_tools as T
from conftest import A, client, make_project  # noqa: F401


def zbytes(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


def test_upload_zip_is_unpacked(client):
    pid = make_project()
    data = zbytes({"szenen/01.txt": "Szene eins", "bild.png": b"\x89PNG", "__MACOSX/x": "x", "../boese.txt": "nein"})
    r = client.post(f"/api/projects/{pid}/upload", data={"file": (io.BytesIO(data), "KOZMOS TOTAL komplett.zip")},
                    content_type="multipart/form-data")
    assert r.status_code == 200
    assert r.get_json()["path"] == "input/KOZMOS-TOTAL-komplett.zip"
    root = A.proj_dir(pid)
    d = root / "input" / "KOZMOS-TOTAL-komplett"
    assert (d / "szenen" / "01.txt").read_text() == "Szene eins"
    assert (d / "bild.png").is_file()
    assert not (d / "__MACOSX").exists()
    assert not (root / "input" / "boese.txt").exists() and not (d.parent.parent / "boese.txt").exists()
    out = T.read_file(root, "input/KOZMOS-TOTAL-komplett.zip")
    assert "unpacked to input/KOZMOS-TOTAL-komplett/" in out and "szenen/01.txt" in out


def test_read_file_unpacks_older_zip(tmp_path):
    (tmp_path / "input").mkdir()
    (tmp_path / "input" / "alt.zip").write_bytes(zbytes({"a.md": "hallo"}))
    out = T.read_file(tmp_path, "input/alt.zip")
    assert "unpacked to input/alt/" in out and "a.md" in out
    assert (tmp_path / "input" / "alt" / "a.md").read_text() == "hallo"


def test_zip_size_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("PCL_UNZIP_MAX_MB", "1")
    (tmp_path / "gross.zip").write_bytes(zbytes({"x.bin": b"0" * 2_000_000}))
    out = T.read_file(tmp_path, "gross.zip")
    assert "not unpacked" in out
    assert not (tmp_path / "gross").exists()


def test_broken_zip_upload_still_saved(client):
    pid = make_project()
    r = client.post(f"/api/projects/{pid}/upload", data={"file": (io.BytesIO(b"kein zip"), "kaputt.zip")},
                    content_type="multipart/form-data")
    assert r.status_code == 200
    assert (A.proj_dir(pid) / "input" / "kaputt.zip").is_file()
    assert not (A.proj_dir(pid) / "input" / "kaputt").exists()
