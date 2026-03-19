import sys
from types import SimpleNamespace


def test_cli_skills_install_accepts_yes_alias(monkeypatch):
    from gauss_cli.main import main

    captured = {}

    def fake_skills_command(args):
        captured["identifier"] = args.identifier
        captured["force"] = args.force

    monkeypatch.setattr("gauss_cli.skills_hub.skills_command", fake_skills_command)
    monkeypatch.setattr(
        sys,
        "argv",
        ["gauss", "skills", "install", "official/email/agentmail", "--yes"],
    )

    main()

    assert captured == {
        "identifier": "official/email/agentmail",
        "force": True,
    }
