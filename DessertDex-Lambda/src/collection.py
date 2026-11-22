def calculate_collection(total: int, collected: int, threshold: int) -> tuple[float, bool]:
    rate = round((collected / total) * 100, 2)
    return rate, rate >= threshold
