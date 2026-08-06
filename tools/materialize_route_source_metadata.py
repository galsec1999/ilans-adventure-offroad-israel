"""הקשחת מטא-דאטה של מקורות לתוך ספר המסלולים — גרסת מסמך 1.0.6; גרסת מוצר 2.3.0."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


PRODUCT_VERSION = "2.3.0"
MAIN_DOCUMENT_VERSION = "2.1.7"
ROUTES_DOCUMENT_VERSION = "2.1.6"
CARD_RE = re.compile(
    r'<details class="(?P<class>[^"]*\broute-card\b[^"]*)" id="(?P<id>[^"]+)"(?P<attrs>[^>]*)>(?P<body>.*?)</details>',
    re.DOTALL,
)
GOOGLE_DIRECTIONS_RE = re.compile(r'href="([^"]*google\.com/maps/dir/\?api=1[^"]*)"')
STATIC_SECTION_RE = re.compile(r'<section class="source-facts-static".*?</section>\s*', re.DOTALL)
STATIC_CHIP_RE = re.compile(r'<span class="source-(?:offroad|google)-chip">.*?</span>', re.DOTALL)


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def km_text(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "מרחק לא צוין במקור"
    if number <= 0:
        return "מרחק לא צוין במקור"
    rendered = f"{number:.1f}".rstrip("0").rstrip(".")
    return f"{rendered} ק״מ"


def duration_text(record: dict[str, Any]) -> str:
    return str(record.get("durationDisplay") or "זמן לא צוין ב־Off-Road")


def difficulty_text(record: dict[str, Any]) -> str:
    return str(record.get("difficultyDisplay") or "לא דורג ב־Off-Road")


def source_level(record: dict[str, Any]) -> int:
    try:
        return int(record.get("difficultyLevel") or 0)
    except (TypeError, ValueError):
        return 0


def normalized_difficulty(records: list[dict[str, Any]]) -> str | None:
    levels = [source_level(item) for item in records if source_level(item) > 0]
    if not levels:
        return None
    highest = max(levels)
    if highest >= 4:
        return "קשה"
    if highest >= 2:
        return "בינוני"
    return "קל"


def set_attr(opening: str, name: str, value: str) -> str:
    escaped = esc(value)
    pattern = re.compile(rf'\s{name}="[^"]*"')
    if pattern.search(opening):
        return pattern.sub(f' {name}="{escaped}"', opening, count=1)
    return opening[:-1] + f' {name}="{escaped}">'


def add_search_text(opening: str, value: str) -> str:
    match = re.search(r'\sdata-search="([^"]*)"', opening)
    if not match:
        return set_attr(opening, "data-search", value)
    current = html.unescape(match.group(1))
    if value in current:
        return opening
    return set_attr(opening, "data-search", f"{current} {value}".strip())


def add_summary(body: str, summary: str, chip_class: str) -> str:
    body = STATIC_CHIP_RE.sub("", body)
    facts_re = re.compile(r'(<span class="summary-facts">)(.*?)(</span>)', re.DOTALL)
    facts = facts_re.search(body)
    if facts and summary not in html.unescape(facts.group(2)):
        body = facts_re.sub(
            lambda item: f"{item.group(1)}{item.group(2)} · {esc(summary)}{item.group(3)}",
            body,
            count=1,
        )
    chips_re = re.compile(r'(<span class="chips">.*?)(</span>\s*</summary>)', re.DOTALL)
    if chips_re.search(body):
        body = chips_re.sub(
            lambda item: f'{item.group(1)}<span class="{chip_class}">{esc(summary)}</span>{item.group(2)}',
            body,
            count=1,
        )
    return body


def replace_visible_difficulty(body: str, old_value: str, new_value: str) -> str:
    if old_value not in {"", "לא אומת", "לא צוין"}:
        return body
    facts_re = re.compile(r'(<span class="summary-facts">)(.*?)(</span>)', re.DOTALL)
    facts = facts_re.search(body)
    if facts:
        content = facts.group(2)
        for missing in ("לא אומת", "לא צוין"):
            content = content.replace(f" · {missing}", f" · {esc(new_value)}", 1)
        body = body[:facts.start(2)] + content + body[facts.end(2):]
    for missing in ("לא אומת", "לא צוין"):
        body = body.replace(f"<span>{missing}</span>", f"<span>{esc(new_value)}</span>", 1)
    return body


def replace_navigation_chip(body: str, label: str, css_class: str) -> str:
    chip_re = re.compile(r'<span class="(?:no-map|has-map)">.*?</span>')
    return chip_re.sub(f'<span class="{css_class}">{esc(label)}</span>', body, count=1)


def replace_meta_value(body: str, label: str, value: str) -> str:
    pattern = re.compile(rf'(<div><small>{re.escape(label)}</small><b>).*?(</b></div>)', re.DOTALL)
    return pattern.sub(lambda item: f'{item.group(1)}{esc(value)}{item.group(2)}', body, count=1)


def inject_before_marketing(body: str, section: str) -> str:
    body = STATIC_SECTION_RE.sub("", body)
    marker = '<section class="marketing">'
    if marker not in body:
        raise ValueError("route card has no marketing section")
    return body.replace(marker, section + "\n" + marker, 1)


def offroad_section(records: list[dict[str, Any]]) -> tuple[str, str]:
    verified = [item for item in records if item.get("status") == "verified"]
    rows: list[str] = []
    for index, record in enumerate(records, start=1):
        title = record.get("title") or f"Track {record.get('trackId')}"
        url = record.get("publicUrl") or f"https://off-road.io/track/{record.get('trackId')}"
        if record.get("status") == "verified":
            facts = [
                km_text(record.get("distanceKm")),
                duration_text(record),
                difficulty_text(record),
                str(record.get("activityDisplay") or "פעילות לא צוינה במקור"),
            ]
            status = "נתונים שנשמרו ממקור Off‑Road"
            css_class = "verified"
        else:
            facts = ["הנתונים אינם זמינים כעת ב־Off‑Road"]
            status = "הקישור נשמר לבדיקה ידנית"
            css_class = "unavailable"
        rows.append(
            f'<article class="source-fact-card {css_class}"><h4>הקלטה {index}: '
            f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(title)}</a></h4>'
            f'<p>{" · ".join(esc(item) for item in facts)}</p><small>{esc(status)}</small></article>'
        )
    if len(records) == 1 and verified:
        primary = verified[0]
        summary = f"Off‑Road: {km_text(primary.get('distanceKm'))} · {duration_text(primary)} · {difficulty_text(primary)}"
    elif verified:
        distances = " / ".join(km_text(item.get("distanceKm")) for item in verified)
        summary = f"Off‑Road: {len(records)} הקלטות · {distances}; פירוט מלא בכרטיס"
    else:
        summary = f"Off‑Road: {len(records)} קישורים ללא נתונים זמינים"
    heading = "נתוני Off‑Road קשיחים לכל ההקלטות" if len(records) > 1 else "נתוני Off‑Road קשיחים"
    section = (
        f'<section class="source-facts-static" data-source="offroad"><h3>{heading}</h3>'
        f'<div class="source-facts-grid">{"".join(rows)}</div>'
        '<p class="source-facts-note">הנתונים הועתקו ממטא־דאטה של המקור ונשמרו ב־HTML. '
        'הם אינם אישור שהמסלול פתוח, חוקי, עביר, בטוח או מתאים לקבוצה.</p></section>'
    )
    return section, summary


def google_section(record: dict[str, Any]) -> tuple[str, str]:
    distance = km_text(record.get("distanceKm"))
    duration = str(record.get("durationDisplay") or "זמן לא צוין ב־Google Maps")
    route_label = str(record.get("routeLabel") or "מסלול נהיגה לפי סדר התחנות שבקישור")
    warning = str(record.get("warning") or "")
    warning_html = f'<p class="source-fact-warning">{esc(warning)}</p>' if warning else ""
    summary = f"Google Maps: {distance} · {duration}"
    section = (
        '<section class="source-facts-static" data-source="google"><h3>נתוני מסלול Google Maps שנבדקו</h3>'
        '<div class="source-facts-grid"><article class="source-fact-card verified">'
        f'<h4><a href="{esc(record.get("url"))}" target="_blank" rel="noopener">{esc(route_label)}</a></h4>'
        f'<p>{esc(distance)} · {esc(duration)} · נהיגה</p>'
        f'<small>נבדק ב־Google Maps בתאריך {esc(record.get("verifiedAt"))}; זמן הנסיעה עשוי להשתנות לפי תנועה וחסימות.</small>'
        f'</article>{warning_html}</div></section>'
    )
    return section, summary


def google_unavailable_section(record: dict[str, Any]) -> tuple[str, str]:
    summary = "Google Maps: הקישור אינו מפיק מסלול תקין"
    section = (
        '<section class="source-facts-static" data-source="google"><h3>בדיקת מסלול Google Maps</h3>'
        '<div class="source-facts-grid"><article class="source-fact-card unavailable">'
        f'<h4><a href="{esc(record.get("url"))}" target="_blank" rel="noopener">הקישור המקורי</a></h4>'
        f'<p>{esc(record.get("error") or "לא התקבלה תוצאת מסלול תקינה")}</p>'
        f'<small>נבדק בתאריך {esc(record.get("verifiedAt"))}; לא הומצאו מרחק או זמן.</small>'
        '</article></div></section>'
    )
    return section, summary


def route_static_payload(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = (
        "trackId", "publicUrl", "status", "title", "distanceKm", "durationMs",
        "durationDisplay", "difficultyLevel", "difficultyDisplay", "activityType",
        "activityDisplay", "updated", "httpStatus",
    )
    return [{key: item.get(key) for key in keys} for item in records]


def materialize(root: Path) -> dict[str, int]:
    index_path = root / "index.html"
    routes_path = root / "data" / "routes.json"
    metadata_path = root / "data" / "offroad-all-metadata.json"
    google_path = root / "data" / "google-route-metadata.json"
    index = index_path.read_text(encoding="utf-8")
    routes_doc = json.loads(routes_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))["records"]
    google_records = json.loads(google_path.read_text(encoding="utf-8"))["records"] if google_path.exists() else {}
    routes = {item["id"]: item for item in routes_doc["routes"]}
    counts = {"cards": 0, "offroad": 0, "google": 0, "googleUnavailable": 0, "verifiedTracks": 0, "unavailableTracks": 0}

    def replace_card(match: re.Match[str]) -> str:
        route_id = match.group("id")
        route = routes.get(route_id)
        if route is None:
            raise ValueError(f"route {route_id} missing from routes.json")
        opening = f'<details class="{match.group("class")}" id="{route_id}"{match.group("attrs")}>'
        body = match.group("body")
        track_ids = [str(item) for item in (route.get("map", {}).get("trackIds") or [])]
        records = [metadata.get(track_id, {"trackId": track_id, "status": "missing"}) for track_id in track_ids]
        google_record = google_records.get(route_id)
        if records:
            section, summary = offroad_section(records)
            body = inject_before_marketing(body, section)
            body = add_summary(body, summary, "source-offroad-chip")
            verified = [item for item in records if item.get("status") == "verified"]
            counts["offroad"] += 1
            counts["verifiedTracks"] += len(verified)
            counts["unavailableTracks"] += len(records) - len(verified)
            route["staticSourceMetadata"] = {"source": "Off-Road", "records": route_static_payload(records)}
            primary = verified[0] if verified else None
            if primary and primary.get("distanceKm") is not None:
                opening = set_attr(opening, "data-distance", str(primary["distanceKm"]))
                opening = set_attr(opening, "data-distance-basis", "primary-offroad-track")
                if len(records) == 1:
                    route["distanceKm"] = primary["distanceKm"]
                    route["lengthTimeDisplay"] = f"{km_text(primary['distanceKm'])} · {duration_text(primary)}"
                    body = replace_meta_value(body, "אורך / זמן", route["lengthTimeDisplay"])
                    body = replace_meta_value(body, "דירוג מקור", difficulty_text(primary))
                else:
                    body = replace_meta_value(body, "אורך / זמן", f"{len(records)} הקלטות — פירוט נפרד בהמשך הכרטיס")
                    body = replace_meta_value(body, "דירוג מקור", "מופיע לכל הקלטה בנפרד")
            source_normalized = normalized_difficulty(verified)
            current_normalized = str(route.get("difficulty", {}).get("normalized") or "")
            if source_normalized and current_normalized in {"", "לא אומת", "לא צוין"}:
                route.setdefault("difficulty", {})["normalized"] = source_normalized
                route["difficulty"]["normalizationBasis"] = "highest-rated-offroad-track"
                opening = set_attr(opening, "data-difficulty", source_normalized)
                opening = set_attr(opening, "data-difficulty-basis", "highest-rated-offroad-track")
                body = replace_visible_difficulty(body, current_normalized, source_normalized)
                body = replace_meta_value(body, "סיווג קושי למסנן", source_normalized)
            elif current_normalized in {"", "לא אומת", "לא צוין"}:
                body = replace_visible_difficulty(body, current_normalized, "לא דורג ב־Off-Road")
            opening = add_search_text(opening, summary)
        elif google_record and google_record.get("status") == "verified":
            section, summary = google_section(google_record)
            body = inject_before_marketing(body, section)
            body = add_summary(body, summary, "source-google-chip")
            body = replace_navigation_chip(body, "Google Maps מאומת", "has-map")
            opening = set_attr(opening, "data-map", "1")
            if google_record.get("distanceKm") is not None:
                route["distanceKm"] = google_record["distanceKm"]
                route["lengthTimeDisplay"] = f"{km_text(google_record['distanceKm'])} · {google_record.get('durationDisplay')}"
                body = replace_meta_value(body, "אורך / זמן", route["lengthTimeDisplay"])
                opening = set_attr(opening, "data-distance", str(google_record["distanceKm"]))
                opening = set_attr(opening, "data-distance-basis", "google-directions")
            route["staticSourceMetadata"] = {"source": "Google Maps Directions", "record": google_record}
            route.setdefault("map", {})["hasDirections"] = True
            route["map"]["directionsStatus"] = "verified"
            route["map"]["directionsUrl"] = google_record.get("url")
            current_normalized = str(route.get("difficulty", {}).get("normalized") or "")
            body = replace_visible_difficulty(body, current_normalized, "קושי לא סופק במקור")
            body = replace_meta_value(body, "דירוג מקור", "Google Maps אינו מספק דירוג קושי")
            body = replace_meta_value(body, "סיווג קושי למסנן", "לא אומת — אין דירוג קושי במקור")
            opening = add_search_text(opening, summary)
            counts["google"] += 1
        elif google_record:
            section, summary = google_unavailable_section(google_record)
            body = inject_before_marketing(body, section)
            body = add_summary(body, summary, "source-google-chip")
            body = replace_navigation_chip(body, "קישור Google לא תקין", "no-map")
            opening = set_attr(opening, "data-map", "0")
            route["staticSourceMetadata"] = {"source": "Google Maps Directions", "record": google_record}
            route.setdefault("map", {})["hasDirections"] = False
            route["map"]["directionsStatus"] = "unavailable"
            route["map"]["directionsUrl"] = google_record.get("url")
            opening = add_search_text(opening, summary)
            counts["googleUnavailable"] += 1
        counts["cards"] += 1
        return opening + body + "</details>"

    updated, card_count = CARD_RE.subn(replace_card, index)
    if card_count != len(routes):
        raise ValueError(f"expected {len(routes)} cards, materialized {card_count}")
    updated = updated.replace("גרסת מוצר 2.2.0", f"גרסת מוצר {PRODUCT_VERSION}")
    updated = updated.replace("גרסת מסמך 2.1.6", f"גרסת מסמך {MAIN_DOCUMENT_VERSION}")
    updated = updated.replace("?v=2.1.6", f"?v={MAIN_DOCUMENT_VERSION}")
    updated = updated.replace("בגרסה 2.1 מוצגים", "בגרסה 2.3 מוצגים")
    updated = updated.replace('<div class="stat"><b>276</b>כרטיסים עם ניווט</div>', '<div class="stat"><b>280</b>כרטיסים עם ניווט</div>')
    routes_doc["productVersion"] = PRODUCT_VERSION
    routes_doc["documentVersion"] = ROUTES_DOCUMENT_VERSION
    routes_doc["staticSourceMetadataPolicy"] = (
        "כל Track מוצג בנפרד ב-HTML; בכרטיס רב-Track אין סכימת מרחקים או זמנים. "
        "סיווג קושי למסנן מתעד את הרמה הגבוהה ביותר מבין המקורות המדורגים בלבד."
    )
    index_path.write_text(updated, encoding="utf-8")
    routes_path.write_text(json.dumps(routes_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return counts


def list_google_only(root: Path) -> list[dict[str, str]]:
    index = (root / "index.html").read_text(encoding="utf-8")
    routes = {item["id"]: item for item in json.loads((root / "data" / "routes.json").read_text(encoding="utf-8"))["routes"]}
    result: list[dict[str, str]] = []
    for match in CARD_RE.finditer(index):
        route_id = match.group("id")
        route = routes[route_id]
        if route.get("map", {}).get("trackIds"):
            continue
        urls = [html.unescape(item) for item in GOOGLE_DIRECTIONS_RE.findall(match.group("body"))]
        for url in urls:
            result.append({"id": route_id, "title": route["title"], "url": url})
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--list-google-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.list_google_only:
        print(json.dumps(list_google_only(root), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(materialize(root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
