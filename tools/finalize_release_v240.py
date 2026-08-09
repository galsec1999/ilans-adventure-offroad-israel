"""סגירת מהדורת האתר 2.4.0 — גרסת מסמך 1.0.6; מסמך ראשי 2.2.3."""

from __future__ import annotations

import json
from pathlib import Path


PRODUCT_VERSION = "2.4.0"
DOCUMENT_VERSION = "2.2.3"
BUILD_DATE = "2026-08-09"


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing release marker: {label}")
    return text.replace(old, new, 1)


def update_json_version(path: Path, product: str, document: str | None = None) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "productVersion" in payload:
        payload["productVersion"] = product
    if "product_version" in payload:
        payload["product_version"] = product
    if document:
        if "documentVersion" in payload:
            payload["documentVersion"] = document
        if "document_version" in payload:
            payload["document_version"] = document
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    index_path = root / "index.html"
    index = index_path.read_text(encoding="utf-8")
    index = index.replace("מהדורת GitHub Pages · 2026-08-06", f"מהדורת GitHub Pages · {BUILD_DATE}")
    old_note = (
        '<section class="wrap edition-note" aria-labelledby="quality-title"><div class="quality-number">35</div><p>'
        '<strong id="quality-title">בגרסה 2.4 מוצגים רק כרטיסי טיול — לא כותרות מחקר.</strong><br>'
        'שלושים וחמישה קישורי Off‑Road שהיו בנספח קיבלו כרטיס עם נתוני המקור. בנוסף, נתוני המקור הושלמו לכל קישורי ה־Track הקיימים בספר, '
        'והקלטות מרובות מוצגות בנפרד. מאה מקורות חיצוניים חלקיים נשמרו למחקר ולא נספרים כמסלולים עד שיעברו אימות.</p></section>'
    )
    new_note = (
        '<section class="wrap edition-note" aria-labelledby="quality-title"><div class="quality-number">2.4</div><p>'
        '<strong id="quality-title">מהדורה מלאה עם 339 כרטיסי טיול וספריית מחקר נפרדת.</strong><br>'
        'בכל כרטיס Off‑Road מוצגים כעת גם תיאור המקור כשפורסם, בעל ההקלטה, תאריך העדכון ונתוני הביקורות — בנוסף למרחק, זמן, פעילות וקושי. '
        'מאה מקורות 4X4 מוצגים בתחתית כספריית מחקר נפרדת ואינם נספרים כמסלולי אופנוע עד שתאומת התאמתם.</p></section>'
    )
    if new_note not in index:
        index = replace_required(index, old_note, new_note, "edition note")
    transparency = (
        '<section class="wrap data-transparency" aria-labelledby="data-transparency-title"><h2 id="data-transparency-title">מה ידוע ומה עדיין דורש בדיקה</h2>'
        '<div class="transparency-grid"><div><b>287</b><span>כרטיסים עם מרחק</span></div><div><b>284</b><span>כרטיסים עם סיווג קושי</span></div>'
        '<div><b>280</b><span>כרטיסים עם ניווט</span></div><div><b>69</b><span>כרטיסים מלאים</span></div>'
        '<div><b>52</b><span>ללא מרחק ידוע</span></div><div><b>55</b><span>ללא קושי מאומת</span></div><div><b>59</b><span>ללא ניווט מאומת</span></div><div><b>7</b><span>סגורים או לא זמינים</span></div></div>'
        '<p>המספרים נגזרים מנתוני הכרטיסים במהדורה זו. שדה חסר נשאר חסר במכוון; אין השלמה משוערת ואין המצאת נתונים.</p></section>'
    )
    marker = '<section class="wrap" aria-labelledby="disclaimer-title">'
    if transparency not in index:
        index = replace_required(index, marker, transparency + marker, "transparency insertion")
    old_counter = '<div class="stat visit-stat"><img id="visitCountBadge" alt="מונה כניסות ציבורי" decoding="async"><span>כניסות שנמדדו</span><small id="visitCountStatus" aria-live="polite">טוען מונה חיצוני…</small></div>'
    new_counter = '<div class="stat visit-stat"><b id="visitCount">—</b>כניסות שנמדדו<small id="visitCountStatus" aria-live="polite">טוען מונה ציבורי…</small></div>'
    if new_counter not in index:
        index = replace_required(index, old_counter, new_counter, "visit counter")
    index_path.write_text(index, encoding="utf-8")

    manifest_path = root / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["description"] = "מדריך קהילתי עם 339 כרטיסי טיול, 100 מקורות מחקר נפרדים, נתוני מקור קשיחים, הזמנות WhatsApp, ייצוא HTML, בטיחות ו-AI מקומי"
    manifest["version"] = PRODUCT_VERSION
    manifest["document_version"] = DOCUMENT_VERSION
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sw_path = root / "sw.js"
    sw = sw_path.read_text(encoding="utf-8")
    sw = sw.replace("גרסת מסמך 2.1.7; גרסת מוצר 2.3.0", "גרסת מסמך 2.2.2; גרסת מוצר 2.4.0")
    sw = sw.replace("גרסת מסמך 2.2.0; גרסת מוצר 2.4.0", "גרסת מסמך 2.2.2; גרסת מוצר 2.4.0")
    sw = sw.replace("גרסת מסמך 2.2.1; גרסת מוצר 2.4.0", "גרסת מסמך 2.2.2; גרסת מוצר 2.4.0")
    sw = sw.replace("גרסת מסמך 2.2.2; גרסת מוצר 2.4.0", "גרסת מסמך 2.2.3; גרסת מוצר 2.4.0")
    sw = sw.replace("2.3.0-doc-2.1.7", "2.4.0-doc-2.2.2").replace("2.4.0-doc-2.2.0", "2.4.0-doc-2.2.2").replace("2.4.0-doc-2.2.1", "2.4.0-doc-2.2.2")
    sw = sw.replace("2.4.0-doc-2.2.2", "2.4.0-doc-2.2.3")
    sw = sw.replace("?v=2.1.7", "?v=2.2.2").replace("?v=2.2.0", "?v=2.2.2").replace("?v=2.2.1", "?v=2.2.2")
    sw = sw.replace("?v=2.2.2", "?v=2.2.3")
    sw_path.write_text(sw, encoding="utf-8")

    offline_path = root / "offline.html"
    offline = offline_path.read_text(encoding="utf-8")
    offline = offline.replace("גרסת מסמך 2.1.7", "גרסת מסמך 2.2.2").replace("גרסת מסמך 2.2.0", "גרסת מסמך 2.2.2").replace("גרסת מסמך 2.2.1", "גרסת מסמך 2.2.2")
    offline = offline.replace("גרסת מסמך 2.2.2", "גרסת מסמך 2.2.3")
    offline = offline.replace("גרסת מוצר 2.3.0", "גרסת מוצר 2.4.0")
    offline = offline.replace("?v=2.1.7", "?v=2.2.2").replace("?v=2.2.0", "?v=2.2.2").replace("?v=2.2.1", "?v=2.2.2")
    offline = offline.replace("?v=2.2.2", "?v=2.2.3")
    offline_path.write_text(offline, encoding="utf-8")

    update_json_version(root / "data" / "offroad-all-metadata.json", PRODUCT_VERSION, "2.1.7")
    metadata_json = json.loads((root / "data" / "offroad-all-metadata.json").read_text(encoding="utf-8"))
    metadata_js = (
        f"/* מטא-דאטה Off-Road — גרסת מסמך 2.1.7; גרסת מוצר {PRODUCT_VERSION} */\n"
        f"window.OFFROAD_TRACK_METADATA = {json.dumps(metadata_json, ensure_ascii=False, separators=(',', ':'))};\n"
    )
    (root / "data" / "offroad-all-metadata.js").write_text(metadata_js, encoding="utf-8")
    google_path = root / "data" / "google-route-metadata.json"
    update_json_version(google_path, PRODUCT_VERSION, "1.0.2")
    google = json.loads(google_path.read_text(encoding="utf-8"))
    google["title"] = "מטא-דאטה מאומת לקישורי Google Maps Directions — גרסת מסמך 1.0.2"
    google_path.write_text(json.dumps(google, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"productVersion": PRODUCT_VERSION, "documentVersion": DOCUMENT_VERSION}, ensure_ascii=False))


if __name__ == "__main__":
    main()
