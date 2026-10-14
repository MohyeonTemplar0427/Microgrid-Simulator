"""ComEd's verified residual aggregate, using the shared PJM file adapter.

The native PJM zone field is blank for this EDC aggregate. It is independent
of the account's COMED transmission zone. No nearest-node or hub fallback.
"""
import pandas as pd

from ..signal_pipeline.providers.pjm import PJMProvider

RESIDUAL_LOCATION = {"pnode_id": "116472935", "pnode_name": "COMED_RESID_AGG", "zone": "",
    "source": "PJM Data Miner Real-Time Hourly LMPs; residual EDC row identity verified October 13, 2026"}


def import_residual_prices(csv_text, metadata, grid):
    if not isinstance(metadata, dict) or metadata.get("market") != "REAL_TIME_HOURLY":
        raise ValueError("BESH requires final real-time hourly residual prices, not five-minute estimates or day-ahead prices.")
    hours = grid.tz_convert("UTC").floor("h").unique()
    frame, provenance = PJMProvider.import_historical_file(csv_text, metadata,
        hours[0], hours[-1]+pd.Timedelta(hours=1), RESIDUAL_LOCATION)
    if "type" not in frame or not frame.type.eq("RESIDUAL_METERED_EDC").all():
        raise ValueError("Every price row must identify COMED_RESID_AGG as RESIDUAL_METERED_EDC.")
    return frame.set_index("timestamp").total_lmp_rt, provenance
