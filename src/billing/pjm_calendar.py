"""Published PJM business holidays; never a generic US/NERC calendar."""
import numpy as np
import pandas as pd

SOURCE_2025 = "https://www.pjm.com/-/media/DotCom/markets-ops/settlements/2025-business-calendar.pdf"
SOURCE_2026 = "https://www.pjm.com/-/media/DotCom/markets-ops/settlements/2026-business-calendar.pdf"
HOLIDAYS = {
    2025: {"01-01", "01-20", "02-17", "05-26", "07-04", "09-01", "11-27", "11-28", "12-25"},
    # PJM explicitly lists Saturday July4; do not invent a Friday July3 holiday.
    2026: {"01-01", "01-19", "02-16", "05-25", "07-04", "09-07", "11-26", "11-27", "12-25"},
}


def holiday_mask(index):
    """Use the published observed dates, without inventing weekend substitutions."""
    index = pd.DatetimeIndex(index)
    if index.tz is None or str(index.tz) != "America/New_York":
        raise ValueError("PJM retail holiday matching requires America/New_York local timestamps.")
    if any(year not in HOLIDAYS for year in index.year.unique()):
        raise ValueError("Published PJM holiday coverage is calendar 2025–2026 only.")
    return np.array([t.strftime("%m-%d") in HOLIDAYS[t.year] for t in index], dtype=bool)
