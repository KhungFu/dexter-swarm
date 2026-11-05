"""ElevenLabs als Stimmen-Anbieter bei Bedarf: Wahl je Aufruf/Figur, Ersatzstimme, Stimmenliste (alles simuliert, kein Key, kein Netz)."""
from pathlib import Path

import pytest

import agent_tools as T
import film_studio as F
from agent_tools import ToolError
from test_video_providers import Fake, Resp


@pytest.fixture
def proj(tmp_path, monkeypatch):
    for k in ("TTS_ENGINE", "TTS_FALLBACK", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE", "ELEVENLABS_TTS_MODEL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(T, "_probe", lambda p: {"duration": 1.0})
    return tmp_path


@pytest.fixture
def local_voice(monkeypatch):
    """Simuliertes espeak-ng: merkt sich die Aufrufe und schreibt eine Datei."""
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        Path(cmd[cmd.index("-w") + 1]).write_bytes(b"RIFF")
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    real_which = T.shutil.which
    monkeypatch.setattr(T, "_piper", lambda: (None, None))
    monkeypatch.setattr(T.shutil, "which", lambda n: "/usr/bin/espeak-ng" if n == "espeak-ng" else real_which(n))
    monkeypatch.setattr(T.subprocess, "run", run)
    monkeypatch.setattr(T, "_ff", lambda args, root, timeout=None: Path(args[-1]).write_bytes(b"ID3local"))
    return calls


def test_ohne_key_wie_bisher(proj, local_voice, monkeypatch):
    f = Fake(monkeypatch, {})
    out = T.speak(proj, "Hallo")
    assert out.startswith("Speech created") and local_voice and not f.calls
    assert "ELEVENLABS IS SET UP" not in T.describe(["speak", "film"])


def test_elevenlabs_nur_fuer_diesen_aufruf(proj, local_voice, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "xi")
    f = Fake(monkeypatch, {("POST", "/text-to-speech/"): Resp(content=b"ID3eleven")})
    out, made = T.run_tool({"tool": "speak", "text": "Willkommen", "engine": "elevenlabs", "voice": "21m00Tcm4TlvDq8ikWAM",
                            "name": "werbung"}, proj, {"media": True})
    assert "with ElevenLabs" in out and made == "output/audio/werbung.mp3"
    assert (proj / made).read_bytes() == b"ID3eleven" and not local_voice
    call = f.find("POST", "text-to-speech/21m00Tcm4TlvDq8ikWAM")[0]
    assert call[2]["headers"]["xi-api-key"] == "xi" and call[2]["json"]["text"] == "Willkommen"
    T.speak(proj, "Entwurf")  # ohne engine bleibt es lokal
    assert local_voice and len(f.calls) == 1
    assert "ELEVENLABS IS SET UP" in T.describe(["speak"])
    T.speak(proj, "Beste", engine="beste")  # Kurzform
    assert len(f.find("POST", "text-to-speech/JBFqnCBsd6RMkjVDRZzb")) == 1


def test_ersatzstimme_bei_fehler(proj, local_voice, monkeypatch):
    monkeypatch.setenv("TTS_ENGINE", "elevenlabs")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "xi")
    Fake(monkeypatch, {("POST", "/text-to-speech/"): Resp({"detail": "quota_exceeded"}, status=401)})
    out = T.speak(proj, "Hallo", voice="21m00Tcm4TlvDq8ikWAM", target=proj / "film/ton/a.mp3")
    assert out.startswith("NOTE: ElevenLabs not used") and "HTTP 401" in out
    assert (proj / "film/ton/a.mp3").read_bytes() == b"ID3local"
    assert local_voice[0][2] == "de"  # Stimmen-ID nicht an espeak weitergegeben
    monkeypatch.delenv("ELEVENLABS_API_KEY")
    assert "ELEVENLABS_API_KEY is missing" in T.speak(proj, "Hallo")
    monkeypatch.setenv("TTS_FALLBACK", "0")
    with pytest.raises(ToolError, match="ELEVENLABS_API_KEY is missing"):
        T.speak(proj, "Hallo")


def test_engine_unbekannt(proj):
    with pytest.raises(ToolError, match="engine 'xyz' unknown"):
        T.speak(proj, "Hallo", engine="xyz")


def test_stimmenliste(proj, monkeypatch):
    out, _ = T.run_tool({"tool": "speak", "list_voices": True}, proj, {"media": True})
    assert "not set up" in out
    monkeypatch.setenv("ELEVENLABS_API_KEY", "xi")
    Fake(monkeypatch, {("GET", "/v1/voices"): Resp({"voices": [
        {"voice_id": "abcdefghijklmnop1234", "name": "Rachel", "labels": {"gender": "female", "age": "young"}}]})})
    out, _ = T.run_tool({"tool": "speak", "list_voices": True}, proj, {"media": True})
    assert "Rachel: abcdefghijklmnop1234 (female, young)" in out


def test_film_figur_mit_elevenlabs(proj, local_voice, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "xi")
    f = Fake(monkeypatch, {("POST", "/text-to-speech/"): [Resp(status=500), Resp(content=b"ID3eleven")]})
    data = {"figuren": {"Bello": {"art": "hund", "stimme": {"engine": "elevenlabs", "voice": "21m00Tcm4TlvDq8ikWAM"}},
                        "Mimi": {"art": "katze"}},
            "szenen": [{"id": "s01", "figuren": {"Bello": {"pos": [-2, 0]}, "Mimi": {"pos": [2, 0]}},
                        "dialog": [{"figur": "Bello", "text": "Hallo!"}, {"figur": "Mimi", "text": "Miau"}], "dauer": 2}]}
    plan = F.normalize(proj, data)
    assert plan["figuren"]["Bello"]["stimme"]["engine"] == "elevenlabs" and plan["figuren"]["Mimi"]["stimme"]["engine"] == ""
    out = F.op_voices(proj, plan, {})
    assert "1 lines with a local substitute voice" in out and len(local_voice) == 2
    out = F.op_voices(proj, plan, {})  # zweiter Versuch vertont nur die Ersatzzeile neu, jetzt mit ElevenLabs
    assert "2 neu" not in out and "Ersatzstimme" not in out and len(f.calls) == 2
    assert (proj / "film/ton/s01_01.mp3").read_bytes() == b"ID3eleven"
    with pytest.raises(ToolError, match="engine 'quatsch' unknown"):
        F.normalize(proj, dict(data, figuren={"Bello": {"art": "hund", "stimme": {"engine": "quatsch"}}}))
