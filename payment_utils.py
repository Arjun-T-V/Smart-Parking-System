
from decimal import Decimal
from math import ceil


RATE_PER_BLOCK = Decimal("30.00")
BLOCK_MINUTES = 30


def calculate_parking_fee(start_time, end_time):
    """Charge ₹30 for each started 30-minute block."""

    duration_seconds = (end_time - start_time).total_seconds()

    if duration_seconds <= 0:
        raise ValueError("End time must be after start time.")

    duration_minutes = duration_seconds / 60
    blocks = ceil(duration_minutes / BLOCK_MINUTES)

    return RATE_PER_BLOCK * blocks
