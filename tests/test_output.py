import json

from compshare_cli.output import (
    agent_envelope,
    command_suggestion,
    print_json,
    quiet_sdk_logs,
    table_text,
)


def test_agent_envelope_includes_required_fields():
    payload = agent_envelope(
        command="resource zones",
        summary="Found 2 supported zones.",
        data={"zones": []},
        cost_risk="read-only",
    )

    assert payload == {
        "ok": True,
        "command": "resource zones",
        "summary": "Found 2 supported zones.",
        "data": {"zones": []},
        "warnings": [],
        "next_actions": [],
        "commands": [],
        "cost_risk": "read-only",
        "debug": {},
    }


def test_command_suggestion_has_risk_and_confirmation():
    suggestion = command_suggestion(
        label="Create instance",
        command="compshare instance create --agent",
        risk="cost-incurring",
        requires_confirmation=True,
    )

    assert suggestion == {
        "label": "Create instance",
        "command": "compshare instance create --agent",
        "risk": "cost-incurring",
        "requires_confirmation": True,
    }


def test_print_json_is_parseable_stdout(capsys):
    print_json({"ok": True})

    assert json.loads(capsys.readouterr().out) == {"ok": True}


def test_quiet_sdk_logs_sets_ucloud_logger_above_info():
    logger = quiet_sdk_logs()

    assert logger.name == "ucloud"
    assert logger.level > 20


def test_print_json_outputs_serialized_payload(capsys):
    print_json({"RetCode": 0, "UHostIds": ["uhost-1"]})

    assert '"RetCode": 0' in capsys.readouterr().out


def test_table_text_renders_headers_and_rows():
    rendered = table_text(["REGION", "ZONE"], [["cn-sh2", "cn-sh2-02"]])

    assert "REGION" in rendered
    assert "cn-sh2-02" in rendered
