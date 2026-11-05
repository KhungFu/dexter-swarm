"""Sprache: Oberflaeche/Prompts Englisch, Kommunikation in der Sprache des Besitzers (note_owner_text, language_line, tr)."""
import app as A
from conftest import make_agent, make_project


class FakeLLM:
    def __init__(self, lang="Turkish"):
        self.lang, self.calls = lang, []

    def __call__(self, agent, messages, images=None):
        self.calls.append(messages)
        if "Which language" in messages[-1]["content"]:
            return self.lang, 1
        return "TR:" + messages[-1]["content"], 1


def setup(monkeypatch, lang="Turkish"):
    pid = make_project()
    make_agent(pid, "CEO", provider="openai")
    fake = FakeLLM(lang)
    monkeypatch.setattr(A, "TRANSLATE", True)
    monkeypatch.setattr(A, "call_llm", fake)
    A._tr_cache.clear()
    return fake


def test_owner_text_ignores_short_and_commands():
    A.note_owner_text("ok")
    A.note_owner_text("/status bitte jetzt sofort zeigen")
    assert A.get_setting("owner_text", "") == ""
    A.note_owner_text("Merhaba, lütfen yeni bir web sitesi hazırlayın")
    assert A.get_setting("owner_text", "").startswith("Merhaba")
    A.set_setting("owner_lang", "Turkish")
    A.note_owner_text("Bitte schreibe mir einen kurzen Bericht über den Monat")
    assert A.get_setting("owner_lang", "") == ""  # neue Worte -> Sprache neu erkennen


def test_language_line_in_prompt():
    pid = make_project()
    aid = make_agent(pid, "CEO")
    A.note_owner_text("Mirupafshim, ju lutem bëni një raport për muajin")
    s = A.build_system(A.q1("SELECT * FROM agents WHERE id=?", (aid,)), A.q1("SELECT * FROM projects WHERE id=?", (pid,)), "work")
    assert "LANGUAGE:" in s and "Mirupafshim" in s


def test_tr_translates_and_caches(monkeypatch):
    fake = setup(monkeypatch)
    A.note_owner_text("Merhaba, lütfen yeni bir web sitesi hazırlayın")
    assert A.tr("✅ Done") == "TR:✅ Done"
    assert A.get_setting("owner_lang", "") == "Turkish"
    n = len(fake.calls)
    assert A.tr("✅ Done") == "TR:✅ Done" and len(fake.calls) == n  # aus dem Zwischenspeicher


def test_tr_keeps_english_and_without_ai(monkeypatch):
    setup(monkeypatch, lang="English")
    A.note_owner_text("Please build me a new website for the bakery")
    assert A.tr("✅ Done") == "✅ Done"
    A.ex("UPDATE agents SET provider='mock'")
    A.set_setting("owner_lang", "")
    A.note_owner_text("Merhaba, lütfen yeni bir web sitesi hazırlayın")
    assert A.tr("✅ Done") == "✅ Done"  # ohne echte KI bleibt Englisch


def test_tr_off_by_switch(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setattr(A, "TRANSLATE", False)
    A.note_owner_text("Merhaba, lütfen yeni bir web sitesi hazırlayın")
    assert A.tr("✅ Done") == "✅ Done"


def test_telegram_buttons_translated(monkeypatch):
    setup(monkeypatch)
    A.note_owner_text("Merhaba, lütfen yeni bir web sitesi hazırlayın")
    sent = []
    monkeypatch.setattr(A, "tg", lambda method, **kw: sent.append(kw) or {"message_id": 1})
    A.tg_send_now(1, "Approved.", buttons=[[{"text": "✅ Done", "callback_data": "ok:1"}]])
    assert sent[0]["text"] == "TR:Approved."
    assert sent[0]["reply_markup"]["inline_keyboard"][0][0] == {"text": "TR:✅ Done", "callback_data": "ok:1"}
    A.tg_send_now(1, "raw", translate=False)
    assert sent[1]["text"] == "raw"
