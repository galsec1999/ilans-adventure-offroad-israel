"""שער איכות למהדורה 2.6.0 — גרסת מסמך 1.0.7; מסמך ראשי 2.4.0."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_VERSION = "2.6.0"
DATA_PRODUCT_VERSION = "2.5.0"
DOCUMENT_VERSION = "2.4.0"
CARD_RE = re.compile(r'<details class="[^"]*\broute-card\b[^"]*" id="([^"]+)"([^>]*)>(.*?)</details>', re.DOTALL)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "assets/css/app.css").read_text(encoding="utf-8")
    js = (ROOT / "assets/js/app.js").read_text(encoding="utf-8")
    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    offline = (ROOT / "offline.html").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))
    routes_doc = json.loads((ROOT / "data/routes.json").read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "data/offroad-all-metadata.json").read_text(encoding="utf-8"))
    research = json.loads((ROOT / "data/research-candidates.json").read_text(encoding="utf-8"))
    cards = list(CARD_RE.finditer(index))

    require(len(cards) == 339, "339 primary route cards")
    require(len({match.group(1) for match in cards}) == 339, "route card IDs are unique")
    require(len(routes_doc["routes"]) == 339, "routes dataset contains 339 records")
    require(routes_doc["productVersion"] == DATA_PRODUCT_VERSION, "routes dataset product version")
    require(routes_doc["documentVersion"] == "2.2.2", "routes dataset document version")
    require(f"גרסת מוצר {PRODUCT_VERSION}" in index and f"גרסת מסמך {DOCUMENT_VERSION}" in index, "visible main versions")
    require(PRODUCT_VERSION in js and DOCUMENT_VERSION in js, "JavaScript versions")
    require(PRODUCT_VERSION in css and DOCUMENT_VERSION in css, "CSS versions")
    require(manifest["version"] == PRODUCT_VERSION and manifest["document_version"] == DOCUMENT_VERSION, "manifest versions")
    require("2.6.0-doc-2.4.0" in sw and "?v=2.4.0" in sw, "service worker cache version")
    require(f"גרסת מוצר {PRODUCT_VERSION}" in offline and f"גרסת מסמך {DOCUMENT_VERSION}" in offline, "offline page versions")

    require(index.count('class="source-fact-card verified"') == 294, "verified source fact cards: 290 Off-Road and 4 Google")
    require(index.count('class="source-fact-card unavailable"') == 6, "unavailable source fact cards: 5 Off-Road and 1 Google")
    require(index.count('class="source-description') == 295, "all Off-Road track associations have hard-coded description status")
    require(index.count("בעל ההקלטה במקור:") == 290, "all verified Off-Road records show owner")
    require(index.count("עודכן:") >= 290, "all verified Off-Road records show update date")
    require(index.count("ביקורות") >= 290, "all verified Off-Road records show review status")
    require(metadata["counts"]["verified"] == 290 and metadata["counts"]["unavailable"] == 5, "Off-Road metadata counts")
    require(metadata["productVersion"] == DATA_PRODUCT_VERSION and metadata["documentVersion"] == "2.2.0", "Off-Road metadata versions")

    derived_cards = [match for match in cards if 'data-difficulty-basis="offroad-track-source"' in match.group(2)]
    require(len(derived_cards) == 272, "272 cards use source-only difficulty normalization")
    require(all(" · לא אומת" not in match.group(3).split("</summary>", 1)[0] for match in derived_cards), "sourced difficulty is visible in every affected summary")
    require(all("<span>לא אומת</span>" not in match.group(3).split("</summary>", 1)[0] for match in derived_cards), "sourced difficulty chips are consistent")

    routes = routes_doc["routes"]
    require(sum(item.get("distanceKm") is not None for item in routes) == 287, "287 cards have distance")
    require(sum((item.get("difficulty") or {}).get("normalized") in {None, "", "לא אומת", "לא צוין"} for item in routes) == 80, "80 cards explicitly lack verified difficulty")
    require(sum(bool((item.get("map") or {}).get("hasMap") or (item.get("map") or {}).get("hasDirections")) for item in routes) == 280, "280 cards have usable navigation")
    qualities = {name: sum(item.get("quality") == name for item in routes) for name in ("כרטיס מלא", "כרטיס שימושי חלקית", "מידע חסר", "סגור / לא זמין")}
    require(qualities == {"כרטיס מלא": 69, "כרטיס שימושי חלקית": 189, "מידע חסר": 74, "סגור / לא זמין": 7}, "quality categories match the data")

    require(len(research["routes"]) == 100 and research["count"] == 100, "100 research candidates preserved")
    require(research["navigation_links_discovered"] == 45, "45 research navigation links recorded")
    require(index.count('class="research-card"') == 100, "100 research cards visible in separate library")
    require(index.count('class="research-nav"') == 46, "46 research navigation links visible across 45 sources")
    require("התאמה לאופנוע לא אומתה" in index and "לא חלק מ־339" in index, "research library is clearly segregated")
    require(all('class="route-card"' not in item for item in re.findall(r'<article class="research-card".*?</article>', index, re.DOTALL)), "research items cannot enter primary filters")

    for page_name, page in (("index.html", index), ("offline.html", offline)):
        require('<meta name="robots" content="noindex,nofollow,noarchive,nosnippet">' in page, f"{page_name} noindex policy")
    require((ROOT / "robots.txt").read_text(encoding="utf-8").strip() == "User-agent: *\nDisallow: /", "robots.txt blocks crawling")
    require(not any(ROOT.glob("sitemap*")), "no sitemap exists")
    require(manifest["start_url"] == "./" and manifest["scope"] == "./", "manifest works from GitHub Pages subpath")
    require(all(item["src"].startswith("./") and (ROOT / item["src"][2:]).exists() for item in manifest["icons"]), "manifest icons use relative existing paths")
    require("navigator.serviceWorker.register('./sw.js')" in js, "service worker registration is subpath-safe")
    require("beforeinstallprompt" in js and "installButton" in index, "PWA install flow exists")
    require("export-html" in index and "כל פרטי הכרטיס" in js and "offroadTracks" in js, "single-trip full HTML export exists")
    require("open-short-invite" in js and "invite-poster" in index and "invite-map-slot" in index, "legacy and rich WhatsApp invitation features exist")
    require("countapi.mileshilliard.com" in js and "visitCount" in index, "public visit counter exists")
    require("data-theme=\"dark\"" in css and "THEME_STORAGE_KEY" in js, "dark mode exists")
    require("אין שרת, מפתח API או תשלום" in index and "sk-" not in index and "sk-" not in js, "AI works without embedded API keys")
    require(all(f'id="{name}"' in index for name in ("region", "subregion", "difficulty", "surface", "shape", "status", "quality", "source", "map", "sort")), "all route filters and sorting controls exist")
    print("PASS: release 2.6.0 quality gate complete")


if __name__ == "__main__":
    main()
