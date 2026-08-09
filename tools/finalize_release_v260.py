"""השלמת מהדורת היומן המקומי — גרסת מסמך 1.0.0; גרסת מוצר 2.6.0."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_VERSION = "2.6.0"
DOCUMENT_VERSION = "2.4.0"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
index = index.replace("2.5.1", PRODUCT_VERSION).replace("2.3.3", DOCUMENT_VERSION)
index = replace_once(
    index,
    f'<script src="./assets/js/app.js?v={DOCUMENT_VERSION}" defer></script></head>',
    f'<script src="./assets/js/app.js?v={DOCUMENT_VERSION}" defer></script><script src="./assets/js/field-notes.js?v={DOCUMENT_VERSION}" defer></script></head>',
    "field-notes script",
)
index = replace_once(
    index,
    "חמישה מסומנים כלא זמינים.</p>",
    "חמישה מסומנים כלא זמינים. מהדורה 2.6 מוסיפה יומן שטח מקומי לכל מסלול עם הערות, ביקורות, תמונות, קישורי סרטונים, גיבוי, ייבוא ודוח HTML — ללא שרת.</p>",
    "hero copy",
)
index = replace_once(index, '<div class="quality-number">2.5</div>', '<div class="quality-number">2.6</div>', "edition number")
index = replace_once(
    index,
    "מהדורה מלאה עם 339 כרטיסי טיול וספריית מחקר נפרדת.",
    "מהדורה מלאה עם 339 כרטיסי טיול, ספריית מחקר ויומן שטח מקומי.",
    "edition title",
)
index = replace_once(
    index,
    '<div class="stat visit-stat">',
    '<div class="stat"><b>מקומי</b>יומן הערות וביקורות</div><div class="stat visit-stat">',
    "journal statistic",
)
index_path.write_text(index, encoding="utf-8")

manifest_path = ROOT / "manifest.webmanifest"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["name"] = f"ספר מסלולי האדוונצ׳ר והאופרוד בישראל של אילן · גרסת מסמך {DOCUMENT_VERSION}"
manifest["description"] = "מדריך מסלולים קהילתי עם מפות, יומן שטח מקומי, ביקורות, תמונות, גיבוי, הזמנות WhatsApp, ייצוא HTML, בטיחות, AI מקומי והסבר קולי"
manifest["version"] = PRODUCT_VERSION
manifest["document_version"] = DOCUMENT_VERSION
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

offline_path = ROOT / "offline.html"
offline = offline_path.read_text(encoding="utf-8").replace("2.5.1", PRODUCT_VERSION).replace("2.3.3", DOCUMENT_VERSION)
offline = replace_once(
    offline,
    "כרטיסים ונתוני המקור הקשיחים שכבר נטענו עשויים להישאר זמינים.",
    "כרטיסים, נתוני המקור והערות מקומיות שכבר נטענו עשויים להישאר זמינים.",
    "offline journal notice",
)
offline_path.write_text(offline, encoding="utf-8")

sw_path = ROOT / "sw.js"
sw = sw_path.read_text(encoding="utf-8").replace("2.5.1", PRODUCT_VERSION).replace("2.3.3", DOCUMENT_VERSION)
sw = replace_once(
    sw,
    f"'./assets/js/app.js?v={DOCUMENT_VERSION}','./icons/icon-192.png'",
    f"'./assets/js/app.js?v={DOCUMENT_VERSION}','./assets/js/field-notes.js?v={DOCUMENT_VERSION}','./icons/icon-192.png'",
    "service worker journal asset",
)
sw_path.write_text(sw, encoding="utf-8")

print(json.dumps({"productVersion": PRODUCT_VERSION, "documentVersion": DOCUMENT_VERSION, "fieldNotes": True}, ensure_ascii=False))
