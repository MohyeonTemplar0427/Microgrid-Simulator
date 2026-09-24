"""CSV-only storage for new browser result tables, with typed paged reads."""

import csv
from itertools import islice
import json
from pathlib import Path

import pandas as pd


def save_table(directory, key, labels, table):
    directory = Path(directory)
    columns = list(table.columns)
    kinds = []
    for column in columns:
        dtype = table[column].dtype
        if pd.api.types.is_bool_dtype(dtype):
            kinds.append("boolean")
        elif pd.api.types.is_integer_dtype(dtype):
            kinds.append("integer")
        elif pd.api.types.is_numeric_dtype(dtype):
            kinds.append("number")
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            kinds.append("datetime")
        else:
            kinds.append("string")
    table.to_csv(directory / f"{key}.csv", index=False)
    from .worker import write_json
    write_json(directory / f"{key}.meta.json", {
        "columns": columns, "labels": labels, "kinds": kinds, "row_count": len(table),
    })


def read_page(directory, key, offset, limit):
    directory = Path(directory)
    metadata = json.loads((directory / f"{key}.meta.json").read_text())
    with (directory / f"{key}.csv").open(newline="", encoding="utf-8") as source:
        reader = csv.reader(source)
        if next(reader) != metadata["columns"]:
            raise ValueError("Saved result columns no longer match their metadata.")
        rows = list(islice(reader, offset, offset + limit))
    def convert(value, kind):
        if value == "":
            return None
        if kind == "boolean":
            if value.lower() not in {"true", "false"}:
                raise ValueError("Saved result contains an invalid Boolean value.")
            return value.lower() == "true"
        if kind == "integer":
            return int(value)
        if kind == "number":
            return float(value)
        return value
    if any(len(row) != len(metadata["kinds"]) for row in rows):
        raise ValueError("Saved result row no longer matches its metadata.")
    return {
        "columns": metadata["columns"], "labels": metadata["labels"],
        "total": metadata["row_count"], "offset": offset,
        "data": [[convert(value, kind) for value, kind in zip(row, metadata["kinds"])] for row in rows],
    }
