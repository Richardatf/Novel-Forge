import pytest

from novel_forge import auth


def test_local_mode_does_not_require_password(monkeypatch):
    monkeypatch.delenv("NOVEL_FORGE_HOSTED", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    assert auth.login_required() is True


def test_hosted_mode_without_password_fails_closed(monkeypatch):
    monkeypatch.setenv("NOVEL_FORGE_HOSTED", "true")
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.setattr(auth.st, "error", lambda *_: None)
    monkeypatch.setattr(auth.st, "caption", lambda *_: None)
    monkeypatch.setattr(auth.st, "stop", lambda: (_ for _ in ()).throw(RuntimeError("stopped")))
    with pytest.raises(RuntimeError, match="stopped"):
        auth.login_required()

