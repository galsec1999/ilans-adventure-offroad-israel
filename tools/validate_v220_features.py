"""שער איכות למהדורה המאוחדת — גרסת מסמך 1.0.0; מוצר 2.2.0, מסמך ראשי 2.1.6."""

from __future__ import annotations

import json
import re
from pathlib import Path


PRODUCT_VERSION = "2.2.0"
DOCUMENT_VERSION = "2.1.6"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    index = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "assets" / "js" / "app.js").read_text(encoding="utf-8")
    css = (root / "assets" / "css" / "app.css").read_text(encoding="utf-8")
    sw = (root / "sw.js").read_text(encoding="utf-8")
    offline = (root / "offline.html").read_text(encoding="utf-8")
    manifest = json.loads((root / "manifest.webmanifest").read_text(encoding="utf-8"))
    routes = json.loads((root / "data" / "routes.json").read_text(encoding="utf-8"))

    check(f"גרסת מוצר {PRODUCT_VERSION}" in index, "main title displays product 2.2.0")
    check(f"גרסת מסמך {DOCUMENT_VERSION}" in index, "main title displays document 2.1.6")
    check(PRODUCT_VERSION in app and DOCUMENT_VERSION in app, "application script declares both versions")
    check(PRODUCT_VERSION in css and DOCUMENT_VERSION in css, "stylesheet declares both versions")
    check(manifest["version"] == PRODUCT_VERSION, "manifest product version is 2.2.0")
    check(manifest["document_version"] == DOCUMENT_VERSION, "manifest document version is 2.1.6")
    check(PRODUCT_VERSION in sw and DOCUMENT_VERSION in sw, "service worker uses the current versions")
    check(PRODUCT_VERSION in offline and DOCUMENT_VERSION in offline, "offline page shows the current versions")
    check(len(routes["routes"]) == 339 and index.count('class="route-card') == 339, "all 339 route cards remain intact")

    check('id="visitCount"' in index and 'id="visitCountStatus"' in index, "visitor counter is visible in the main statistics")
    check("api.counterapi.dev/v1/ilans-adventure-offroad-israel/site-visits-v1" in app, "public visitor counter endpoint is configured")
    check("VISIT_DAY_STORAGE_KEY" in app and "alreadyCountedToday" in app, "counter increments at most once per device per day")
    check("VISIT_VALUE_STORAGE_KEY" in app and "הערך האחרון שנשמר במכשיר" in app, "counter has a local fallback")

    check("makeInvite(card)" in app and "invite-poster-share" in app, "rich WhatsApp invitation and poster remain")
    check("makeShortInvite(card)" in app and 'id="invite-short-whatsapp"' in index, "short WhatsApp invitation is restored")
    check("downloadRouteImage(card)" in app and "shareRouteImage(card)" in app, "route image download and share are restored")
    check("buildAiPrompt(card)" in app and "speechSynthesis" in app, "local AI prompt and voice explanation remain")
    check("apiKey" not in app and "API_KEY" not in app, "no AI API key is embedded in the application")
    check("routeGuideThemeV21" in app and 'option value="dark"' in index, "dark mode remains")
    check("beforeinstallprompt" in app and "serviceWorker.register" in app, "PWA installation flow remains")

    check("כל פרטי הכרטיס" in app, "single-trip HTML export includes every card field")
    check("נתוני המקור המלאים מ־Off-Road" in app, "single-trip HTML export includes full Off-Road metadata")
    check("data.mapUrls.map" in app and "כל מפות המסלול" in app, "single-trip HTML export includes every linked map")
    check("embedLocalImages(clone)" in app and "התמונות הוטמעו בקובץ" in app, "single-trip HTML export embeds its images")
    check("הדפסה / שמירה כ־PDF" in app, "exported HTML supports printing and PDF saving")

    check(f"app.css?v={DOCUMENT_VERSION}" in index, "stylesheet is cache-busted")
    check(f"offroad-all-metadata.js?v={DOCUMENT_VERSION}" in index, "metadata script is cache-busted")
    check(f"app.js?v={DOCUMENT_VERSION}" in index, "application script is cache-busted")
    check(f"app.js?v={DOCUMENT_VERSION}" in sw, "service worker caches the versioned application script")
    check('<meta name="robots" content="noindex,nofollow,noarchive,nosnippet">' in index, "noindex policy remains")
    check(re.search(r"User-agent:\s*\*\s*Disallow:\s*/", (root / "robots.txt").read_text(encoding="utf-8")) is not None, "robots.txt still disallows crawling")
    check(not (root / "sitemap.xml").exists(), "no sitemap was created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
