"""Strict Data Miner historical-file import, including revisions and DST.

Raw bytes and revision columns remain private study inputs. No row filling,
timezone guessing, node substitution or public redistribution is performed.
"""
import hashlib
import io
import math
import pandas as pd

FEEDS = {"REAL_TIME_5_MIN": ("total_lmp_rt", 5),
         "REAL_TIME_HOURLY": ("total_lmp_rt", 60),
         "DAY_AHEAD_HOURLY": ("total_lmp_da", 60)}


def import_pjm_csv(csv_text, metadata, start, end, location):
    if not isinstance(csv_text, str) or len(csv_text.encode()) > 8 * 1024 * 1024:
        raise ValueError("PJM CSV must be UTF-8 text within 8 MiB.")
    if not isinstance(metadata, dict) or set(metadata) != {"market", "source_url", "retrieved_at", "unit", "usage_permission"}:
        raise ValueError("Supply market, source URL, retrieval timestamp, unit and usage permission.")
    if metadata["market"] not in FEEDS or metadata["unit"] != "$/MWh" or metadata["usage_permission"] != "internal_use_only":
        raise ValueError("Choose a supported PJM feed, $/MWh units and internal-use-only permission.")
    from urllib.parse import urlsplit
    source = urlsplit(metadata["source_url"])
    if source.scheme != "https" or source.hostname not in ("dataminer2.pjm.com", "api.pjm.com", "www.pjm.com"):
        raise ValueError("Provide the official PJM source URL.")
    retrieved = pd.Timestamp(metadata["retrieved_at"])
    if retrieved.tzinfo is None:
        raise ValueError("Retrieval timestamp must have a timezone.")
    price, minutes = FEEDS[metadata["market"]]
    frame = pd.read_csv(io.StringIO(csv_text))
    aliases = {"Datetime Beginning UTC": "datetime_beginning_utc", "Pricing Node ID": "pnode_id",
               "Pricing Node Name": "pnode_name", "Transmission Zone": "zone",
               "Total LMP Real Time": "total_lmp_rt", "Total LMP Day Ahead": "total_lmp_da",
               "Version Number": "version_nbr", "Latest Version": "row_is_current"}
    if any(k in frame and v in frame for k, v in aliases.items()):
        raise ValueError("Ambiguous duplicate PJM column aliases.")
    frame = frame.rename(columns=aliases)
    required = {"datetime_beginning_utc", "pnode_id", "pnode_name", "zone", price,
                "version_nbr", "row_is_current"}
    if not required <= set(frame):
        raise ValueError("PJM file lacks timestamp, node, zone, price or revision fields: " + str(sorted(required-set(frame))))
    if len(frame) > 110000 or frame.empty:
        raise ValueError("PJM file must contain 1–110,000 rows.")
    # This source column explicitly denotes UTC, including when PJM omits Z.
    frame["timestamp"] = pd.to_datetime(frame.datetime_beginning_utc, utc=True, errors="raise")
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise ValueError("Supply an ordered, timezone-aware historical window.")
    frame = frame.loc[(frame.timestamp >= start) & (frame.timestamp < end)].copy()
    if frame.empty or set(frame.pnode_id.astype(str)) != {str(location["pnode_id"])} or set(frame.pnode_name) != {location["pnode_name"]} or set(frame.zone) != {location["zone"]}:
        raise ValueError("Every selected row must match the verified pricing node and zone exactly.")
    current = frame.row_is_current.astype(str).str.lower()
    if not current.isin(["true", "false"]).all():
        raise ValueError("row_is_current must explicitly be true or false.")
    frame["version_nbr"] = pd.to_numeric(frame.version_nbr, errors="raise")
    frame[price] = pd.to_numeric(frame[price], errors="raise")
    if not frame[[price, "version_nbr"]].map(lambda v: math.isfinite(v)).all().all() or (frame.version_nbr < 1).any() or (frame.version_nbr % 1 != 0).any():
        raise ValueError("Prices must be finite and revision numbers positive integers.")
    latest = frame.groupby("timestamp").version_nbr.transform("max")
    selected = frame.loc[(current == "true") & (frame.version_nbr == latest)].copy()
    if selected.timestamp.duplicated().any():
        raise ValueError("Conflicting or duplicate latest PJM revisions.")
    selected = selected.sort_values("timestamp")
    expected = pd.date_range(start, end, freq=f"{minutes}min", inclusive="left").tz_convert("UTC")
    if not pd.DatetimeIndex(selected.timestamp).equals(expected):
        raise ValueError("PJM data must cover every native interval exactly once; missing/stale revisions are not filled.")
    selected["price_per_kWh"] = selected[price] / 1000
    provenance = {**metadata, "raw_sha256": hashlib.sha256(csv_text.encode()).hexdigest(),
                  "native_interval_minutes": minutes, "timestamp_convention": "interval-start UTC",
                  "pricing_location": location, "revision_numbers": sorted(selected.version_nbr.unique().tolist()),
                  "selected_rows": len(selected), "public_download_allowed": False}
    return selected, provenance
