import json

import maf_orchestrator


def test_persist_culprit_record_writes_json_array(tmp_path, monkeypatch):
    log_path = tmp_path / "culprit_reports.json"
    monkeypatch.setattr(maf_orchestrator, "CULPRIT_LOG_PATH", str(log_path))
    monkeypatch.setattr(maf_orchestrator, "MAX_HEALING_ITERATIONS", 3)

    record = {
        "number": 3,
        "name": "Slice 3",
        "failure": "AssertionError: expected 2 got 3",
    }

    maf_orchestrator.persist_culprit_record(
        record,
        slice_markdown="## Slice 3\n- sample requirement",
        test_command="cd engine && pytest tests/",
    )

    payload = json.loads(log_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert payload[-1]["number"] == 3
    assert payload[-1]["name"] == "Slice 3"
    assert payload[-1]["failure"] == "AssertionError: expected 2 got 3"
