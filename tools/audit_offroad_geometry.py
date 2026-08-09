"""אימות תוואי מפות Off-Road ונקודות ציון — גרסת מסמך 1.1.0; מוצר 2.7.0."""

from __future__ import annotations

import concurrent.futures
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


PRODUCT_VERSION = "2.7.0"
DOCUMENT_VERSION = "1.1.0"
USER_AGENT = "IlansAdventureRouteBook/2.7 navigation-completion-audit"
LAYER_URL = "https://api.off-road.io/_ah/api/offroadApi/v2/trackLayers/{layer_key}?access_token="
BREAK_URL = "https://parse.off-road.io/v2/layers/{layer_key}/break?access_token="
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
ISRAEL_BBOX = (29.35, 34.15, 33.40, 35.95)


def get_json(url: str, *, timeout: int = 60) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def haversine_m(a: dict, b: dict) -> float:
    lat1, lon1 = math.radians(float(a["latitude"])), math.radians(float(a["longitude"]))
    lat2, lon2 = math.radians(float(b["latitude"])), math.radians(float(b["longitude"]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 12_742_000 * math.asin(math.sqrt(h))


def point_distance_m(lat: float, lon: float, point: dict) -> float:
    return haversine_m({"latitude": lat, "longitude": lon}, point)


def path_length_km(path: list[dict]) -> float:
    return sum(haversine_m(a, b) for a, b in zip(path, path[1:])) / 1000


def fetch_layer(record: dict) -> dict:
    track_id = str(record["trackId"])
    layer_key = str(record.get("trackLayerKey") or "")
    base = {"trackId": track_id, "trackLayerKey": layer_key, "publicUrl": record.get("publicUrl")}
    if record.get("status") != "verified" or not layer_key:
        return {**base, "status": "source-unavailable", "reason": "אין Track Layer זמין במקור"}
    try:
        payload = get_json(LAYER_URL.format(layer_key=layer_key), timeout=90)
        layers = payload.get("layers") or []
        path = (layers[0].get("path") if layers else None) or []
        path = [p for p in path if p.get("latitude") is not None and p.get("longitude") is not None]
        if len(path) < 2:
            return {**base, "status": "geometry-unavailable", "reason": "שכבת המפה לא החזירה תוואי"}
        source_start, source_end = record.get("start") or {}, record.get("end") or {}
        chunks = [path]
        start_delta = round(min(haversine_m(source_start, point) for point in path), 1) if source_start else None
        end_delta = round(min(haversine_m(source_end, point) for point in path), 1) if source_end else None
        geometry_mode = "track-layer-full"
        if end_delta is not None and end_delta > 100:
            broken = get_json(BREAK_URL.format(layer_key=layer_key), timeout=120)
            chunks = [[point for point in (layer.get("path") or []) if point.get("latitude") is not None and point.get("longitude") is not None] for layer in (broken.get("layers") or [])]
            chunks = [chunk for chunk in chunks if chunk]
            full_path = [point for chunk in chunks for point in chunk]
            full_path = [p for p in full_path if p.get("latitude") is not None and p.get("longitude") is not None]
            if len(full_path) >= 2:
                path = full_path
                start_delta = round(min(haversine_m(source_start, point) for point in path), 1) if source_start else None
                end_delta = round(min(haversine_m(source_end, point) for point in path), 1) if source_end else None
                geometry_mode = "parse-break-full-course"
        lats = [float(p["latitude"]) for p in path]
        lons = [float(p["longitude"]) for p in path]
        calculated_length = round(sum(path_length_km(chunk) for chunk in chunks), 3)
        source_length = record.get("distanceKm")
        distance_delta = round(abs(calculated_length - float(source_length)) / float(source_length) * 100, 1) if source_length else None
        status = "geometry-verified"
        reason = None
        if (start_delta is not None and start_delta > 100) or (end_delta is not None and end_delta > 100):
            status = "geometry-source-inconsistency"
            reason = "שכבת התוואי נפתחה גם בממשק הקורס המלא, אך נקודת ההתחלה או הסיום שבמטא־דאטה אינה נמצאת עד 100 מטר מקו המפה."
        return {
            **base,
            "status": status,
            "reason": reason,
            "pointCount": len(path),
            "geometryMode": geometry_mode,
            "start": {"latitude": lats[0], "longitude": lons[0]},
            "end": {"latitude": lats[-1], "longitude": lons[-1]},
            "sourceStartDeltaM": start_delta,
            "sourceEndDeltaM": end_delta,
            "boundingBox": {"south": min(lats), "west": min(lons), "north": max(lats), "east": max(lons)},
            "calculatedGeometryLengthKm": calculated_length,
            "sourceDistanceKm": source_length,
            "distanceDeltaPercent": distance_delta,
            "path": [{"latitude": float(p["latitude"]), "longitude": float(p["longitude"])} for p in path],
        }
    except Exception as exc:  # network/source failures are evidence, not invented data
        return {**base, "status": "geometry-fetch-failed", "reason": f"{type(exc).__name__}: {exc}"}


def fetch_named_features() -> list[dict]:
    south, west, north, east = ISRAEL_BBOX
    bbox = f"{south},{west},{north},{east}"
    query = f"""[out:json][timeout:240];(
      nwr[\"name\"][\"place\"]({bbox});
      nwr[\"name\"][\"natural\"~\"peak|spring|water|valley|cliff|wood|cave_entrance\"]({bbox});
      nwr[\"name\"][\"waterway\"~\"river|stream|wadi\"]({bbox});
      nwr[\"name\"][\"tourism\"~\"viewpoint|attraction|picnic_site\"]({bbox});
      nwr[\"name\"][\"historic\"]({bbox});
      nwr[\"name\"][\"leisure\"=\"nature_reserve\"]({bbox});
    );out center tags qt;"""
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_error: Exception | None = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            request = urllib.request.Request(endpoint, data=body, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=300) as response:
                payload = json.load(response)
            features = []
            for element in payload.get("elements", []):
                tags = element.get("tags") or {}
                center = element.get("center") or element
                lat, lon = center.get("lat"), center.get("lon")
                name = (tags.get("name:he") or tags.get("name") or "").strip()
                if not name or lat is None or lon is None:
                    continue
                kind = next((f"{key}:{tags[key]}" for key in ("place", "natural", "waterway", "tourism", "historic", "leisure") if tags.get(key)), "named-feature")
                features.append({"name": name, "latitude": float(lat), "longitude": float(lon), "kind": kind, "osmType": element.get("type"), "osmId": element.get("id")})
            return features
        except Exception as exc:
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"Overpass failed: {last_error}")


def add_nearby_landmarks(layers: list[dict], features: list[dict]) -> None:
    cell_size = 0.02
    grid: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for feature in features:
        grid[(int(feature["latitude"] / cell_size), int(feature["longitude"] / cell_size))].append(feature)
    for layer in layers:
        path = layer.get("path") or []
        if not path:
            layer["verifiedNearbyPlaces"] = []
            continue
        candidates: dict[tuple[str, str, int], dict] = {}
        stride = max(1, len(path) // 1200)
        for point in path[::stride]:
            cell = (int(point["latitude"] / cell_size), int(point["longitude"] / cell_size))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for feature in grid.get((cell[0] + dx, cell[1] + dy), []):
                        distance = point_distance_m(feature["latitude"], feature["longitude"], point)
                        limit = 1_200 if feature["kind"].startswith("place:") else 450
                        if distance > limit:
                            continue
                        key = (feature["name"], feature["osmType"], feature["osmId"])
                        existing = candidates.get(key)
                        if existing is None or distance < existing["distanceFromTrackM"]:
                            candidates[key] = {**feature, "distanceFromTrackM": round(distance)}
        ordered = sorted(candidates.values(), key=lambda f: (f["distanceFromTrackM"], f["name"]))
        seen_names: set[str] = set()
        selected = []
        for feature in ordered:
            folded = feature["name"].strip().casefold()
            if folded in seen_names:
                continue
            seen_names.add(folded)
            selected.append(feature)
            if len(selected) == 24:
                break
        layer["verifiedNearbyPlaces"] = selected


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output_path = root / "data" / "offroad-geometry-audit.json"
    if "--reclassify-existing" in sys.argv:
        output = json.loads(output_path.read_text(encoding="utf-8"))
        counts = defaultdict(int)
        for layer in output["tracks"]:
            if layer.get("status") == "geometry-verified" and ((layer.get("sourceStartDeltaM") or 0) > 100 or (layer.get("sourceEndDeltaM") or 0) > 100):
                layer["status"] = "geometry-source-inconsistency"
                layer["reason"] = "שכבת התוואי נפתחה גם בממשק הקורס המלא, אך נקודת ההתחלה או הסיום שבמטא־דאטה אינה נמצאת עד 100 מטר מקו המפה."
            counts[layer["status"]] += 1
        output["counts"] = {
            "totalTrackIds": len(output["tracks"]),
            **dict(sorted(counts.items())),
            "osmNamedFeaturesConsidered": output["counts"].get("osmNamedFeaturesConsidered", 0),
            "tracksWithNearbyPlaces": sum(bool(item.get("verifiedNearbyPlaces")) for item in output["tracks"]),
        }
        output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(output["counts"], ensure_ascii=False, indent=2))
        return 0
    metadata = json.loads((root / "data" / "offroad-all-metadata.json").read_text(encoding="utf-8"))
    record_map = metadata["records"]
    records = list(record_map.values()) if isinstance(record_map, dict) else list(record_map)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        layers = list(pool.map(fetch_layer, records))
    features = fetch_named_features()
    add_nearby_landmarks(layers, features)
    for layer in layers:
        layer.pop("path", None)
    counts = defaultdict(int)
    for layer in layers:
        counts[layer["status"]] += 1
    output = {
        "title": f"אימות תוואי מפות ונקודות ציון — גרסת מסמך {DOCUMENT_VERSION}",
        "productVersion": PRODUCT_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "method": "כל שכבת Track נפתחה ישירות מ-Off-Road, נקודות התוואי הושוו לקואורדינטות המקור, ושמות סמוכים נוספו רק מישויות ממופות של OpenStreetMap הנמצאות במרחק המדווח מן התוואי. שכבה שבה נקודת הסיום לא נמצאה נפתחה גם דרך תצוגת break של Off-Road; סתירה שנשארה לאחר מכן מסומנת כסתירה פנימית במקור.",
        "landmarkPolicy": "יישוב עד 1,200 מטר מן התוואי; אתר טבע, מים, תצפית, שמורה או אתר היסטורי עד 450 מטר. המרחק נשמר לכל שם; קרבה אינה הוכחה שהמסלול נכנס לאתר.",
        "sources": {
            "offRoadTrackLayerApi": "https://api.off-road.io/_ah/api/offroadApi/v2/trackLayers/{trackLayerKey}",
            "offRoadFullCourseApi": "https://parse.off-road.io/v2/layers/{trackLayerKey}/break",
            "openStreetMap": "https://www.openstreetmap.org/copyright",
            "overpassApi": list(OVERPASS_ENDPOINTS),
        },
        "counts": {"totalTrackIds": len(layers), **dict(sorted(counts.items())), "osmNamedFeaturesConsidered": len(features), "tracksWithNearbyPlaces": sum(bool(x.get("verifiedNearbyPlaces")) for x in layers)},
        "tracks": layers,
    }
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["counts"], ensure_ascii=False, indent=2))
    return 0 if not counts.get("geometry-fetch-failed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
