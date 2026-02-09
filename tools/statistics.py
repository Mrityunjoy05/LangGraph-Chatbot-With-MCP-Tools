from statistics import mean, median


async def calculate_mean(numbers: list[float]) -> float:
    """Computes the arithmetic mean of a list of numbers."""
    return mean(numbers)


async def calculate_median(numbers: list[float]) -> float:
    """Computes the median of a list of numbers."""
    return median(numbers)