"""Dateiansicht: mehrere Dateien auf einmal loeschen und einen Ordner leeren (Wunsch ABI 2026-11-06)."""
from conftest import A, client, make_project  # noqa: F401


def files(pid, *rels):
    root = A.proj_dir(pid)
    for r in rels:
        (root / r).parent.mkdir(parents=True, exist_ok=True)
        (root / r).write_text("x")
    return root


def test_mehrere_dateien_loeschen(client):
    pid = make_project()
    root = files(pid, "input/a.txt", "input/zip/sub/b.txt", "output/c.png", "output/d.png", ".rust/geheim.txt")
    r = client.post(f"/api/projects/{pid}/files/delete",
                    json={"paths": ["input/a.txt", "input/zip/sub/b.txt", "output/c.png", "../../etc/passwd", ".rust/geheim.txt"]})
    assert r.status_code == 200 and r.json["deleted"] == 3
    assert set(r.json["skipped"]) == {"../../etc/passwd", ".rust/geheim.txt"}
    assert not (root / "input" / "a.txt").exists() and (root / "output" / "d.png").exists()
    assert not (root / "input" / "zip").exists() and (root / "input").is_dir()  # leere Unterordner weg, input/ bleibt
    assert (root / ".rust" / "geheim.txt").exists()
    listed = [f["path"] for f in client.get(f"/api/projects/{pid}/files").json["files"]]
    assert "output/d.png" in listed and "input/a.txt" not in listed and "output/c.png" not in listed


def test_mehrere_loeschen_ohne_auswahl(client):
    pid = make_project()
    assert client.post(f"/api/projects/{pid}/files/delete", json={"paths": []}).status_code == 400


def test_ordner_leeren_braucht_bestaetigung(client):
    pid = make_project()
    root = files(pid, "input/a.txt", "input/x/b.txt", "input/.versteckt", "output/c.txt")
    assert client.post(f"/api/projects/{pid}/files/clear", json={"folder": "input"}).status_code == 400
    assert (root / "input" / "a.txt").exists()
    r = client.post(f"/api/projects/{pid}/files/clear", json={"folder": "input", "confirm": True})
    assert r.status_code == 200 and r.json["deleted"] == 2
    assert (root / "input").is_dir() and not (root / "input" / "x").exists()
    assert (root / "input" / ".versteckt").exists() and (root / "output" / "c.txt").exists()


def test_ordner_leeren_nur_erste_ebene_im_projekt(client):
    pid = make_project()
    files(pid, "input/a.txt")
    for bad in ["", "..", "../..", "input/x", ".rust", "gibtsnicht"]:
        r = client.post(f"/api/projects/{pid}/files/clear", json={"folder": bad, "confirm": True})
        assert r.status_code == 400, bad
