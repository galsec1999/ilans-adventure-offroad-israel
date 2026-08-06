"""שער איכות למטא-דאטה קשיח — גרסת מסמך 1.0.2; מוצר 2.3.0, מסמך ראשי 2.1.7."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path


PRODUCT_VERSION = "2.3.0"
MAIN_DOCUMENT_VERSION = "2.1.7"
DATA_DOCUMENT_VERSION = "2.1.6"
EXPECTED_CARDS = 339
EXPECTED_TRACK_CARDS = 276
EXPECTED_NAVIGATION_CARDS = 280
EXPECTED_TRACKS = 295
EXPECTED_VERIFIED_TRACKS = 290
EXPECTED_UNAVAILABLE_TRACKS = 5
TARGET_ROUTE_ID = "r-405491051a"
CARD_RE = re.compile(
    r'<details class="[^"]*\broute-card\b[^"]*" id="(?P<id>[^"]+)"[^>]*>(?P<body>.*?)</details>',
    re.DOTALL,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def km_text(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "מרחק לא צוין במקור"
    rendered = f"{number:.1f}".rstrip("0").rstrip(".")
    return f"{rendered} ק״מ"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    index = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "assets" / "js" / "app.js").read_text(encoding="utf-8")
    css = (root / "assets" / "css" / "app.css").read_text(encoding="utf-8")
    sw = (root / "sw.js").read_text(encoding="utf-8")
    manifest = json.loads((root / "manifest.webmanifest").read_text(encoding="utf-8"))
    routes_doc = json.loads((root / "data" / "routes.json").read_text(encoding="utf-8"))
    metadata = json.loads((root / "data" / "offroad-all-metadata.json").read_text(encoding="utf-8"))
    google = json.loads((root / "data" / "google-route-metadata.json").read_text(encoding="utf-8"))
    routes = {item["id"]: item for item in routes_doc["routes"]}
    cards = {match.group("id"): match.group("body") for match in CARD_RE.finditer(index)}

    check(len(cards) == EXPECTED_CARDS, "index contains exactly 339 route cards")
    check(routes_doc["productVersion"] == PRODUCT_VERSION, "routes dataset product version is 2.3.0")
    check(routes_doc["documentVersion"] == DATA_DOCUMENT_VERSION, "routes dataset document version is 2.1.6")
    check(metadata["productVersion"] == PRODUCT_VERSION, "Off-Road metadata product version is 2.3.0")
    check(metadata["documentVersion"] == DATA_DOCUMENT_VERSION, "Off-Road metadata document version is 2.1.6")
    check(f"גרסת מוצר {PRODUCT_VERSION}" in index, "main HTML displays product version 2.3.0")
    check(f"גרסת מסמך {MAIN_DOCUMENT_VERSION}" in index, "main HTML displays document version 2.1.7")
    check(manifest["version"] == PRODUCT_VERSION and manifest["document_version"] == MAIN_DOCUMENT_VERSION, "manifest versions are current")
    check("2.3.0-doc-2.1.7" in sw and "?v=2.1.7" in sw, "service worker cache is current")

    track_routes = [item for item in routes.values() if item.get("map", {}).get("trackIds")]
    check(len(track_routes) == EXPECTED_TRACK_CARDS, "276 cards retain Track IDs")
    check(index.count('data-map="1"') == EXPECTED_NAVIGATION_CARDS, "280 cards expose usable navigation")
    check(sum('data-source="offroad"' in cards[item["id"]] for item in track_routes) == EXPECTED_TRACK_CARDS, "all Track cards contain static Off-Road sections")
    check(index.count('class="source-fact-card') == EXPECTED_TRACKS + len(google["records"]), "HTML contains one static source card for every Off-Road and Google record")

    verified = [item for item in metadata["records"].values() if item["status"] == "verified"]
    unavailable = [item for item in metadata["records"].values() if item["status"] != "verified"]
    check(len(verified) == EXPECTED_VERIFIED_TRACKS, "290 Off-Road records are verified")
    check(len(unavailable) == EXPECTED_UNAVAILABLE_TRACKS, "five unavailable Off-Road records remain explicit")

    missing_static: list[str] = []
    for route in track_routes:
        body = html.unescape(cards[route["id"]])
        for track_id in map(str, route["map"]["trackIds"]):
            record = metadata["records"][track_id]
            expected = [record.get("title") or f"Track {track_id}"]
            if record["status"] == "verified":
                expected.extend([
                    km_text(record.get("distanceKm")),
                    record.get("durationDisplay") or "זמן לא צוין ב־Off-Road",
                    record.get("difficultyDisplay") or "לא דורג ב־Off-Road",
                ])
            if not all(str(value) in body for value in expected):
                missing_static.append(f"{route['id']}:{track_id}")
    check(not missing_static, "every linked Track has hard-coded title, distance, time state and difficulty state")

    normalized_from_source = [item for item in routes.values() if item.get("difficulty", {}).get("normalizationBasis") == "highest-rated-offroad-track"]
    check(len(normalized_from_source) == 62, "62 previously unverified difficulty filters are now sourced conservatively from Off-Road")
    check(all(item["difficulty"]["normalized"] in {"קל", "בינוני", "קשה"} for item in normalized_from_source), "source-derived filter values use valid categories")
    check(all("staticSourceMetadata" in item for item in track_routes), "routes dataset preserves static source payload for every Track card")

    verified_google = [item for item in google["records"].values() if item["status"] == "verified"]
    unavailable_google = [item for item in google["records"].values() if item["status"] != "verified"]
    check(len(verified_google) == 4 and len(unavailable_google) == 1, "four Google routes verified and one broken route preserved")
    check(all(routes[route_id]["map"].get("hasDirections") is True for route_id, item in google["records"].items() if item["status"] == "verified"), "verified Google routes are classified as usable navigation")
    for route_id, record in google["records"].items():
        body = html.unescape(cards[route_id])
        check('data-source="google"' in cards[route_id], f"{route_id} contains a static Google source section")
        if record["status"] == "verified":
            check(km_text(record["distanceKm"]) in body and record["durationDisplay"] in body, f"{route_id} contains verified Google distance and time")
        else:
            check(record["error"] in body and "לא הומצאו מרחק או זמן" in body, f"{route_id} exposes the broken Google route without fabricated values")

    target = html.unescape(cards[TARGET_ROUTE_ID])
    check("156 ק״מ" in target and "2 שעות ו-33 דקות" in target, "target Yakum route contains 156 km and 2h33m")
    check("קושי לא סופק במקור" in target, "target Yakum route explains why no difficulty is shown")
    check("<small>אורך / זמן</small><b>156 ק״מ · 2 שעות ו-33 דקות</b>" in target, "target Yakum metadata panel contains verified distance and time")
    check("Google Maps אינו מספק דירוג קושי" in target, "target Yakum metadata panel contains an explicit source limitation")
    check(routes[TARGET_ROUTE_ID]["distanceKm"] == 156.0, "target Yakum route dataset stores verified distance")
    check(routes[TARGET_ROUTE_ID]["lengthTimeDisplay"] == "156 ק״מ · 2 שעות ו-33 דקות", "target Yakum route dataset stores verified duration")
    check(re.search(rf'id="{TARGET_ROUTE_ID}"[^>]*data-map="1"', index) is not None and "Google Maps מאומת" in target, "target Yakum route is marked as usable Google navigation")

    check('.source-facts-static[data-source="offroad"]' in app, "runtime enrichment skips already materialized Off-Road cards")
    check("source-facts-static" in css and "source-facts-grid" in css, "static source cards have responsive styling")
    check("clone.innerHTML" in app and "כל פרטי הכרטיס" in app, "single-trip HTML export includes the materialized card body")
    check('a[href*="google.com/maps/dir/"]' in app and "פתיחת המסלול ב־Google Maps" in app, "single-trip HTML export retains verified Google navigation")
    check("apiKey" not in app and "API_KEY" not in app, "AI remains keyless")
    check('<meta name="robots" content="noindex,nofollow,noarchive,nosnippet">' in index, "noindex policy remains in main HTML")
    check(re.search(r"User-agent:\s*\*\s*Disallow:\s*/", (root / "robots.txt").read_text(encoding="utf-8")) is not None, "robots.txt still disallows crawling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
