import pytest

from validation import validate_collection


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((True, 0, 100), "Invalid input type"),
        ((1, False, 100), "Invalid input type"),
        ((1, 0, True), "Invalid input type"),
        ((1, 0.0, 100), "Invalid input type"),
        ((1, None, 100), "Invalid input type"),
        ((-1, 0, 100), "Invalid collection data"),
        ((1, -1, 100), "Invalid collection data"),
        ((1, 0, -1), "Invalid unlock threshold"),
        ((1, 0, 101), "Invalid unlock threshold"),
        ((0, "0", 101), "Invalid input type"),
        ((0, 0, 101), "Invalid collection data"),
        ((1, 0, 0), None),
        ((1, 1, 100), None),
    ],
)
def test_validate_collection(values, expected):
    assert validate_collection(*values) == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((2**53, 0, None), "Invalid input type"),
        ((2**53, 0, 101), "Invalid collection data"),
        ((1, 0, 1 << 100_000), "Invalid unlock threshold"),
    ],
    ids=["type-before-count-limit", "count-limit-before-threshold", "oversized-threshold"],
)
def test_validation_priority_with_large_integers(values, expected):
    assert validate_collection(*values) == expected
