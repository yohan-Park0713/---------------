import pytest

from lambda_function import lambda_handler


@pytest.mark.parametrize(
    ("event", "status_code", "body"),
    [
        pytest.param(
            {"total_desserts": 3, "collected_desserts": 2, "unlock_threshold": 80},
            200, '{"collection_rate": 66.67, "special_illustration_unlocked": false}',
            id="collection-rate",
        ),
        pytest.param(
            {"total_desserts": 10, "collected_desserts": 8, "unlock_threshold": 80},
            200, '{"collection_rate": 80.0, "special_illustration_unlocked": true}',
            id="unlock-at-threshold",
        ),
        pytest.param(
            {"total_desserts": "10", "collected_desserts": 8},
            400, '{"message": "Invalid input type"}',
            id="non-integer",
        ),
        pytest.param(
            {"total_desserts": 2, "collected_desserts": 3},
            400, '{"message": "Invalid collection data"}',
            id="collected-exceeds-total",
        ),
        pytest.param(
            {"total_desserts": 0, "collected_desserts": 0},
            400, '{"message": "Invalid collection data"}',
            id="zero-total",
        ),
        pytest.param(
            {"total_desserts": 2, "unlock_threshold": 101},
            400, '{"message": "Invalid unlock threshold"}',
            id="invalid-threshold",
        ),
        pytest.param(
            {"total_desserts": 2},
            200, '{"collection_rate": 0.0, "special_illustration_unlocked": false}',
            id="default-collected",
        ),
        pytest.param(
            {"total_desserts": 2, "collected_desserts": 1, "extra": "ignored"},
            200, '{"collection_rate": 50.0, "special_illustration_unlocked": false}',
            id="default-threshold-and-extra-field",
        ),
        pytest.param(
            {"total_desserts": 2, "collected_desserts": 2},
            200, '{"collection_rate": 100.0, "special_illustration_unlocked": true}',
            id="default-threshold-at-100",
        ),
        pytest.param(
            {},
            400, '{"message": "Invalid collection data"}',
            id="default-total",
        ),
        pytest.param(
            {"total_desserts": 20_001, "collected_desserts": 20_000},
            200, '{"collection_rate": 100.0, "special_illustration_unlocked": true}',
            id="unlock-after-rounding",
        ),
    ],
)
def test_lambda_response_contract(event, status_code, body):
    assert lambda_handler(event, None) == {"statusCode": status_code, "body": body}


@pytest.mark.parametrize("event", [None, True, 1, 1.0, "raw input", [], ()])
def test_rejects_non_dict_events(event):
    assert lambda_handler(event, None) == {
        "statusCode": 400,
        "body": '{"message": "Invalid input type"}',
    }


@pytest.mark.parametrize(
    "field", ["total_desserts", "collected_desserts", "unlock_threshold"]
)
@pytest.mark.parametrize("value", [None, True, 1.0, "raw input", []])
def test_rejects_invalid_field_types(field, value):
    event = {"total_desserts": 2, "collected_desserts": 1, "unlock_threshold": 50}
    event[field] = value

    assert lambda_handler(event, None) == {
        "statusCode": 400,
        "body": '{"message": "Invalid input type"}',
    }


@pytest.mark.parametrize(
    ("total", "collected"),
    [(2**53, 0), (1 << 100_000, 1 << 100_000), (1, 1 << 100_000)],
    ids=["above-limit", "oversized-counts", "oversized-collected"],
)
def test_rejects_oversized_counts(total, collected):
    assert lambda_handler({"total_desserts": total, "collected_desserts": collected}, None) == {
        "statusCode": 400,
        "body": '{"message": "Invalid collection data"}',
    }


def test_accepts_maximum_counts():
    max_count = 2**53 - 1
    assert lambda_handler({"total_desserts": max_count, "collected_desserts": max_count}, None) == {
        "statusCode": 200,
        "body": '{"collection_rate": 100.0, "special_illustration_unlocked": true}',
    }
