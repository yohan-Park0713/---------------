import pytest

from collection import calculate_collection


@pytest.mark.parametrize(
    ("total", "collected", "threshold", "expected"),
    [
        (3, 2, 100, (66.67, False)),
        (3, 1, 0, (33.33, True)),
        (2, 1, 50, (50.0, True)),
        (2, 1, 51, (50.0, False)),
        (4, 0, 0, (0.0, True)),
        (4, 0, 1, (0.0, False)),
        (4, 4, 100, (100.0, True)),
        (20_001, 20_000, 100, (100.0, True)),
    ],
)
def test_collection_rate_and_unlock(total, collected, threshold, expected):
    assert calculate_collection(total, collected, threshold) == expected
