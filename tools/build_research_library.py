"""בניית ספריית מועמדי המחקר — גרסת מסמך 1.0.1; גרסת מוצר 2.4.0."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any


PRODUCT_VERSION = "2.4.0"
MAIN_DOCUMENT_VERSION = "2.2.2"
RESEARCH_DOCUMENT_VERSION = "2.1.5"
SECTION_RE = re.compile(r'<section class="wrap research-note".*?</section>', re.DOTALL)


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def build_card(item: dict[str, Any], index: int) -> str:
    links = item.get("recovered_navigation_links") or []
    source_difficulty = item.get("source_vehicle_difficulty") or "לא צוין במקור 4X4"
    navigation = (
        "".join(
            f'<a class="research-nav" href="{esc(url)}" target="_blank" rel="noopener">פתיחת קובץ ניווט {position}</a>'
            for position, url in enumerate(links, start=1)
        )
        if links else '<span class="research-missing">לא אותר קובץ ניווט בבדיקה הטכנית</span>'
    )
    search = " ".join(
        str(item.get(key) or "")
        for key in ("title", "summary", "region", "source_vehicle_difficulty", "editorial_summary_he")
    )
    return (
        f'<article class="research-card" data-region="{esc(item.get("region") or "לא זוהה")}" '
        f'data-navigation="{1 if links else 0}" data-search="{esc(search)}">'
        f'<div class="research-card-number">{index:03d}</div><div class="research-card-body">'
        f'<h3>{esc(item.get("title"))}</h3><div class="research-tags">'
        f'<span>{esc(item.get("region") or "לא זוהה")}</span><span>מקור: {esc(item.get("source") or "לא צוין")}</span>'
        f'<span>עבירות רכב במקור: {esc(source_difficulty)}</span>'
        '<span class="research-unverified">התאמה לאופנוע לא אומתה</span></div>'
        f'<p>{esc(item.get("editorial_summary_he") or item.get("summary"))}</p>'
        f'<p class="research-caveat">{esc(item.get("content_caveat_he"))}</p>'
        f'<div class="research-actions"><a href="{esc(item.get("url"))}" target="_blank" rel="noopener">פתיחת כתבת המקור</a>{navigation}</div>'
        '</div></article>'
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    index_path = root / "index.html"
    research_path = root / "data" / "research-candidates.json"
    document = json.loads(research_path.read_text(encoding="utf-8"))
    routes = document["routes"]
    with_navigation = sum(bool(item.get("recovered_navigation_links")) for item in routes)
    regions = sorted({str(item.get("region") or "לא זוהה") for item in routes})
    region_options = "".join(f'<option value="{esc(region)}">{esc(region)}</option>' for region in regions)
    cards = "".join(build_card(item, index) for index, item in enumerate(routes, start=1))
    section = (
        '<section class="wrap research-note" id="research-library" aria-labelledby="research-title">'
        '<details class="research-library"><summary><span><b id="research-title">100 מסלולים נוספים למחקר</b>'
        '<small>ספרייה נפרדת — לא חלק מ־339 כרטיסי הטיול המאומתים</small></span><span class="research-count-badge">100</span></summary>'
        '<div class="research-library-body"><div class="research-warning"><b>חשוב:</b> אלה מקורות 4X4 שנשמרו להרחבת המבחר. '
        'הם אינם המלצה לרכיבה, ההתאמה לאופנוע לא אומתה, וקובץ GPX שאותר טכנית אינו מוכיח חוקיות, עבירות או בטיחות.</div>'
        '<div class="research-filters"><label>חיפוש בספריית המחקר<input id="researchQuery" type="search" placeholder="שם מסלול, אזור או נקודת עניין"></label>'
        f'<label>אזור<select id="researchRegion"><option value="">כל האזורים</option>{region_options}</select></label>'
        '<label class="research-check"><input id="researchNavigationOnly" type="checkbox">רק מקורות עם קובץ ניווט שאותר</label>'
        f'<strong id="researchResultCount">{len(routes)} מתוך {len(routes)} מקורות</strong></div>'
        f'<div class="research-grid">{cards}</div><div class="research-empty" id="researchEmpty" hidden>לא נמצאו מקורות שתואמים לחיפוש.</div>'
        f'<p class="research-source-note">{with_navigation} מקורות כוללים קישור ניווט שאותר טכנית; '
        f'{len(routes) - with_navigation} ללא קישור כזה. <a href="./data/research-candidates.json">פתיחת נתוני המחקר המלאים (JSON)</a> · '
        '<a href="./data/unavailable-tracks.json">Tracks שאינם זמינים</a></p></div></details></section>'
    )
    index = index_path.read_text(encoding="utf-8")
    updated, count = SECTION_RE.subn(section, index, count=1)
    if count != 1:
        raise RuntimeError(f"expected one research section, found {count}")
    index_path.write_text(updated, encoding="utf-8")
    document["title"] = f"מועמדי מחקר שנשמרו מחוץ לקטלוג הראשי — גרסת מסמך {RESEARCH_DOCUMENT_VERSION}"
    document["document_version"] = RESEARCH_DOCUMENT_VERSION
    document["product_version"] = PRODUCT_VERSION
    document["count"] = len(routes)
    document["navigation_links_discovered"] = with_navigation
    research_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"researchCards": len(routes), "withNavigation": with_navigation}, ensure_ascii=False))


if __name__ == "__main__":
    main()
