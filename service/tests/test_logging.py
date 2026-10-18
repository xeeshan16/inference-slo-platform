from __future__ import annotations

import json
import logging

from app.logging_setup import JsonFormatter


def test_json_formatter_includes_extra_fields() -> None:
    record = logging.makeLogRecord(
        {"name": "inference", "levelname": "INFO", "msg": "hello %s", "args": ("world",)}
    )
    record.model_version = "v1"
    line = json.loads(JsonFormatter().format(record))
    assert line["msg"] == "hello world"
    assert line["level"] == "INFO"
    assert line["model_version"] == "v1"
    assert "trace_id" not in line
