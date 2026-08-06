"""בדיקות השלמת מטא-דאטה Off-Road — גרסת מסמך 2.1.6; גרסת מוצר 2.2.0."""

from __future__ import annotations

import json
import re
from pathlib import Path


DATA_DOCUMENT_VERSION = "2.1.5"
SITE_DOCUMENT_VERSION = "2.1.6"
EXPECTED_CARDS = 339
EXPECTED_TRACK_IDS = 295


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    routes = json.loads((root / "data" / "routes.json").read_text(encoding="utf-8"))
    metadata = json.loads((root / "data" / "offroad-all-metadata.json").read_text(encoding="utf-8"))
    metadata_js = (root / "data" / "offroad-all-metadata.js").read_text(encoding="utf-8")
    index = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "assets" / "js" / "app.js").read_text(encoding="utf-8")
    service_worker = (root / "sw.js").read_text(encoding="utf-8")
    manifest = json.loads((root / "manifest.webmanifest").read_text(encoding="utf-8"))

    records = metadata["records"]
    route_items = routes["routes"]
    all_route_track_ids = {
        str(track_id)
        for route in route_items
        for track_id in (route.get("map", {}).get("trackIds") or [])
    }
    cards_with_tracks = [route for route in route_items if route.get("map", {}).get("trackIds")]
    unavailable = [record for record in records.values() if record["status"] == "unavailable"]
    errors = [record for record in records.values() if record["status"] == "error"]
    verified = [record for record in records.values() if record["status"] == "verified"]
    missing_single_distance = []
    for route in cards_with_tracks:
        ids = [str(item) for item in route["map"]["trackIds"]]
        successful = [records[item] for item in ids if records[item]["status"] == "verified"]
        if len(ids) == 1 and len(successful) == 1 and successful[0].get("distanceKm") is not None and route.get("distanceKm") is None:
            missing_single_distance.append(route["id"])

    check(routes["documentVersion"] == DATA_DOCUMENT_VERSION, "unchanged routes dataset retains document version 2.1.5")
    check(metadata["documentVersion"] == DATA_DOCUMENT_VERSION, "unchanged metadata dataset retains document version 2.1.5")
    check(len(route_items) == EXPECTED_CARDS, "route count remains exactly 339")
    check(len(cards_with_tracks) == 276, "276 cards retain Off-Road track links")
    check(len(all_route_track_ids) == EXPECTED_TRACK_IDS, "295 unique Off-Road track IDs are represented")
    check(set(records) == all_route_track_ids, "metadata covers every linked track ID and no unrelated ID")
    check(len(records) == EXPECTED_TRACK_IDS, "metadata contains exactly 295 records")
    check(len(verified) == 290, "290 Off-Road records verified")
    check(len(unavailable) == 5, "five unavailable records preserved explicitly")
    check(not errors, "no metadata fetch errors remain")
    check(all(record.get("distanceKm") is not None for record in verified), "every verified record has source distance")
    check(not missing_single_distance, "single-track cards inherit verified distance when missing")
    check(metadata_js.startswith("/* מטא-דאטה Off-Road — גרסת מסמך 2.1.5"), "metadata JavaScript shows document version")
    check("window.OFFROAD_TRACK_METADATA = " in metadata_js, "metadata JavaScript exposes the static dataset")
    check(index.find("offroad-all-metadata.js") < index.find("assets/js/app.js"), "metadata loads before app logic")
    check(index.count('class="route-card') == EXPECTED_CARDS, "static HTML still contains 339 route cards")
    check(f"גרסת מסמך {SITE_DOCUMENT_VERSION}" in index, "main HTML displays document version 2.1.6")
    check('<meta name="robots" content="noindex,nofollow,noarchive,nosnippet">' in index, "main HTML retains noindex policy")
    check("offroad-source-data" in app and "offroadTrackSummaries" in app, "app renders and exports source metadata")
    check("📊 נתוני Off‑Road מן ההקלטה" in app, "WhatsApp invitation includes source metadata")
    check("offroadTrackMetadata:data.offroadTracks" in app, "AI prompt receives source metadata")
    check("offroad-all-metadata.js" in service_worker and SITE_DOCUMENT_VERSION in service_worker, "service worker caches metadata with the current site cache version")
    check(manifest["document_version"] == SITE_DOCUMENT_VERSION, "manifest document version is 2.1.6")
    check(re.search(r"User-agent:\s*\*\s*Disallow:\s*/", (root / "robots.txt").read_text(encoding="utf-8")) is not None, "robots.txt still disallows crawling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
