"""שילוב אימות תוואי ונקודות ציון בספר — גרסת מסמך 1.1.0; מוצר 2.7.0."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


PRODUCT_VERSION = "2.7.0"
MAIN_DOCUMENT_VERSION = "2.5.0"
ROUTES_DOCUMENT_VERSION = "2.3.0"
CARD_RE = re.compile(
    r'<details class="(?P<class>[^"]*\broute-card\b[^"]*)" id="(?P<id>[^"]+)"(?P<attrs>[^>]*)>(?P<body>.*?)</details>',
    re.DOTALL,
)


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def one_search_attr(opening: str, reliable_search: str, *, replace_existing: bool) -> str:
    pattern = re.compile(r"\sdata-search=(['\"])(.*?)\1", re.DOTALL)
    existing = next((" ".join(html.unescape(match.group(2)).split()) for match in pattern.finditer(opening)), "")
    opening = pattern.sub("", opening)
    opening = re.sub(r'\sdata-geometry-audited=(?:"[^"]*"|\'[^\']*\')', "", opening)
    combined = " ".join(reliable_search.split()) if replace_existing else existing
    suffix = ' data-geometry-audited="true"' if replace_existing else ""
    opening = opening[:-1] + f' data-search="{esc(combined)}"{suffix}>'
    return opening


def osm_url(place: dict) -> str:
    osm_type = {"node": "node", "way": "way", "relation": "relation"}.get(place.get("osmType"), "")
    return f"https://www.openstreetmap.org/{osm_type}/{place.get('osmId')}" if osm_type and place.get("osmId") else "https://www.openstreetmap.org/"


def geometry_panel(records: list[dict]) -> str:
    opened = [record for record in records if record.get("status") in {"geometry-verified", "geometry-source-inconsistency"}]
    if not opened:
        reason = " · ".join(str(record.get("reason") or "שכבת התוואי אינה זמינה") for record in records)
        return (
            '<div class="geometry-verification unavailable"><h3>בדיקת תוואי המפה בפועל</h3>'
            f'<p><b>לא ניתן לפתוח את שכבת התוואי:</b> {esc(reason)}</p>'
            '<p>הכרטיס אינו מוצג כאילו התוואי אומת; אין להשלים נקודות ציון בניחוש.</p></div>'
        )
    rows = []
    for index, record in enumerate(opened, 1):
        points = record.get("pointCount")
        length = record.get("calculatedGeometryLengthKm")
        source_length = record.get("sourceDistanceKm")
        places = record.get("verifiedNearbyPlaces") or []
        place_links = " · ".join(
            f'<a href="{esc(osm_url(place))}" target="_blank" rel="noopener">{esc(place.get("name"))}</a> '
            f'<small>({place.get("distanceFromTrackM")} מ׳ מן הקו)</small>'
            for place in places
        ) or "לא נמצאו שמות ממופים סמוכים בתנאי הסף"
        rows.append(
            '<article class="geometry-track">'
            f'<h4>הקלטה {index} · Track {esc(record.get("trackId"))}</h4>'
            + (f'<p class="geometry-warning"><b>סתירה פנימית במקור לאחר פתיחת הקורס המלא:</b> {esc(record.get("reason"))}</p>' if record.get("status") == "geometry-source-inconsistency" else '')
            +
            f'<p><b>שכבת המפה נפתחה:</b> {points:,} נקודות תוואי; אורך גאומטרי {length:g} ק״מ'
            + (f' לעומת {source_length:g} ק״מ במטא־דאטה.' if source_length else ".")
            + f' סטיית התחלה {record.get("sourceStartDeltaM")} מ׳ וסטיית סיום {record.get("sourceEndDeltaM")} מ׳.</p>'
            f'<p><b>שמות ממופים סמוך לתוואי:</b> {place_links}</p></article>'
        )
    return (
        '<div class="geometry-verification"><h3>אימות תוואי המפה בפועל</h3>'
        + "".join(rows)
        + '<p class="source-facts-note">השמות נלקחו מ־OpenStreetMap לפי מרחק מדוד מן הקו: יישוב עד 1,200 מ׳; אתר טבע, מים, תצפית, שמורה או אתר היסטורי עד 450 מ׳. קרבה אינה הוכחה שהמסלול נכנס לאתר.</p></div>'
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    routes_path = root / "data" / "routes.json"
    routes_doc = json.loads(routes_path.read_text(encoding="utf-8"))
    geometry_doc = json.loads((root / "data" / "offroad-geometry-audit.json").read_text(encoding="utf-8"))
    geometry = {str(record["trackId"]): record for record in geometry_doc["tracks"]}
    route_by_id = {route["id"]: route for route in routes_doc["routes"]}

    for route in routes_doc["routes"]:
        track_ids = [str(value) for value in route.get("map", {}).get("trackIds") or []]
        records = [geometry[track_id] for track_id in track_ids if track_id in geometry]
        if not records:
            continue
        places: dict[str, dict] = {}
        for record in records:
            for place in record.get("verifiedNearbyPlaces") or []:
                key = str(place.get("name") or "").casefold()
                if key and (key not in places or place["distanceFromTrackM"] < places[key]["distanceFromTrackM"]):
                    places[key] = place
        trust = route.setdefault("trustAudit", {})
        if all(record.get("status") == "geometry-verified" for record in records):
            trust["geometryStatus"] = "verified"
        elif any(record.get("status") == "geometry-source-inconsistency" for record in records):
            trust["geometryStatus"] = "source-inconsistency"
        else:
            trust["geometryStatus"] = "unavailable"
        trust["geometryTracks"] = [{key: record.get(key) for key in ("trackId", "status", "pointCount", "boundingBox", "calculatedGeometryLengthKm", "sourceDistanceKm", "distanceDeltaPercent", "sourceStartDeltaM", "sourceEndDeltaM")} for record in records]
        trust["verifiedNearbyPlaces"] = sorted(places.values(), key=lambda place: (place["distanceFromTrackM"], place["name"]))
        trust["geometryPolicy"] = "שמות מקום נוספו רק מישויות OpenStreetMap שנמצאו במרחק מדוד משכבת התוואי שנפתחה מ-Off-Road."

    routes_doc["documentVersion"] = ROUTES_DOCUMENT_VERSION
    routes_doc["title"] = f"נתוני ספר המסלולים — גרסת מסמך {ROUTES_DOCUMENT_VERSION}"
    routes_doc["routeGeometryAudit"] = {
        "documentVersion": geometry_doc["title"].split()[-1],
        "geometryVerified": geometry_doc["counts"].get("geometry-verified", 0),
        "sourceInconsistency": geometry_doc["counts"].get("geometry-source-inconsistency", 0),
        "sourceUnavailable": geometry_doc["counts"].get("source-unavailable", 0),
        "tracksWithNearbyPlaces": geometry_doc["counts"].get("tracksWithNearbyPlaces", 0),
    }
    routes_path.write_text(json.dumps(routes_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    index_path = root / "index.html"
    source = index_path.read_text(encoding="utf-8")

    def replace_card(match: re.Match[str]) -> str:
        route = route_by_id.get(match.group("id"))
        if not route:
            return match.group(0)
        track_ids = [str(value) for value in route.get("map", {}).get("trackIds") or []]
        records = [geometry[track_id] for track_id in track_ids if track_id in geometry]
        opening = f'<details class="{match.group("class")}" id="{match.group("id")}"{match.group("attrs")}>'
        trust = route.get("trustAudit") or {}
        places = trust.get("verifiedNearbyPlaces") or []
        archived = trust.get("archivedClassification") or {}
        reliable_search = " ".join(
            str(value or "")
            for value in (
                route.get("title"), trust.get("canonicalTitle"), trust.get("canonicalDescription"),
                trust.get("sourceSearchText"), route.get("region"), route.get("subregion"),
                (route.get("difficulty") or {}).get("normalized"), route.get("shape"),
                " ".join(route.get("surfaces") or []), " ".join(trust.get("sourcePlaceMentions") or []),
                " ".join(str(place.get("name") or "") for place in places), archived.get("title"),
            )
        )
        opening = one_search_attr(opening, reliable_search, replace_existing=bool(records))
        body = re.sub(r'<div class="geometry-verification(?: unavailable)?">.*?</div>', "", match.group("body"), flags=re.DOTALL)
        if records:
            marker = re.search(r'<h3>נתוני Off‑Road קשיחים(?: לכל ההקלטות)?</h3>', body)
            if not marker:
                raise RuntimeError(f"source metadata marker missing in {route['id']}")
            body = body[:marker.start()] + geometry_panel(records) + body[marker.start():]
        return opening + body + "</details>"

    source, card_count = CARD_RE.subn(replace_card, source)
    if card_count != 339:
        raise RuntimeError(f"expected 339 cards, found {card_count}")
    source = source.replace("גרסת מסמך 2.3.1", f"גרסת מסמך {MAIN_DOCUMENT_VERSION}")
    source = source.replace("?v=2.3.1", f"?v={MAIN_DOCUMENT_VERSION}")
    source = source.replace("מטמון 2.3.1", f"מטמון {MAIN_DOCUMENT_VERSION}")
    index_path.write_text(source, encoding="utf-8")

    manifest_path = root / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["name"] = f"ספר מסלולי האדוונצ׳ר והאופרוד בישראל של אילן · גרסת מסמך {MAIN_DOCUMENT_VERSION}"
    manifest["document_version"] = MAIN_DOCUMENT_VERSION
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for relative in ("offline.html", "assets/js/app.js", "assets/css/app.css"):
        path = root / relative
        text = path.read_text(encoding="utf-8").replace("גרסת מסמך 2.3.1", f"גרסת מסמך {MAIN_DOCUMENT_VERSION}").replace("?v=2.3.1", f"?v={MAIN_DOCUMENT_VERSION}")
        path.write_text(text, encoding="utf-8")
    sw_path = root / "sw.js"
    sw = sw_path.read_text(encoding="utf-8").replace("2.5.0-doc-2.3.1", f"2.5.0-doc-{MAIN_DOCUMENT_VERSION}").replace("גרסת מסמך 2.3.1", f"גרסת מסמך {MAIN_DOCUMENT_VERSION}").replace("?v=2.3.1", f"?v={MAIN_DOCUMENT_VERSION}")
    if "./data/offroad-geometry-audit.json" not in sw:
        sw = sw.replace("'./data/route-map-trust-audit.json'", "'./data/route-map-trust-audit.json','./data/offroad-geometry-audit.json'")
    sw_path.write_text(sw, encoding="utf-8")

    css_path = root / "assets" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    if ".geometry-verification{" not in css:
        css += "\n.geometry-verification{margin:14px 0;padding:14px;border:1px solid var(--line);border-radius:12px;background:color-mix(in srgb,var(--accent) 8%,var(--surface))}.geometry-verification h3,.geometry-verification h4{margin-top:0}.geometry-track+ .geometry-track{border-top:1px solid var(--line);padding-top:12px}.geometry-verification a{font-weight:700}.geometry-verification small{white-space:nowrap}.geometry-verification.unavailable{border-color:var(--warning)}\n"
    css_path.write_text(css, encoding="utf-8")

    audit_path = root / "data" / "route-map-trust-audit.json"
    audit_doc = json.loads(audit_path.read_text(encoding="utf-8"))
    audit_doc["title"] = "ביקורת התאמת כרטיס–מפה לכל מסלולי הספר — גרסת מסמך 1.0.1"
    audit_doc["routesDocumentVersion"] = ROUTES_DOCUMENT_VERSION
    audit_doc["geometryAudit"] = geometry_doc["counts"]
    audit_path.write_text(json.dumps(audit_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cards": card_count, "routesDocumentVersion": ROUTES_DOCUMENT_VERSION, "mainDocumentVersion": MAIN_DOCUMENT_VERSION, "geometryVerified": geometry_doc["counts"].get("geometry-verified")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
