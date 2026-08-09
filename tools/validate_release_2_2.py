#!/usr/bin/env python3
"""בדיקות שחרור 2.2 — גרסת מסמך 1.0.0; גרסת מוצר 2.2.0."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_VERSION = "2.2.0"
DOCUMENT_VERSION = "2.2.0"


class GuideParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.route_ids: list[str] = []
        self.route_actions = 0
        self.export_buttons = 0
        self.noindex = False
        self.scripts: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "details" and "route-card" in classes:
            self.route_ids.append(values.get("id") or "")
        if tag == "div" and "route-actions" in classes:
            self.route_actions += 1
        if tag == "button" and "export-html" in classes:
            self.export_buttons += 1
        if tag == "meta" and values.get("name") == "robots":
            self.noindex = values.get("content") == "noindex,nofollow,noarchive,nosnippet"
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    index_text = (ROOT / "index.html").read_text(encoding="utf-8")
    parser = GuideParser()
    parser.feed(index_text)
    require(len(parser.route_ids) == 339, f"expected 339 route cards, found {len(parser.route_ids)}")
    require(len(set(parser.route_ids)) == 339, "route IDs must be unique")
    require(all(parser.route_ids), "every route card must have an ID")
    require(parser.route_actions == 339, f"expected 339 route action bars, found {parser.route_actions}")
    require(parser.export_buttons == 339, f"expected 339 HTML export buttons, found {parser.export_buttons}")
    require(parser.noindex, "index.html noindex directive is missing")
    require(f"גרסת מוצר {PRODUCT_VERSION}" in parser.title, "product version is missing from title")
    require(f"גרסת מסמך {DOCUMENT_VERSION}" in parser.title, "document version is missing from title")
    require("./assets/js/field-notes.js" in parser.scripts, "field notes module is not loaded")

    manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))
    require(manifest["version"] == PRODUCT_VERSION, "manifest product version mismatch")
    require(manifest["document_version"] == DOCUMENT_VERSION, "manifest document version mismatch")
    require(manifest["start_url"] == "./" and manifest["scope"] == "./", "manifest must remain subpath-safe")
    for icon in manifest["icons"]:
        require((ROOT / icon["src"].removeprefix("./")).is_file(), f"missing icon: {icon['src']}")

    service_worker = (ROOT / "sw.js").read_text(encoding="utf-8")
    require("2.2.0" in service_worker, "service worker version mismatch")
    require("./assets/js/field-notes.js" in service_worker, "field notes module is missing from the app shell")
    require("const CACHE_PREFIX='ilans-adventure-offroad-guide-';" in service_worker, "service worker uses the stable cache cleanup prefix")

    notes_source = (ROOT / "assets/js/field-notes.js").read_text(encoding="utf-8")
    for required in (
        "indexedDB.open",
        "routeId",
        "routeSnapshot",
        "sourceType",
        "sourceUrl",
        "reviewText",
        "videoLinks",
        "exifRemoved:true",
        "syncState:'local-only'",
        "routeExportHtml",
        "exportPackage",
        "importBackup",
    ):
        require(required in notes_source, f"field notes contract is missing: {required}")

    app_source = (ROOT / "assets/js/app.js").read_text(encoding="utf-8")
    require("R123FieldNotes?.routeExportHtml" in app_source, "trip HTML export does not include local notes")
    require("const PRODUCT_VERSION = '2.2.0'" in app_source, "app product version mismatch")
    require("const DOC_VERSION = '2.2.0'" in app_source, "app document version mismatch")

    robots = (ROOT / "robots.txt").read_text(encoding="utf-8").replace("\r\n", "\n")
    require(robots == "User-agent: *\nDisallow: /\n", "robots.txt contract mismatch")
    require(not (ROOT / "sitemap.xml").exists(), "sitemap.xml must not be present")

    for path in ("README_HE.md", "CHANGELOG.md", "BUILD_INFO.txt"):
        text = (ROOT / path).read_text(encoding="utf-8")
        require("גרסת מסמך 2.2.0" in text, f"{path} does not show document version 2.2.0")
    format_doc = (ROOT / "FIELD_NOTES_FORMAT.md").read_text(encoding="utf-8")
    require("גרסת מסמך 1.0.0" in format_doc, "field notes format document has no visible version")

    routes = json.loads((ROOT / "data/routes.json").read_text(encoding="utf-8"))
    require(len(routes["routes"]) == 339, f"routes.json count changed unexpectedly: {len(routes['routes'])}")

    print(json.dumps({
        "result": "passed",
        "route_cards": len(parser.route_ids),
        "route_action_bars": parser.route_actions,
        "html_export_buttons": parser.export_buttons,
        "product_version": PRODUCT_VERSION,
        "document_version": DOCUMENT_VERSION,
        "field_notes_schema": 1,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
