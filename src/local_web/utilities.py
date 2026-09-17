"""California CEC point-in-territory matching; never infers account enrollment."""
from datetime import datetime, timezone
import requests
from .contract import number

BASE = "https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/"
LAYERS = {"distribution": BASE + "ElectricLoadServingEntities_IOU_POU/FeatureServer/0",
          "other": BASE + "ElectricLoadServingEntities_Other/FeatureServer/0"}


def lookup_utilities(request, *, get=None):
    if not isinstance(request, dict) or set(request) != {"latitude", "longitude"}:
        raise ValueError("Supply latitude and longitude for utility matching.")
    latitude = request["latitude"]
    longitude = request["longitude"]
    number(latitude, "Latitude", -90, 90)
    number(longitude, "Longitude", -180, 180)
    result = dict(candidates=[], coverage="California", status="no_match", sources=list(LAYERS.values()),
                  retrieved_at=datetime.now(timezone.utc).isoformat(), request=request,
                  message="No mapped California provider found. Select a manual service option.")
    # Coverage filter only, never a utility assignment.
    if not (32 <= latitude <= 43 and -125 <= longitude <= -113):
        result.update(status="outside_coverage", message="Automatic utility matching currently covers California. Select a manual service option.")
        return result
    failures = []
    for kind, url in LAYERS.items():
        try:
            response = (get or requests.get)(url + "/query", params={
                "f": "json", "geometry": f"{longitude},{latitude}", "geometryType": "esriGeometryPoint",
                "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "returnGeometry": "false",
                "outFields": "OBJECTID,Utility,Acronym,Type", "resultRecordCount": 100}, timeout=10)
            response.raise_for_status()
            data = response.json()
            if "error" in data or "features" not in data or data.get("exceededTransferLimit"):
                raise ValueError("Incomplete territory response")
            entries = []
            for feature in data["features"]:
                a = feature["attributes"]
                if not isinstance(a.get("Utility"), str) or not a["Utility"].strip() or type(a.get("OBJECTID")) is not int:
                    raise ValueError("Invalid territory record")
                pge = kind == "distribution" and a.get("Acronym") == "PG&E"
                entries.append(dict(id="pge" if pge else f"cec:{kind}:{a['OBJECTID']}",
                                    name=a["Utility"], type=a.get("Type") or "utility", source_url=url,
                                    object_id=a["OBJECTID"], bundled_tariff_supported=pge))
            result["candidates"].extend(entries)
        except (requests.RequestException, ValueError, KeyError, TypeError):
            failures.append(kind)
    result["candidates"] = sorted({x["id"]: x for x in result["candidates"]}.values(), key=lambda x:x["name"])
    if failures:
        result.update(status="partial" if result["candidates"] else "unavailable",
                      message="Some territory data could not be retrieved. Matches may be incomplete; manual service selection remains available.")
    elif result["candidates"]:
        result.update(status="matched", message="CEC territory matches. Boundaries are approximate; select the service shown on your bill. CCA generation and utility delivery may overlap.")
    return result
