"""ביקורת התאמת כרטיס–מפה — גרסת מסמך 1.1.0; גרסת מוצר 2.7.0.

הכלי עובר על כל 339 הכרטיסים. ב־Off-Road הוא מתייחס למטא־דאטה של ה־Track
כמקור המחייב לשם, תיאור, אזור, קושי, פעילות וצורת המסלול. תוכן מקומי קודם
נשמר בארכיון הביקורת, אך אינו משמש להשלמת עובדה שהמקור אינו מספק.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRODUCT_VERSION = "2.7.0"
DOCUMENT_VERSION = "1.1.0"
ROUTES_DOCUMENT_VERSION = "2.3.0"

AREA_LABELS = {
    "HERMON_GOLAN_ETZBA_GALIL": ("צפון", "חרמון, גולן ואצבע הגליל"),
    "GALIL_ELION_MAARAVI": ("צפון", "הגליל העליון והמערבי"),
    "GALIL_BOT_AMAKIM_GILBOA": ("צפון", "הגליל התחתון, העמקים והגלבוע"),
    "CARMEL_RAMOT_MENASHE": ("צפון", "כרמל, רמות מנשה והעמקים"),
    "MISHOR_GUSH_DAN": ("מרכז", "מישור החוף וגוש דן"),
    "JERUSALEM_MOUNT_SHFELA": ("מרכז", "ירושלים, הרי יהודה והשפלה"),
    "JLM": ("מרכז", "ירושלים והסביבה"),
    "SHOMRON_BINYAMIN": ("מרכז", "שומרון ובנימין"),
    "DEAD_SEA_MIDBAR_YEHIDA": ("דרום ומדבר", "ים המלח ומדבר יהודה"),
    "NEGEV_NORTH": ("דרום ומדבר", "צפון הנגב"),
    "NEGEV_CENTER_MACHTESHIM": ("דרום ומדבר", "מרכז הנגב והמכתשים"),
    "NEGEV_SOUTH_EILAT": ("דרום ומדבר", "דרום הנגב ואילת"),
}

UNKNOWN_AREA_OVERRIDES = {
    "4661681859592192": ("צפון", "בקעת הירדן הצפונית"),
    "4775363851583488": ("דרום ומדבר", "צפון הנגב ועוטף עזה"),
    "4907207393804288": ("דרום ומדבר", "צפון הנגב ועוטף עזה"),
    "5013454925332480": ("דרום ומדבר", "צפון הנגב ועוטף עזה"),
    "5188030844108800": ("דרום ומדבר", "צפון הנגב ועוטף עזה"),
    "5853101876051968": ("דרום ומדבר", "צפון הנגב"),
    "6743706558005248": ("דרום ומדבר", "שפלת הדרום ועוטף עזה"),
}

STOP_WORDS = {
    "של", "עם", "את", "אל", "על", "בין", "דרך", "מסלול", "טיול", "רכיבה",
    "אדוונצר", "אדוונצ׳ר", "אופנוע", "אופנועים", "שטח", "קל", "בינוני", "קשה",
    "ניווט", "navigation", "offroad", "gpx", "יום", "יוצא", "יוצאים", "סובב",
    "חוצה", "מעגלי", "מלא", "ללא", "לכיוון", "הקלטה", "הקלטת",
}

GENERIC_TITLE_RE = re.compile(
    r"^(?:navigation|ניווט|מסלול|track|offroad|downloading|\d{4}(?:\s+\d{1,2}[:_]\d{2}[:_]\d{2})?)(?:\b|\s|[-_.])",
    re.IGNORECASE,
)

SURFACE_RULES = (
    (re.compile(r"חול|דיונ"), "חול"),
    (re.compile(r"בוץ|בוצי"), "בוץ"),
    (re.compile(r"סלע|אבנ|דרדר"), "סלעים"),
    (re.compile(r"כורכר"), "כורכר"),
    (re.compile(r"אספלט|כביש"), "כביש"),
)

PLACE_HINT_RE = re.compile(
    r"(?:נחל|עין|מעיין|הר|מצפה|תל|יער|בקעת|עמק|צומת|פארק|שמורת|מעלה|באר|בור|חורב[הת]|חוף|אגמון|"
    r"כנרת|גלבוע|גולן|כרמל|מנשה|ירקון|שרון|שומרון|בנימין|נגב|מדבר|ערד|אילת|ירושלים|לטרון|שוהם|"
    r"מודיעין|שבטה|שדרות|רעים|רוחמה|חדרה|נתניה|קיסריה|פרדס|כרכור|בת שלמה|בית שאן|כפר|קיבוץ|מושב|"
    r"אלמוג|מרסבא|נבי מוסא|סרטבה|ג[׳']יפטליק|פצאל|מחולה|הרודיון|דרגות|ים המלח)",
    re.IGNORECASE,
)
NON_PLACE_RE = re.compile(r"(?:טכני|מנוסים|מתחילים|כיפי|זורם|קושי|אופנוע|רוכבים|סרטון|קישור|gpx|יצאנו|רכבנו|משם|בחזרה|הקלטת)", re.IGNORECASE)


def normalized_tokens(value: Any) -> set[str]:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = text.replace("־", " ").replace("׳", " ").replace("'", " ")
    return {
        token for token in re.findall(r"[א-תa-z0-9]{2,}", text)
        if token not in STOP_WORDS and not token.isdigit()
    }


def meaningful_title(value: Any) -> bool:
    text = " ".join(str(value or "").split()).strip(" -_.")
    if len(text) < 4 or GENERIC_TITLE_RE.search(text):
        return False
    tokens = normalized_tokens(text)
    return bool(tokens)


def meaningful_description(value: Any) -> bool:
    text = " ".join(str(value or "").split()).strip()
    if len(text) < 4 or re.fullmatch(r"https?://\S+", text, re.IGNORECASE):
        return False
    if re.fullmatch(r"[^\n]{1,100}\.gpx", text, re.IGNORECASE):
        return False
    return True


def source_text(record: dict[str, Any]) -> str:
    return " ".join(
        str(record.get(key) or "") for key in ("title", "shortDescription", "description")
    ).strip()


def source_place_mentions(records: list[dict[str, Any]]) -> list[str]:
    """Return only verbatim fragments containing an explicit geographic place hint."""
    mentions: list[str] = []
    seen: set[str] = set()
    for record in records:
        for field in ("title", "shortDescription"):
            value = str(record.get(field) or "")
            value = re.sub(r"https?://\S+", " ", value)
            value = re.sub(r"\b\d{1,4}(?:[/.:_-]\d{1,4})+\b", " ", value)
            for part in re.split(r"[\n,;|→]|\s[-–—]\s|/", value):
                part = " ".join(part.split()).strip(" .:-_()[]")
                part = re.sub(r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b.*$", "", part).strip()
                part = re.sub(r"\s+\d+$", "", part).strip()
                if not (2 <= len(part) <= 48) or not re.search(r"[א-ת]", part):
                    continue
                if not normalized_tokens(part) or GENERIC_TITLE_RE.search(part):
                    continue
                if not PLACE_HINT_RE.search(part) or NON_PLACE_RE.search(part):
                    continue
                key = part.casefold()
                if key not in seen:
                    seen.add(key)
                    mentions.append(part)
    return mentions[:18]


def source_surfaces(records: list[dict[str, Any]]) -> list[str]:
    text = " ".join(source_text(record) for record in records).lower()
    values = [label for pattern, label in SURFACE_RULES if pattern.search(text)]
    return values or ["לא צוין"]


def area_for_record(record: dict[str, Any]) -> tuple[str, str] | None:
    track_id = str(record.get("trackId") or "")
    if track_id in UNKNOWN_AREA_OVERRIDES:
        return UNKNOWN_AREA_OVERRIDES[track_id]
    return AREA_LABELS.get(str(record.get("area") or ""))


def resolved_region(old_region: str, records: list[dict[str, Any]], areas: list[tuple[str, str]]) -> str:
    """Resolve only when API area and endpoints make the major region unambiguous."""
    area_codes = {str(record.get("area") or "") for record in records}
    south_codes = {"NEGEV_NORTH", "NEGEV_CENTER_MACHTESHIM", "NEGEV_SOUTH_EILAT", "DEAD_SEA_MIDBAR_YEHIDA"}
    north_codes = {"HERMON_GOLAN_ETZBA_GALIL", "GALIL_ELION_MAARAVI", "GALIL_BOT_AMAKIM_GILBOA", "CARMEL_RAMOT_MENASHE"}
    center_codes = {"MISHOR_GUSH_DAN"}
    if area_codes & south_codes:
        return "דרום ומדבר"
    coordinates = [
        point
        for record in records
        for point in (record.get("start"), record.get("end"))
        if isinstance(point, dict) and isinstance(point.get("latitude"), (int, float))
    ]
    latitudes = [float(point["latitude"]) for point in coordinates]
    if latitudes and max(latitudes) < 31.65:
        return "דרום ומדבר"
    if old_region == "צפון":
        if area_codes & center_codes and latitudes and max(latitudes) < 32.30:
            return "מרכז"
        return "צפון"
    if old_region == "מרכז":
        if area_codes & north_codes and latitudes and min(latitudes) > 32.55:
            return "צפון"
        return "מרכז"
    if old_region == "דרום ומדבר":
        if area_codes & north_codes and latitudes and min(latitudes) > 32.20:
            return "צפון"
        if area_codes & center_codes and latitudes and min(latitudes) > 31.80:
            return "מרכז"
        return "דרום ומדבר"
    if latitudes and min(latitudes) > 32.55:
        return "צפון"
    if latitudes and min(latitudes) >= 31.65 and max(latitudes) <= 32.55:
        return "מרכז"
    known_regions = list(dict.fromkeys(area[0] for area in areas))
    if len(known_regions) == 1 and known_regions[0] == old_region:
        return old_region
    return old_region or "לא זוהה"


def resolved_subregion(region: str, records: list[dict[str, Any]], areas: list[tuple[str, str]]) -> str:
    codes = {str(record.get("area") or "") for record in records}
    latitudes = [
        float(point["latitude"])
        for record in records
        for point in (record.get("start"), record.get("end"))
        if isinstance(point, dict) and isinstance(point.get("latitude"), (int, float))
    ]
    if region == "מרכז" and "CARMEL_RAMOT_MENASHE" in codes and latitudes and max(latitudes) < 32.55:
        return "השרון, עמק חפר ומישור החוף"
    if region == "דרום ומדבר" and latitudes and max(latitudes) < 31.65 and not (codes & {"DEAD_SEA_MIDBAR_YEHIDA", "NEGEV_CENTER_MACHTESHIM", "NEGEV_SOUTH_EILAT"}):
        return "שפלת הדרום וצפון הנגב"
    return " / ".join(dict.fromkeys(area[1] for area in areas)) or "אזור המקור לא סווג ב־Off‑Road"


def shape_for_records(records: list[dict[str, Any]]) -> str:
    if len(records) != 1:
        return "מספר חלופות"
    value = records[0].get("roundTrip")
    if value is True:
        return "מעגלי"
    if value is False:
        return "קווי / חד־כיווני"
    return "לא צוין"


def difficulty_for_records(records: list[dict[str, Any]]) -> str:
    levels = [int(item.get("difficultyLevel") or 0) for item in records]
    highest = max(levels, default=0)
    if highest >= 4:
        return "קשה"
    if highest >= 2:
        return "בינוני"
    if highest == 1:
        return "קל"
    return "לא אומת"


def canonical_title(route: dict[str, Any], records: list[dict[str, Any]]) -> str:
    if len(records) > 1:
        return str(route.get("title") or "מסלול עם מספר חלופות")
    record = records[0]
    title = " ".join(str(record.get("title") or "").split())
    if meaningful_title(title):
        return title
    description = " ".join(str(record.get("shortDescription") or "").split())
    if meaningful_title(description) and len(description) <= 90:
        return description
    return f"הקלטת Off‑Road {record.get('trackId')}"


def canonical_description(records: list[dict[str, Any]]) -> str:
    if len(records) > 1:
        return "בכרטיס קיימות מספר הקלטות. יש לבחור הקלטה לפי שמה ונתוני המקור לפני פרסום הטיול."
    record = records[0]
    description = " ".join(str(record.get("shortDescription") or "").split())
    if meaningful_description(description):
        return description
    title = " ".join(str(record.get("title") or "").split())
    return f"במקור לא פורסם תיאור נוסף. שם ההקלטה ב־Off‑Road: {title or record.get('trackId')}."


def audit(root: Path) -> dict[str, Any]:
    routes_path = root / "data" / "routes.json"
    metadata_path = root / "data" / "offroad-all-metadata.json"
    google_path = root / "data" / "google-route-metadata.json"
    routes_doc = json.loads(routes_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))["records"]
    google = json.loads(google_path.read_text(encoding="utf-8"))["records"]
    entries: list[dict[str, Any]] = []

    for route in routes_doc["routes"]:
        track_ids = [str(value) for value in (route.get("map", {}).get("trackIds") or [])]
        records = [metadata.get(track_id, {"trackId": track_id, "status": "missing"}) for track_id in track_ids]
        verified = [record for record in records if record.get("status") == "verified"]
        current = {
            "title": route.get("title"),
            "region": route.get("region"),
            "subregion": route.get("subregion"),
            "difficulty": route.get("difficulty", {}).get("normalized"),
            "shape": route.get("shape"),
            "surfaces": route.get("surfaces"),
        }
        archived = (route.get("trustAudit") or {}).get("archivedClassification")
        old = archived if isinstance(archived, dict) else current

        if track_ids:
            local_tokens = normalized_tokens(route.get("title"))
            source_tokens = set().union(*(normalized_tokens(source_text(record)) for record in verified)) if verified else set()
            overlap = sorted(local_tokens & source_tokens)
            areas = [area_for_record(record) for record in verified]
            areas = [area for area in areas if area]
            subregions = list(dict.fromkeys(area[1] for area in areas))
            title = canonical_title(route, verified) if verified else str(route.get("title") or "Track לא זמין")
            description = canonical_description(verified) if verified else "מטא־דאטה של המפה אינו זמין כעת; אין לפרסם על סמך הכרטיס בלבד."
            if areas:
                route["region"] = resolved_region(str(old.get("region") or ""), verified, areas)
                route["subregion"] = resolved_subregion(route["region"], verified, areas)
            elif verified:
                route["region"] = "לא זוהה"
                route["subregion"] = "אזור המקור לא סווג ב־Off‑Road"
            if verified:
                route.setdefault("difficulty", {})["normalized"] = difficulty_for_records(verified)
                route["difficulty"]["normalizationBasis"] = "offroad-track-source"
                route["shape"] = shape_for_records(verified)
                route["surfaces"] = source_surfaces(verified)
                if len(records) == 1:
                    route["title"] = title
            mentions = source_place_mentions(verified)
            status = "verified-source-aligned" if verified and len(verified) == len(records) else "source-unavailable"
            if len(records) > 1:
                status = "multiple-source-maps"
            confidence = "high" if verified and len(verified) == len(records) and (meaningful_title(title) or mentions) else "limited"
            route["trustAudit"] = {
                "status": status,
                "confidence": confidence,
                "canonicalTitle": title,
                "canonicalDescription": description,
                "sourcePlaceMentions": mentions,
                "sourceSearchText": " ".join(source_text(record) for record in verified),
                "sourceAreas": [str(record.get("area") or "UNKNOWN") for record in verified],
                "titleTokenOverlap": overlap,
                "archivedClassification": old,
                "policy": "שם ותיאור להזמנה נלקחים מאותה הקלטת מפה; הטקסט המקומי הקודם נשמר כהקשר ארכיוני בלבד.",
            }
            entry = {
                "routeId": route["id"],
                "localTitleBeforeAudit": old["title"],
                "canonicalTitle": title,
                "trackIds": track_ids,
                "sourceTitles": [record.get("title") for record in records],
                "sourceAreas": [record.get("area") for record in records],
                "resolvedRegion": route.get("region"),
                "resolvedSubregion": route.get("subregion"),
                "sourcePlaceMentions": mentions,
                "titleTokenOverlap": overlap,
                "status": status,
                "confidence": confidence,
            }
        elif route["id"] in google:
            record = google[route["id"]]
            route["trustAudit"] = {
                "status": "google-source-aligned" if record.get("status") == "verified" else "source-unavailable",
                "confidence": "high" if record.get("status") == "verified" else "limited",
                "canonicalTitle": record.get("routeLabel") or route.get("title"),
                "canonicalDescription": record.get("routeLabel") or "לא התקבל תיאור מסלול מן המקור.",
                "sourcePlaceMentions": record.get("waypoints") or [],
                "sourceSearchText": " ".join(record.get("waypoints") or []),
                "archivedClassification": old,
                "policy": "הכותרת ותחנות המסלול נלקחות מקישור Google Directions שנבדק.",
            }
            entry = {
                "routeId": route["id"],
                "localTitleBeforeAudit": old["title"],
                "canonicalTitle": route["trustAudit"]["canonicalTitle"],
                "trackIds": [],
                "sourceTitles": [record.get("routeLabel")],
                "sourceAreas": [],
                "resolvedRegion": route.get("region"),
                "resolvedSubregion": route.get("subregion"),
                "sourcePlaceMentions": route["trustAudit"]["sourcePlaceMentions"],
                "titleTokenOverlap": [],
                "status": route["trustAudit"]["status"],
                "confidence": route["trustAudit"]["confidence"],
            }
        else:
            route["trustAudit"] = {
                "status": "no-map-to-compare",
                "confidence": "none",
                "canonicalTitle": route.get("title"),
                "canonicalDescription": "אין בכרטיס מפה מאומתת להשוואה.",
                "sourcePlaceMentions": [],
                "sourceSearchText": "",
                "archivedClassification": old,
                "policy": "לא בוצעה התאמת מפה משום שאין קישור ניווט מאומת.",
            }
            entry = {
                "routeId": route["id"],
                "localTitleBeforeAudit": old["title"],
                "canonicalTitle": route.get("title"),
                "trackIds": [],
                "sourceTitles": [],
                "sourceAreas": [],
                "resolvedRegion": route.get("region"),
                "resolvedSubregion": route.get("subregion"),
                "sourcePlaceMentions": [],
                "titleTokenOverlap": [],
                "status": "no-map-to-compare",
                "confidence": "none",
            }
        entries.append(entry)

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    routes_doc["productVersion"] = PRODUCT_VERSION
    routes_doc["documentVersion"] = ROUTES_DOCUMENT_VERSION
    routes_doc["generatedAt"] = generated_at
    routes_doc["routeMapTrustPolicy"] = (
        "נתוני ההזמנה, הסינון והאינדוקס של כרטיס עם מפה נגזרים מאותו מקור מפה. "
        "כאשר אין מקור או אין מידע מספיק, הדבר מוצג במפורש ואין השלמה משוערת."
    )
    routes_path.write_text(json.dumps(routes_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    report = {
        "title": f"ביקורת התאמת כרטיס–מפה לכל מסלולי הספר — גרסת מסמך {DOCUMENT_VERSION}",
        "productVersion": PRODUCT_VERSION,
        "routesDocumentVersion": ROUTES_DOCUMENT_VERSION,
        "generatedAt": generated_at,
        "policy": "339 כרטיסים נבדקו. מקומות ומילות חיפוש מוצגים רק כציטוטי מקור או נתוני אזור של API; אין ניחוש שמות מקום מקואורדינטות.",
        "counts": {"total": len(entries), **counts},
        "entries": entries,
    }
    (root / "data" / "route-map-trust-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = audit(root)
    print(json.dumps(report["counts"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
