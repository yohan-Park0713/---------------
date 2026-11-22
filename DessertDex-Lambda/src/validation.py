MAX_DESSERT_COUNT = 2**53 - 1


def validate_collection(total: object, collected: object, threshold: object) -> str | None:
    if not all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in (total, collected, threshold)
    ):
        return "Invalid input type"

    if not 1 <= total <= MAX_DESSERT_COUNT or not 0 <= collected <= total:
        return "Invalid collection data"

    if not 0 <= threshold <= 100:
        return "Invalid unlock threshold"

    return None
