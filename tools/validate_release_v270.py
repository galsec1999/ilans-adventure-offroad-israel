"""בדיקת מהדורת הניווט — גרסת מסמך 1.0.0; גרסת מוצר 2.7.0."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_VERSION = "2.7.0"
DOCUMENT_VERSION = "2.5.0"
ROUTES_DOCUMENT_VERSION = "2.3.0"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    manifest = load_json("manifest.webmanifest")
    routes_document = load_json("data/routes.json")
    navigation = load_json("data/navigation-supplements.json")
    metadata = load_json("data/offroad-all-metadata.json")
    geometry = load_json("data/offroad-geometry-audit.json")
    service_worker = (ROOT / "sw.js").read_text(encoding="utf-8")
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")

    routes = routes_document["routes"]
    require(len(routes) == 339, "route count must remain 339")
    require(len(re.findall(r'<details[^>]+class=["\'][^"\']*route-card', index)) == 339, "HTML card count must remain 339")
    require(index.count('class="export-html"') == 339, "every card must retain HTML export")
    require(f"גרסת מוצר {PRODUCT_VERSION}" in index, "visible product version missing")
    require(f"גרסת מסמך {DOCUMENT_VERSION}" in index, "visible document version missing")
    require(routes_document["documentVersion"] == ROUTES_DOCUMENT_VERSION, "routes document version mismatch")
    require(routes_document["productVersion"] == PRODUCT_VERSION, "routes product version mismatch")

    require(manifest["version"] == PRODUCT_VERSION, "manifest product version mismatch")
    require(manifest["document_version"] == DOCUMENT_VERSION, "manifest document version mismatch")
    require(manifest["start_url"] == "./" and manifest["scope"] == "./", "manifest must remain subpath safe")
    require(f"{PRODUCT_VERSION}-doc-{DOCUMENT_VERSION}" in service_worker, "service worker cache version mismatch")
    require("./data/navigation-supplements.json" in service_worker, "navigation data missing from app shell")

    summary = navigation["summary"]
    require(summary == {
        "reviewed": 59,
        "offRoad": 20,
        "routeFiles": 16,
        "googleRoadRoutes": 5,
        "googleAccessOnly": 17,
        "unresolved": 1,
    }, "navigation summary mismatch")
    require(len(navigation["records"]) == 59, "navigation audit must contain all 59 records")
    coverage = {kind: index.count(f'data-navigation-coverage="{kind}"') for kind in ("full-track", "road-route", "access-only", "none")}
    require(coverage == {"full-track": 36, "road-route": 5, "access-only": 17, "none": 1}, f"navigation panels mismatch: {coverage}")

    full_or_road = 0
    access_only = 0
    unresolved = 0
    offroad_cards = 0
    google_verified = 0
    file_verified = 0
    for route in routes:
        map_info = route.get("map", {})
        if map_info.get("hasMap"):
            offroad_cards += 1
        if map_info.get("hasDirections") and map_info.get("directionsStatus") == "verified":
            google_verified += 1
        if map_info.get("hasFileNavigation") and map_info.get("fileNavigationStatus") == "verified":
            file_verified += 1
        supplement = route.get("navigationSupplement", {})
        if map_info.get("hasMap") or (map_info.get("hasDirections") and map_info.get("directionsStatus") == "verified") or (map_info.get("hasFileNavigation") and map_info.get("fileNavigationStatus") == "verified"):
            full_or_road += 1
        elif supplement.get("coverage") == "access-only":
            access_only += 1
        else:
            unresolved += 1
    require((offroad_cards, google_verified, file_verified) == (296, 9, 16), "provider route counts mismatch")
    require((full_or_road, access_only, unresolved) == (321, 17, 1), "usable navigation counts mismatch")

    require(metadata["counts"] == {
        "requested": 307,
        "verified": 302,
        "unavailable": 5,
        "errors": 0,
        "withDistance": 302,
        "withDuration": 265,
        "withDifficulty": 248,
        "withActivity": 302,
    }, "Off-Road metadata counts mismatch")
    require(geometry["counts"]["totalTrackIds"] == 307, "geometry audit total mismatch")
    require(geometry["counts"]["geometry-verified"] == 296, "geometry verified count mismatch")
    require(geometry["counts"]["geometry-source-inconsistency"] == 6, "geometry inconsistency count mismatch")
    require(geometry["counts"]["source-unavailable"] == 5, "geometry unavailable count mismatch")

    local_file_count = 0
    official_external = []
    for record in navigation["records"]:
        if record["type"] != "route-file":
            continue
        url = record["url"]
        if url.startswith("./"):
            local_file_count += 1
            path = ROOT / url[2:]
            require(path.is_file() and path.stat().st_size > 0, f"missing route file: {url}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            require(digest == record.get("sha256"), f"route file digest mismatch: {url}")
        else:
            official_external.append(record["ordinal"])
            require("kkl.org.il" in url, f"external route file is not an official KKL source: {url}")
    require(local_file_count == 13, "expected 13 locally stored route files")
    require(official_external == [48, 49, 176], f"unexpected external route files: {official_external}")

    target_289 = next(route for route in routes if int(route["ordinal"]) == 289)
    require("2 שעות ו־45 דקות" in target_289.get("lengthTimeDisplay", ""), "route 289 duration was not corrected")
    require("טיוטה" in target_289.get("status", ""), "route 289 must remain an explicit draft")

    require('content="noindex,nofollow,noarchive,nosnippet"' in index, "noindex metadata missing")
    require("User-agent: *" in robots and "Disallow: /" in robots, "robots block missing")
    require(not (ROOT / "sitemap.xml").exists(), "sitemap must not exist")
    require("themeDarkButton" in index and "themeLightButton" in index, "light/dark controls missing")
    require("field-notes.js" in index and "visitCount" in index, "field notes or visit counter missing")
    require("עם תוואי או מפת גישה" in index and "ללא מפה שימושית" in index, "clear map filter labels missing")

    broken_images = []
    for source in re.findall(r'<img[^>]+src=["\']([^"\']+)', index):
        clean = source.split("?", 1)[0]
        if clean.startswith("./") and not (ROOT / clean[2:]).is_file():
            broken_images.append(source)
    require(not broken_images, f"broken local image references: {broken_images[:5]}")

    print(json.dumps({
        "status": "PASS",
        "productVersion": PRODUCT_VERSION,
        "documentVersion": DOCUMENT_VERSION,
        "routes": len(routes),
        "fullTrackOrRoadRoute": full_or_road,
        "accessOnly": access_only,
        "unresolved": unresolved,
        "locallyStoredRouteFiles": local_file_count,
        "officialExternalRouteFiles": official_external,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
