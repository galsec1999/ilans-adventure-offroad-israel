#!/usr/bin/env python3
"""שער איכות למצבי תצוגה בהיר וחשוך — גרסת מסמך 1.0.1; מוצר 2.6.0."""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []
checks = 0


def require(condition: bool, message: str) -> None:
    global checks
    checks += 1
    if not condition:
        failures.append(message)


index = (ROOT / "index.html").read_text(encoding="utf-8")
css = (ROOT / "assets/css/app.css").read_text(encoding="utf-8")
js = (ROOT / "assets/js/app.js").read_text(encoding="utf-8")
sw = (ROOT / "sw.js").read_text(encoding="utf-8")
manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))

require("גרסת מוצר 2.6.0" in index and "גרסת מסמך 2.4.0" in index, "visible release versions")
require(index.index('id="earlyTheme"') < index.index('rel="stylesheet"'), "early theme is applied before CSS")
require(index.count('id="themeLightButton"') == 1, "one prominent light-mode button")
require(index.count('id="themeDarkButton"') == 1, "one prominent dark-mode button")
require('role="group" aria-label="בחירת מצב תצוגה"' in index, "theme control has an accessible group label")
require('id="themeStatus" aria-live="polite"' in index, "theme status is announced")
require('option value="light"' in index and 'option value="dark"' in index and 'option value="system"' in index, "advanced theme select retains all choices")
require(':root[data-theme="dark"]' in css and "color-scheme: dark" in css, "dark palette is defined")
require(".theme-switcher" in css and '.theme-choice[aria-pressed="true"]' in css, "visible active switch styles")
require("@media(max-width:760px)" in css and ".theme-switcher{display:flex;width:100%" in css, "mobile theme switch layout")
require("themeLightButton" in js and "themeDarkButton" in js and "chooseTheme" in js, "buttons are wired")
require("localStorage.setItem(THEME_STORAGE_KEY, preference)" in js, "theme choice is persisted")
require("themeSelect.value = preference" in js, "hero buttons synchronize the advanced select")
require("aria-pressed" in js and "themeStatus.textContent" in js, "theme state stays accessible")
require(manifest["version"] == "2.6.0" and manifest["document_version"] == "2.4.0", "manifest versions")
require("2.6.0-doc-2.4.0" in sw and "?v=2.4.0" in sw, "fresh PWA cache")

if failures:
    print(f"FAIL: {len(failures)} of {checks} checks failed")
    for failure in failures:
        print(f"- {failure}")
    raise SystemExit(1)

print(f"PASS: {checks} theme-mode checks passed")
