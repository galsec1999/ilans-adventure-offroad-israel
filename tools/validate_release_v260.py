"""שער איכות ליומן השטח המקומי — גרסת מסמך 1.0.1; מוצר 2.6.0, מסמך ראשי 2.4.0."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_VERSION = "2.6.0"
DOCUMENT_VERSION = "2.4.0"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


index = (ROOT / "index.html").read_text(encoding="utf-8")
app = (ROOT / "assets/js/app.js").read_text(encoding="utf-8")
notes = (ROOT / "assets/js/field-notes.js").read_text(encoding="utf-8")
css = (ROOT / "assets/css/app.css").read_text(encoding="utf-8")
sw = (ROOT / "sw.js").read_text(encoding="utf-8")
offline = (ROOT / "offline.html").read_text(encoding="utf-8")
manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))
robots = (ROOT / "robots.txt").read_text(encoding="utf-8")

require(index.count('class="route-card') == 339, "339 route cards must remain")
require(index.count('class="export-html"') == 339, "every route must retain HTML export")
require(f"גרסת מוצר {PRODUCT_VERSION}" in index and f"גרסת מסמך {DOCUMENT_VERSION}" in index, "visible versions")
require(f"assets/js/field-notes.js?v={DOCUMENT_VERSION}" in index, "field-notes script is loaded with cache busting")
require(f"assets/js/field-notes.js?v={DOCUMENT_VERSION}" in sw, "field-notes script is cached by the service worker")
require(manifest["version"] == PRODUCT_VERSION and manifest["document_version"] == DOCUMENT_VERSION, "manifest versions")
require(manifest["start_url"] == "./" and manifest["scope"] == "./", "manifest remains subpath-safe")
require(f"{PRODUCT_VERSION}-doc-{DOCUMENT_VERSION}" in sw, "service-worker cache version")
require(PRODUCT_VERSION in app and DOCUMENT_VERSION in app and PRODUCT_VERSION in css and DOCUMENT_VERSION in css, "code versions")
require(PRODUCT_VERSION in offline and DOCUMENT_VERSION in offline, "offline versions")
require("window.R123FieldNotes?.routeExportHtml" in app and "${localNotesHtml}" in app, "route HTML export includes local notes")

for token in (
    "ilans-adventure-route-field-notes",
    "indexedDB.open",
    "REPORT_STORE = 'reports'",
    "MEDIA_STORE = 'media'",
    "SETTINGS_STORE = 'settings'",
    "sharing:{visibility:'private', syncState:'local-only'",
    "MAX_PHOTOS_PER_REPORT = 6",
    "MAX_PHOTO_EDGE = 1600",
    "exifRemoved:true",
    "field-notes-action",
    "fieldNotesHubButton",
    "exportHtmlReport",
    "importBackup",
):
    require(token in notes, f"missing field-notes contract: {token}")

require("field-notes-layout" in css and "field-report-photos" in css, "field-notes responsive styles")
require("themeLightButton" in index and "themeDarkButton" in index, "light/dark controls retained")
require("route-map-trust-audit.json" in index and "route-map-trust-audit.json" in sw, "map-trust evidence retained")
require('<meta name="robots" content="noindex,nofollow,noarchive,nosnippet">' in index, "noindex policy")
require(re.search(r"User-agent:\s*\*\s*Disallow:\s*/", robots) is not None, "robots policy")
require(not (ROOT / "sitemap.xml").exists(), "sitemap must not exist")

local_sources = sorted(set(re.findall(r'<img[^>]+src="(\./[^"]+)"', index)))
missing = [source for source in local_sources if not (ROOT / source[2:]).is_file() or (ROOT / source[2:]).stat().st_size == 0]
require(not missing, f"missing local images: {missing[:5]}")

print(json.dumps({
    "result": "passed",
    "productVersion": PRODUCT_VERSION,
    "documentVersion": DOCUMENT_VERSION,
    "routeCards": 339,
    "htmlExports": 339,
    "uniqueLocalImageSources": len(local_sources),
    "fieldNotesSchema": 1,
}, ensure_ascii=False))
