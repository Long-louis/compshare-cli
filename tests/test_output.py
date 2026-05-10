from compshare_cli.output import print_json, table_text


def test_print_json_outputs_serialized_payload(capsys):
    print_json({"RetCode": 0, "UHostIds": ["uhost-1"]})

    assert '"RetCode": 0' in capsys.readouterr().out


def test_table_text_renders_headers_and_rows():
    rendered = table_text(["REGION", "ZONE"], [["cn-sh2", "cn-sh2-02"]])

    assert "REGION" in rendered
    assert "cn-sh2-02" in rendered
