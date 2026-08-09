"""שער אמינות כרטיס–מפה 2.5.0 — גרסת מסמך 1.0.2; מסמך אתר 2.3.3."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CARD_RE = re.compile(
    r'<details class="(?P<class>[^"]*\broute-card\b[^"]*)" id="(?P<id>[^"]+)"(?P<attrs>[^>]*)>(?P<body>.*?)</details>',
    re.DOTALL,
)


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(f"FAIL: {label}")
    print(f"PASS: {label}")


def record_text(record: dict[str, Any]) -> str:
    return " ".join(str(record.get(key) or "") for key in ("title", "shortDescription", "description"))


def main() -> int:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "assets" / "css" / "app.css").read_text(encoding="utf-8")
    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))
    routes_doc = json.loads((ROOT / "data" / "routes.json").read_text(encoding="utf-8"))
    metadata_doc = json.loads((ROOT / "data" / "offroad-all-metadata.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "data" / "route-map-trust-audit.json").read_text(encoding="utf-8"))
    routes = {item["id"]: item for item in routes_doc["routes"]}
    metadata = metadata_doc["records"]
    cards = {match.group("id"): (match.group("attrs"), match.group("body")) for match in CARD_RE.finditer(index)}

    require(routes_doc["productVersion"] == "2.5.0" and routes_doc["documentVersion"] == "2.2.2", "routes dataset versions")
    require(metadata_doc["productVersion"] == "2.5.0" and metadata_doc["documentVersion"] == "2.2.0", "Off-Road metadata versions")
    require(audit["productVersion"] == "2.5.0" and audit["routesDocumentVersion"] == "2.2.2", "alignment audit versions")
    require(manifest["version"] == "2.5.1" and manifest["document_version"] == "2.3.3", "manifest versions")
    require("גרסת מוצר 2.5.1" in index and "גרסת מסמך 2.3.3" in index, "visible main versions")
    require("2.5.1-doc-2.3.3" in sw and "./data/route-map-trust-audit.json" in sw, "PWA cache includes trust audit")
    require(len(routes) == len(cards) == 339, "339 route cards remain intact")

    expected_counts = {
        "total": 339,
        "verified-source-aligned": 260,
        "multiple-source-maps": 12,
        "google-source-aligned": 4,
        "no-map-to-compare": 58,
        "source-unavailable": 5,
    }
    require(audit["counts"] == expected_counts, "all 339 cards have a one-by-one alignment result")
    entries = audit["entries"]
    require(len(entries) == 339 and {item["routeId"] for item in entries} == set(routes), "audit entry exists for every route")

    verified_records = [item for item in metadata.values() if item.get("status") == "verified"]
    require(len(metadata) == 295 and len(verified_records) == 290, "all 295 Track IDs refreshed; 290 verified")
    require(all(item.get("area") and item.get("start") and item.get("end") for item in verified_records), "verified tracks include source area and endpoints")

    track_routes = [item for item in routes.values() if item.get("map", {}).get("trackIds")]
    require(len(track_routes) == 276, "276 cards with Off-Road maps audited")
    single_verified = 0
    place_cards = 0
    for route in track_routes:
        ids = [str(value) for value in route["map"]["trackIds"]]
        source_records = [metadata[value] for value in ids]
        verified = [item for item in source_records if item.get("status") == "verified"]
        trust = route.get("trustAudit") or {}
        attrs, body = cards[route["id"]]
        require(bool(trust.get("canonicalTitle")), f"{route['id']} has canonical map title")
        require('data-canonical-title="' in attrs, f"{route['id']} exposes canonical title to runtime")
        require('class="source-alignment"' in body, f"{route['id']} shows map alignment evidence")
        require("השם המחייב להזמנה ולייצוא" in body, f"{route['id']} labels authoritative title")
        require(all(html.escape(str(item.get("title") or f"Track {item['trackId']}"), quote=True) in body for item in source_records), f"{route['id']} retains every source map title")
        for mention in trust.get("sourcePlaceMentions") or []:
            normalized_source = " ".join(" ".join(record_text(item) for item in verified).split())
            mention_tokens = set(re.findall(r"[א-תa-z]+", mention.lower()))
            source_tokens = set(re.findall(r"[א-תa-z]+", normalized_source.lower()))
            require(bool(mention_tokens) and mention_tokens <= source_tokens, f"{route['id']} landmark uses source words only")
        if trust.get("sourcePlaceMentions"):
            place_cards += 1
        if len(ids) == 1 and len(verified) == 1:
            single_verified += 1
            require(route["title"] == trust["canonicalTitle"], f"{route['id']} primary title matches its only map")
            require(html.escape(route["title"], quote=True) in body, f"{route['id']} visible title matches source map")
        if verified:
            require(route.get("difficulty", {}).get("normalizationBasis") == "offroad-track-source", f"{route['id']} difficulty filter is source based")
            require(route.get("shape") in {"מעגלי", "קווי / חד־כיווני", "מספר חלופות", "לא צוין"}, f"{route['id']} route shape is source based")
            require(set(route.get("surfaces") or []) <= {"לא צוין", "חול", "בוץ", "סלעים", "כורכר", "כביש"}, f"{route['id']} surface filter is conservative")

    require(single_verified == 260, "260 single-map cards use their exact source title")
    require(place_cards >= 150, "at least 150 map cards expose explicit source place terms")
    require(index.count('class="source-coordinates"') == 290, "every verified Track shows source endpoints")

    known_repairs = {
        "r-c20c0c5507": ("לטרון - דרך נוף צרעה - תל גזר - בית הקשתות", "מרכז"),
        "r-32ce4f24bb": ('לא שלי סינגל מעגלי ליידו שביל קק"ל איזור פורה קליל', "דרום ומדבר"),
        "r-df98cfab89": ("חורשן כרמל טכני", "צפון"),
        "r-c4dd975d24": ("אלכס ונתן סדום", "דרום ומדבר"),
        "r-60daa2e1b7": ("ירקון 05/05/2026 גדה דרומית רמת החייל למקורות הירקון", "מרכז"),
    }
    for route_id, (title, region) in known_repairs.items():
        require(routes[route_id]["title"] == title and routes[route_id]["region"] == region, f"known mismatch repaired: {route_id}")

    require('id="invite-map-select"' in index and "בכרטיס עם כמה מפות" in index, "multi-map invitation requires explicit map selection")
    require("function invitationRouteData(card)" in app, "invitation has a selected-map data model")
    require("const data = invitationRouteData(card);" in app, "rich and short invitations use selected-map data")
    require("mapUrls:[selected.url]" in app and "qrUrl:selected.qrUrl" in app, "invitation text and QR are bound to one selected map")
    require("canonicalDescription" in app and "sourceDescription(record)" in app, "invitation description comes from selected source")
    require(".source-alignment{" in css and ".route-trust-release{" in css, "alignment evidence has responsive visual styling")
    require("noindex,nofollow,noarchive,nosnippet" in index, "noindex policy remains")
    require((ROOT / "robots.txt").read_text(encoding="utf-8").replace("\r\n", "\n") == "User-agent: *\nDisallow: /\n", "robots policy remains")
    require(not list(ROOT.glob("**/sitemap*")), "no sitemap was created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
