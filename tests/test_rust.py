"""Rust-Projekte bauen, testen und als Paket abliefern (Werkzeug rust_project)."""
import io
import json
import shutil
import zipfile

import pytest

import agent_tools as T
import app as A
import rust_builder as R
from conftest import drain, make_agent, make_project, make_task, task

needs_cargo = pytest.mark.skipif(not R.cargo_enabled(), reason="cargo oder bubblewrap fehlt")

TOML = '[package]\nname = "rechner"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\n'
MAIN = ('fn add(a: i32, b: i32) -> i32 { a + b }\n'
        'fn main() { let mut s = String::new(); std::io::stdin().read_line(&mut s).ok();\n'
        '  println!("{} {}", add(2, 3), s.trim()); }\n'
        '#[cfg(test)]\nmod tests { use super::*; #[test] fn plus() { assert_eq!(add(2, 3), 5); }\n'
        '  #[test] fn kein_netz() { assert!(std::net::TcpStream::connect("1.1.1.1:53").is_err()); } }\n')


def crate(root, main=MAIN, name="rechner"):
    d = root / "rust" / name
    (d / "src").mkdir(parents=True, exist_ok=True)
    (d / "Cargo.toml").write_text(TOML.replace("rechner", name))
    (d / "src" / "main.rs").write_text(main)
    return d


@needs_cargo
def test_paket_mit_tests(tmp_path):
    crate(tmp_path)
    out = R.rust_project(tmp_path, {"op": "package", "dir": "rust/rechner"})
    assert "2 passed" in out and "PACKAGE DONE: output/rechner.zip" in out
    names = zipfile.ZipFile(tmp_path / "output" / "rechner.zip").namelist()
    assert {"rechner/README.txt", "rechner/TEST_REPORT.txt", "rechner/source/Cargo.toml",
            "rechner/source/src/main.rs", "rechner/source/Cargo.lock"} <= set(names)
    assert any(n.startswith("rechner/program/rechner") for n in names)
    assert (tmp_path / "rust" / "rechner" / "Cargo.lock").is_file()  # feste Versionen zurueck ins Projekt


@needs_cargo
def test_kein_paket_bei_fehlern(tmp_path):
    crate(tmp_path, main="fn main() { let x: i32 = \"text\"; }\n")
    out = R.rust_project(tmp_path, {"op": "package", "dir": "rust/rechner"})
    assert "ERROR" in out and "mismatched types" in out and "src/main.rs" in out
    assert "NO PACKAGE" in out and not (tmp_path / "output" / "rechner.zip").exists()


@needs_cargo
def test_run_mit_stdin_und_warnung_ohne_tests(tmp_path):
    crate(tmp_path, main=MAIN.split("#[cfg(test)]")[0])
    out = R.rust_project(tmp_path, {"op": "run", "dir": "rust/rechner", "stdin": "hallo\n"})
    assert "5 hallo" in out
    assert "WARNING: There are no tests" in R.rust_project(tmp_path, {"op": "test", "dir": "rust/rechner"})


@needs_cargo
def test_fremde_konfiguration_wird_nicht_kopiert(tmp_path):
    d = crate(tmp_path)
    (d / ".cargo").mkdir()
    (d / ".cargo" / "config.toml").write_text("[build]\nrustflags = [\"--kaputt\"]\n")
    (d / "rust-toolchain.toml").write_text('[toolchain]\nchannel = "1.0.0"\n')
    assert "OK" in R.rust_project(tmp_path, {"op": "build", "dir": "rust/rechner"})


def test_eingaben_werden_geprueft(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "sandbox_mode", lambda: "bwrap")
    (tmp_path / "leer").mkdir()
    with pytest.raises(T.ToolError, match="Cargo.toml"):
        R.rust_project(tmp_path, {"op": "test", "dir": "leer"})
    with pytest.raises(T.ToolError, match="outside"):
        R.rust_project(tmp_path, {"op": "test", "dir": "../.."})
    with pytest.raises(T.ToolError, match="op:"):
        R.rust_project(tmp_path, {"op": "loeschen", "dir": "leer"})


def test_ohne_sandbox_nur_mit_schalter(monkeypatch):
    monkeypatch.setattr(R, "cargo_path", lambda: "/usr/bin/cargo")
    monkeypatch.setattr(R.shutil, "which", lambda n: None)  # kein bubblewrap (wie unter Windows)
    monkeypatch.delenv("PCL_CARGO_UNSAFE", raising=False)
    assert R.sandbox_mode() == ""
    monkeypatch.setenv("PCL_CARGO_UNSAFE", "1")
    assert R.sandbox_mode() == "unsafe"
    monkeypatch.setenv("PCL_CARGO", "0")
    assert R.sandbox_mode() == ""


def test_nur_mit_recht_code_ausfuehren(monkeypatch):
    monkeypatch.setattr(R, "sandbox_mode", lambda: "bwrap")
    assert "rust_project" not in T.available(dict(A.DEFAULT_PERMS))
    assert "rust_project" in T.available(dict(A.DEFAULT_PERMS, run_code=True))
    monkeypatch.setattr(R, "sandbox_mode", lambda: "")
    assert "rust_project" not in T.available(dict(A.DEFAULT_PERMS, run_code=True))


@needs_cargo
def test_agent_liefert_fertiges_paket(monkeypatch):
    pid = make_project()
    a = make_agent(pid, "Rust-Entwickler", run_code=True, code=True, write_files=True)
    replies = iter([
        {"tools": [{"tool": "write_code", "path": "rust/rechner/Cargo.toml", "content": TOML},
                   {"tool": "write_code", "path": "rust/rechner/src/main.rs", "content": MAIN},
                   {"tool": "rust_project", "op": "package", "dir": "rust/rechner"}]},
        {"result": "Fertig: output/rechner.zip"}])
    seen = []

    def fake(agent, messages):
        seen.append(messages[-1]["content"])
        return json.dumps(next(replies)), 10
    monkeypatch.setattr(A, "mock_llm", fake)
    tid = make_task(pid, a)
    drain()
    assert task(tid)["status"] == "done"
    assert "PACKAGE DONE" in seen[-1]
    assert (A.proj_dir(pid) / "output" / "rechner.zip").is_file()
    shutil.rmtree(A.proj_dir(pid) / ".rust", ignore_errors=True)


def test_projekt_zip_ohne_versteckte_ordner():
    pid = make_project()
    root = A.proj_dir(pid)
    (root / ".rust" / "cargo-home").mkdir(parents=True)
    (root / ".rust" / "cargo-home" / "gross.bin").write_bytes(b"x" * 10)
    (root / "output").mkdir(exist_ok=True)
    (root / "output" / "a.txt").write_text("a")
    r = A.app.test_client().get(f"/files/{pid}/{A.file_token(pid)}/_projekt.zip")
    names = zipfile.ZipFile(io.BytesIO(r.data)).namelist()
    assert "output/a.txt" in names and not any(n.startswith(".rust") for n in names)
