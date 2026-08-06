"""השלמת מטא-דאטה Off-Road — גרסת מסמך 2.1.5; גרסת מוצר 2.1.0.

הכלי קורא את מזהי ה-Track שכבר קיימים בכרטיסי הספר, מושך רק נתוני מקור
ציבוריים מ-Off-Road, ושומר אותם כ-JSON וכ-JavaScript סטטי לשימוש ה-PWA.
הוא אינו ממציא נתונים ואינו מסיק התאמה לאופנוע או תקינות מסלול.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRODUCT_VERSION = "2.1.0"
DOCUMENT_VERSION = "2.1.5"
API_TEMPLATE = "https://api.off-road.io/_ah/api/offroadApi/v2/tracks/trackResult/{track_id}"
PUBLIC_TEMPLATE = "https://off-road.io/track/{track_id}"
USER_AGENT = "IlansAdventureGuide/2.1.0 metadata-enrichment"

DIFFICULTY_LABELS = {
    0: "לא דורג במקור",
    1: "1/5 — קל",
    2: "2/5 — קל–בינוני",
    3: "3/5 — בינוני",
    4: "4/5 — בינוני–קשה",
    5: "5/5 — קשה",
}

ACTIVITY_LABELS = {
    "Motorcycling": "אופנוע",
    "OffRoading": "רכיבת שטח",
    "MountainBiking": "אופני הרים",
    "Cycling": "אופניים",
    "Hiking": "הליכה",
    "Driving": "רכב",
}


def positive_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def integer_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def duration_text(duration_ms: int | None) -> str | None:
    if not duration_ms or duration_ms <= 0:
        return None
    total_minutes = max(1, round(duration_ms / 60000))
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours} שעות ו-{minutes} דקות"
    if hours == 1:
        return "שעה"
    if hours:
        return f"{hours} שעות"
    return f"{minutes} דקות"


def coordinate(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        latitude = float(value["latitude"])
        longitude = float(value["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    return {"latitude": latitude, "longitude": longitude}


def normalize_track(track_id: str, payload: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    track = payload.get("track") if isinstance(payload, dict) else None
    if not isinstance(track, dict):
        raise ValueError("API response has no track object")

    layers = track.get("layersStatistics") if isinstance(track.get("layersStatistics"), dict) else {}
    distance = positive_number(layers.get("distance")) or positive_number(track.get("totalLengthKm"))
    duration_ms = integer_or_none(track.get("duration"))
    difficulty_level = integer_or_none(track.get("difficultyLevel"))
    activity_type = str(track.get("activityType") or "").strip() or None
    activities = track.get("activities") if isinstance(track.get("activities"), dict) else {}

    return {
        "trackId": track_id,
        "publicUrl": PUBLIC_TEMPLATE.format(track_id=track_id),
        "apiUrl": API_TEMPLATE.format(track_id=track_id),
        "status": "verified",
        "fetchedAt": fetched_at,
        "title": str(track.get("title") or "").strip() or None,
        "shortDescription": str(track.get("shortDescription") or "").strip() or None,
        "distanceKm": round(distance, 3) if distance is not None else None,
        "distanceBasis": "track.layersStatistics.distance" if positive_number(layers.get("distance")) else ("track.totalLengthKm" if positive_number(track.get("totalLengthKm")) else None),
        "durationMs": duration_ms if duration_ms and duration_ms > 0 else None,
        "durationDisplay": duration_text(duration_ms),
        "difficultyLevel": difficulty_level,
        "difficultyDisplay": DIFFICULTY_LABELS.get(difficulty_level, "לא דורג במקור"),
        "activityType": activity_type,
        "activityDisplay": ACTIVITY_LABELS.get(activity_type, activity_type or "לא צוין במקור"),
        "start": coordinate(track.get("start")),
        "end": coordinate(track.get("end")),
        "roundTrip": activities.get("roundTrip") if isinstance(activities.get("roundTrip"), bool) else None,
        "created": track.get("created"),
        "updated": track.get("updated"),
        "ownerDisplayName": str(track.get("ownerDisplayName") or "").strip() or None,
        "rating": track.get("rating"),
        "reviews": integer_or_none(track.get("reviews")),
    }


def fetch_track(track_id: str, fetched_at: str, timeout: int, retries: int) -> dict[str, Any]:
    url = API_TEMPLATE.format(track_id=track_id)
    last_error = "unknown error"
    for attempt in range(1, retries + 2):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                result = normalize_track(track_id, payload, fetched_at)
                result["httpStatus"] = int(response.status)
                result["attempts"] = attempt
                return result
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
            if exc.code in {400, 401, 403, 404}:
                return {
                    "trackId": track_id,
                    "publicUrl": PUBLIC_TEMPLATE.format(track_id=track_id),
                    "apiUrl": url,
                    "status": "unavailable",
                    "fetchedAt": fetched_at,
                    "httpStatus": exc.code,
                    "attempts": attempt,
                    "error": last_error,
                }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            last_error = str(exc)
        if attempt <= retries:
            time.sleep(0.5 * attempt)
    return {
        "trackId": track_id,
        "publicUrl": PUBLIC_TEMPLATE.format(track_id=track_id),
        "apiUrl": url,
        "status": "error",
        "fetchedAt": fetched_at,
        "httpStatus": None,
        "attempts": retries + 1,
        "error": last_error,
    }


def compact_for_route(record: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "trackId", "publicUrl", "status", "title", "distanceKm", "durationMs",
        "durationDisplay", "difficultyLevel", "difficultyDisplay", "activityType",
        "activityDisplay", "start", "end", "roundTrip", "updated", "httpStatus",
    )
    return {key: record.get(key) for key in keys}


def combined_length_time(record: dict[str, Any]) -> str:
    parts: list[str] = []
    distance = record.get("distanceKm")
    if isinstance(distance, (int, float)) and distance > 0:
        parts.append(f"{distance:.1f} ק״מ")
    if record.get("durationDisplay"):
        parts.append(str(record["durationDisplay"]))
    return " · ".join(parts) or "לא צוין במקור"


def enrich_routes(routes_doc: dict[str, Any], records: dict[str, dict[str, Any]], generated_at: str) -> dict[str, int]:
    routes = routes_doc.get("routes") if isinstance(routes_doc.get("routes"), list) else []
    cards_with_tracks = 0
    cards_with_verified_tracks = 0
    cards_filled_distance = 0
    cards_filled_duration = 0

    for route in routes:
        map_info = route.get("map") if isinstance(route.get("map"), dict) else {}
        track_ids = [str(item) for item in (map_info.get("trackIds") or []) if str(item).isdigit()]
        if not track_ids:
            route.pop("offroadTracks", None)
            continue
        cards_with_tracks += 1
        route_records = [records[item] for item in track_ids if item in records]
        route["offroadTracks"] = [compact_for_route(item) for item in route_records]
        verified = [item for item in route_records if item.get("status") == "verified"]
        if verified:
            cards_with_verified_tracks += 1

        if len(track_ids) == 1 and len(verified) == 1:
            source = verified[0]
            route["sourceTrackTitle"] = source.get("title")
            route["sourceDistanceKm"] = source.get("distanceKm")
            route["sourceDurationMs"] = source.get("durationMs")
            route["sourceDurationDisplay"] = source.get("durationDisplay")
            route["sourceDifficultyLevel"] = source.get("difficultyLevel")
            route["sourceDifficultyDisplay"] = source.get("difficultyDisplay")
            route["sourceActivityType"] = source.get("activityType")
            route["sourceActivityDisplay"] = source.get("activityDisplay")
            if route.get("distanceKm") is None and source.get("distanceKm") is not None:
                route["distanceKm"] = source["distanceKm"]
                cards_filled_distance += 1
            if str(route.get("lengthTimeDisplay") or "").strip() in {"", "לא צוין", "לא נמסר"}:
                route["lengthTimeDisplay"] = combined_length_time(source)
                if source.get("durationMs"):
                    cards_filled_duration += 1
        else:
            for key in (
                "sourceTrackTitle", "sourceDistanceKm", "sourceDurationMs", "sourceDurationDisplay",
                "sourceDifficultyLevel", "sourceDifficultyDisplay", "sourceActivityType", "sourceActivityDisplay",
            ):
                route.pop(key, None)

    routes_doc["documentVersion"] = DOCUMENT_VERSION
    routes_doc["generatedAt"] = generated_at
    routes_doc["offroadMetadataCoverage"] = {
        "cardsWithTrackIds": cards_with_tracks,
        "cardsWithVerifiedTracks": cards_with_verified_tracks,
        "cardsFilledDistanceFromSingleTrack": cards_filled_distance,
        "cardsFilledDurationFromSingleTrack": cards_filled_duration,
        "policy": "נתוני מקור מוצגים לכל Track בנפרד; אין לחבר מרחקים או זמנים של מספר הקלטות ללא הוכחה שהן מקטעים רציפים.",
    }
    return routes_doc["offroadMetadataCoverage"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich all Off-Road track references in the route guide")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()

    root = args.root.resolve()
    routes_path = root / "data" / "routes.json"
    routes_doc = json.loads(routes_path.read_text(encoding="utf-8"))
    routes = routes_doc.get("routes") if isinstance(routes_doc.get("routes"), list) else []
    track_ids = sorted({
        str(track_id)
        for route in routes
        for track_id in ((route.get("map") or {}).get("trackIds") or [])
        if str(track_id).isdigit()
    }, key=int)

    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    records: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(fetch_track, track_id, fetched_at, args.timeout, args.retries): track_id
            for track_id in track_ids
        }
        for future in as_completed(futures):
            track_id = futures[future]
            try:
                records[track_id] = future.result()
            except Exception as exc:  # defensive: preserve a visible failure instead of losing the batch
                records[track_id] = {
                    "trackId": track_id,
                    "publicUrl": PUBLIC_TEMPLATE.format(track_id=track_id),
                    "apiUrl": API_TEMPLATE.format(track_id=track_id),
                    "status": "error",
                    "fetchedAt": fetched_at,
                    "httpStatus": None,
                    "attempts": 0,
                    "error": str(exc),
                }

    ordered_records = {track_id: records[track_id] for track_id in track_ids}
    coverage = enrich_routes(routes_doc, ordered_records, fetched_at)
    metadata_doc = {
        "title": "מטא-דאטה מאומת לכל קישורי Off-Road בספר",
        "productVersion": PRODUCT_VERSION,
        "documentVersion": DOCUMENT_VERSION,
        "generatedAt": fetched_at,
        "source": "Off-Road public trackResult API",
        "policy": "הנתונים משקפים את מטא-דאטה של המקור בזמן המשיכה ואינם אישור תקינות, פתיחה, חוקיות, עבירות, בטיחות או התאמה לרוכב.",
        "counts": {
            "requested": len(track_ids),
            "verified": sum(item.get("status") == "verified" for item in ordered_records.values()),
            "unavailable": sum(item.get("status") == "unavailable" for item in ordered_records.values()),
            "errors": sum(item.get("status") == "error" for item in ordered_records.values()),
            "withDistance": sum(item.get("distanceKm") is not None for item in ordered_records.values()),
            "withDuration": sum(item.get("durationMs") is not None for item in ordered_records.values()),
            "withDifficulty": sum((item.get("difficultyLevel") or 0) > 0 for item in ordered_records.values()),
            "withActivity": sum(bool(item.get("activityType")) for item in ordered_records.values()),
        },
        "records": ordered_records,
    }

    json_text = json.dumps(metadata_doc, ensure_ascii=False, indent=2) + "\n"
    routes_path.write_text(json.dumps(routes_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "data" / "offroad-all-metadata.json").write_text(json_text, encoding="utf-8")
    js_text = (
        f"/* מטא-דאטה Off-Road — גרסת מסמך {DOCUMENT_VERSION}; גרסת מוצר {PRODUCT_VERSION} */\n"
        "window.OFFROAD_TRACK_METADATA = "
        + json.dumps(metadata_doc, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    (root / "data" / "offroad-all-metadata.js").write_text(js_text, encoding="utf-8")

    print(json.dumps({"counts": metadata_doc["counts"], "coverage": coverage}, ensure_ascii=True, indent=2))
    return 0 if metadata_doc["counts"]["errors"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
