"""סגירת מהדורת אמינות 2.5.0 — גרסת מסמך 1.0.1; מסמך ראשי 2.3.2."""

from __future__ import annotations

import json
from pathlib import Path


PRODUCT_VERSION = "2.5.0"
DOCUMENT_VERSION = "2.3.2"
BUILD_DATE = "2026-08-09"


def replace_all(text: str, replacements: dict[str, str]) -> str:
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    index_path = root / "index.html"
    index = index_path.read_text(encoding="utf-8")
    index = replace_all(index, {
        "גרסת מוצר 2.4.0": f"גרסת מוצר {PRODUCT_VERSION}",
        "גרסת מסמך 2.2.3": f"גרסת מסמך {DOCUMENT_VERSION}",
        "?v=2.2.3": f"?v={DOCUMENT_VERSION}",
        "מהדורת GitHub Pages · 2026-08-06": f"מהדורת GitHub Pages · {BUILD_DATE}",
        '<div class="quality-number">2.4</div>': '<div class="quality-number">2.5</div>',
        '<div><b>284</b><span>כרטיסים עם סיווג קושי</span></div>': '<div><b>259</b><span>כרטיסים עם סיווג קושי מאומת</span></div>',
        '<div><b>55</b><span>ללא קושי מאומת</span></div>': '<div><b>80</b><span>ללא קושי מאומת</span></div>',
    })
    old_map_section = (
        '<section class="form-section"><h3>מפה והערות</h3><div class="map-status" id="invite-map-status">'
    )
    new_map_section = (
        '<section class="form-section"><h3>מפה והערות</h3>'
        '<label id="invite-map-select-wrap" hidden>בחירת ההקלטה המחייבת להזמנה'
        '<select id="invite-map-select" aria-describedby="invite-map-help"></select>'
        '<small id="invite-map-help">בכרטיס עם כמה מפות, שם הטיול, התיאור, המרחק, הקושי וה־QR נלקחים רק מהמפה שנבחרה.</small></label>'
        '<div class="map-status" id="invite-map-status">'
    )
    if 'id="invite-map-select"' not in index:
        if old_map_section not in index:
            raise RuntimeError("invite map section was not found")
        index = index.replace(old_map_section, new_map_section, 1)
    audit_note = (
        '<section class="wrap route-trust-release" aria-labelledby="route-trust-release-title">'
        '<h2 id="route-trust-release-title">מהדורת אמינות: הטקסט והמפה נשארים יחד</h2>'
        '<p>כל 339 הכרטיסים עברו ביקורת התאמה. בכרטיס עם מפת Off‑Road, ההזמנה והייצוא משתמשים בשם, בתיאור, '
        'באזור, במרחק, בזמן, בקושי ובפעילות של אותה הקלטה. בכרטיס עם כמה מפות חייבים לבחור הקלטה אחת לפני פרסום.</p>'
        '<p><a href="./data/route-map-trust-audit.json">דוח ההתאמה המלא — כרטיס אחר כרטיס</a></p></section>'
    )
    marker = '<section class="wrap data-transparency"'
    if audit_note not in index:
        if marker not in index:
            raise RuntimeError("transparency marker was not found")
        index = index.replace(marker, audit_note + marker, 1)
    index_path.write_text(index, encoding="utf-8")

    manifest_path = root / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["name"] = f"ספר מסלולי האדוונצ׳ר והאופרוד בישראל של אילן · גרסת מסמך {DOCUMENT_VERSION}"
    manifest["description"] = "339 כרטיסי טיול עם ביקורת התאמה בין שם, תיאור, מיון ומפת המקור; הזמנות WhatsApp, ייצוא HTML, בטיחות ו-AI מקומי"
    manifest["version"] = PRODUCT_VERSION
    manifest["document_version"] = DOCUMENT_VERSION
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sw_path = root / "sw.js"
    sw = replace_all(sw_path.read_text(encoding="utf-8"), {
        "גרסת מסמך 2.2.3; גרסת מוצר 2.4.0": f"גרסת מסמך {DOCUMENT_VERSION}; גרסת מוצר {PRODUCT_VERSION}",
        "2.4.0-doc-2.2.3": f"{PRODUCT_VERSION}-doc-{DOCUMENT_VERSION}",
        "?v=2.2.3": f"?v={DOCUMENT_VERSION}",
    })
    if "./data/route-map-trust-audit.json" not in sw:
        sw = sw.replace(f"'./data/offroad-all-metadata.js?v={DOCUMENT_VERSION}'", f"'./data/offroad-all-metadata.js?v={DOCUMENT_VERSION}','./data/route-map-trust-audit.json'")
    sw_path.write_text(sw, encoding="utf-8")

    offline_path = root / "offline.html"
    offline = replace_all(offline_path.read_text(encoding="utf-8"), {
        "גרסת מוצר 2.4.0": f"גרסת מוצר {PRODUCT_VERSION}",
        "גרסת מסמך 2.2.3": f"גרסת מסמך {DOCUMENT_VERSION}",
        "?v=2.2.3": f"?v={DOCUMENT_VERSION}",
    })
    offline_path.write_text(offline, encoding="utf-8")

    css_path = root / "assets" / "css" / "app.css"
    css = replace_all(css_path.read_text(encoding="utf-8"), {
        "גרסת מסמך 2.2.3; גרסת מוצר 2.4.0": f"גרסת מסמך {DOCUMENT_VERSION}; גרסת מוצר {PRODUCT_VERSION}",
    })
    trust_css = (
        "\n.source-alignment{margin:0 0 16px;padding:14px;border:2px solid color-mix(in srgb,var(--success) 60%,var(--line));"
        "border-radius:13px;background:color-mix(in srgb,var(--success) 10%,var(--surface))}.source-alignment h3{margin:0 0 8px}.source-alignment p{margin:.45em 0;line-height:1.6}"
        ".source-coordinates{direction:rtl}.source-coordinates a{display:inline-block;direction:ltr}.route-trust-release{margin-block:18px;padding:18px;border-right:7px solid var(--success);"
        "border-radius:15px;background:color-mix(in srgb,var(--success) 10%,var(--surface));box-shadow:var(--shadow-soft)}.route-trust-release h2{margin-top:0;color:var(--forest)}"
        "#invite-map-select-wrap{margin-bottom:10px;padding:10px;border:1px solid var(--line);border-radius:11px;background:var(--surface)}"
    )
    if ".source-alignment{" not in css:
        css += trust_css + "\n"
    css_path.write_text(css, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
