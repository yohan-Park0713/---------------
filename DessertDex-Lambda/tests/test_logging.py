import logging
from types import SimpleNamespace

import pytest

from lambda_function import lambda_handler

VALID_EVENT = {"total_desserts": 2, "collected_desserts": 1, "unlock_threshold": 50}


def test_success_log_has_request_id_and_duration(caplog):
    caplog.set_level(logging.INFO, logger="lambda_function")

    response = lambda_handler(VALID_EVENT, SimpleNamespace(aws_request_id="invocation-123"))

    assert response["statusCode"] == 200
    record, = caplog.records
    assert record.levelno == logging.INFO
    assert record.request_id == "invocation-123"
    assert record.outcome == "success"
    assert record.error_code is None
    assert record.duration_ms >= 0


@pytest.mark.parametrize(
    ("event", "error_code"),
    [
        ([], "INVALID_INPUT_TYPE"),
        ({"total_desserts": None}, "INVALID_INPUT_TYPE"),
        ({}, "INVALID_COLLECTION_DATA"),
        ({"total_desserts": 2, "unlock_threshold": 101}, "INVALID_UNLOCK_THRESHOLD"),
    ],
)
def test_validation_warning_without_context(caplog, event, error_code):
    assert lambda_handler(event, None)["statusCode"] == 400

    record, = caplog.records
    assert record.levelno == logging.WARNING
    assert record.request_id is None
    assert record.outcome == "validation_failed"
    assert record.error_code == error_code
    assert record.duration_ms >= 0


def test_logs_exclude_request_data(caplog):
    caplog.set_level(logging.INFO, logger="lambda_function")
    private_fields = {
        "user_id": "private-user-marker",
        "authorization": "Bearer private-token-marker",
        "aws_secret_access_key": "private-key-marker",
        "request_id": "caller-request-id-marker",
    }
    lambda_handler({**VALID_EVENT, **private_fields}, None)
    lambda_handler({**private_fields, "total_desserts": "raw-input-marker"}, None)

    assert len(caplog.records) == 2
    for record in caplog.records:
        attributes = repr(vars(record))
        for value in (*private_fields.values(), "raw-input-marker"):
            assert value not in attributes


@pytest.mark.parametrize("event", [VALID_EVENT, {}])
def test_logging_failure_preserves_response(monkeypatch, event):
    expected = lambda_handler(event, None)

    def fail_to_log(*args, **kwargs):
        raise RuntimeError("logging failed")

    monkeypatch.setattr("lambda_function.logger.log", fail_to_log)

    assert lambda_handler(event, None) == expected
