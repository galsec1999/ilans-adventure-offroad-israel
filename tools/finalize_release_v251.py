#!/usr/bin/env python3
"""Finalize the public light/dark release. גרסת מסמך 1.0.0; גרסת מוצר 2.5.1."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str, expected: int | None = None) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if expected is not None and count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrences, found {count}: {old}")
    if count == 0:
        raise SystemExit(f"{path}: missing required text: {old}")
    target.write_text(text.replace(old, new), encoding="utf-8")


replace("index.html", "2.5.0", "2.5.1")
replace("index.html", "2.3.2", "2.3.3")

early_theme = (
    '<script id="earlyTheme">(function(){try{var p=localStorage.getItem('
    "'routeGuideThemeV21')||'light';var t=p==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):p;"
    "document.documentElement.dataset.theme=t;document.querySelector('meta[name=\"theme-color\"]')?.setAttribute('content',t==='dark'?'#151c18':'#285d45');"
    "}catch(e){document.documentElement.dataset.theme='light';}})();</script>"
)
replace(
    "index.html",
    '<link rel="stylesheet" href="./assets/css/app.css?v=2.3.3">',
    early_theme + '<link rel="stylesheet" href="./assets/css/app.css?v=2.3.3">',
    1,
)

hero_nav = (
    '<nav class="hero-actions" aria-label="פעולות ראשיות"><a class="primary" href="#routes">מעבר למסלולים</a>'
    '<a class="ghost" href="#safety">בטיחות ואחריות</a><button class="accent" type="button" '
    "onclick=\"document.getElementById('installButton').click()\">התקנת האפליקציה</button></nav>"
)
theme_switcher = (
    '<div class="theme-switcher" role="group" aria-label="בחירת מצב תצוגה">'
    '<span class="theme-switcher-label">תצוגה</span>'
    '<button class="theme-choice" id="themeLightButton" type="button" aria-pressed="true">☀️ מצב בהיר</button>'
    '<button class="theme-choice" id="themeDarkButton" type="button" aria-pressed="false">🌙 מצב חשוך</button>'
    '<span class="theme-status" id="themeStatus" aria-live="polite">מצב בהיר פעיל</span></div>'
)
replace("index.html", hero_nav, hero_nav + theme_switcher, 1)

for name in ("manifest.webmanifest", "sw.js", "offline.html"):
    replace(name, "2.5.0", "2.5.1")
    replace(name, "2.3.2", "2.3.3")

print("Finalized product 2.5.1 / document 2.3.3")
