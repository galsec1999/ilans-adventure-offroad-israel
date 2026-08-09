"""שער איכות לאימות תוואי ונקודות ציון — גרסת מסמך 1.0.0; מוצר 2.5.0."""

from __future__ import annotations

import json
import re
from pathlib import Path


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"PASS: {label}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    audit = json.loads((root / "data" / "offroad-geometry-audit.json").read_text(encoding="utf-8"))
    routes = json.loads((root / "data" / "routes.json").read_text(encoding="utf-8"))
    index = (root / "index.html").read_text(encoding="utf-8")
    tracks = audit["tracks"]
    counts = audit["counts"]
    check("גרסת מסמך 1.0.0" in audit["title"], "geometry audit has visible document version")
    check(audit["productVersion"] == "2.5.0", "geometry audit product version")
    check(counts["totalTrackIds"] == 295 and len(tracks) == 295, "all 295 track ids audited")
    check(counts["geometry-verified"] == 285, "285 tracks have internally aligned geometry")
    check(counts["geometry-source-inconsistency"] == 5, "five persistent source inconsistencies are explicit")
    check(counts["source-unavailable"] == 5, "five unavailable sources are explicit")
    opened = [track for track in tracks if track["status"].startswith("geometry-")]
    aligned = [track for track in tracks if track["status"] == "geometry-verified"]
    inconsistent = [track for track in tracks if track["status"] == "geometry-source-inconsistency"]
    check(len(opened) == 290 and all(track.get("pointCount", 0) >= 2 for track in opened), "290 source map layers opened with route points")
    check(sum(track["pointCount"] for track in opened) == 551740, "551740 map points inspected")
    check(counts["osmNamedFeaturesConsidered"] == 20614, "20614 named map features considered")
    check(counts["tracksWithNearbyPlaces"] == 290 and all(track.get("verifiedNearbyPlaces") for track in opened), "every opened map has spatially verified search places")
    check(all((track.get("sourceStartDeltaM") or 0) <= 100 and (track.get("sourceEndDeltaM") or 0) <= 100 for track in aligned), "aligned tracks contain source endpoints")
    check(all((track.get("sourceStartDeltaM") or 0) > 100 or (track.get("sourceEndDeltaM") or 0) > 100 for track in inconsistent), "inconsistent tracks retain measured endpoint evidence")
    check(all(track.get("reason") for track in inconsistent), "each source inconsistency has a concrete reason")
    route_list = routes["routes"]
    check(routes["documentVersion"] == "2.2.2" and "גרסת מסמך 2.2.2" in routes["title"], "routes document version 2.2.2")
    check(sum(bool((route.get("trustAudit") or {}).get("verifiedNearbyPlaces")) for route in route_list) == 272, "272 cards with opened maps contain geometry-derived place indexes")
    cards = re.findall(r'<details class="[^"]*\broute-card\b[^"]*"[^>]*>', index)
    check(len(cards) == 339, "339 HTML route cards remain")
    check(all(len(re.findall(r"\sdata-search=", card)) == 1 for card in cards), "exactly one search index per route card")
    check(index.count('class="geometry-verification') == 276, "276 cards show geometry verification")
    check(index.count('class="geometry-warning') == 5, "five source inconsistencies are visible in cards")
    check("גרסת מוצר 2.5.0" in index and "גרסת מסמך 2.3.2" in index, "main page versions are visible")
    check("בית הקשתות" in next(card for card in cards if 'id="r-c20c0c5507"' in card), "Latrun corrected card indexed by mapped landmark")
    check("נחל אלכסנדר" in next(card for card in cards if 'id="r-7894e9f48d"' in card), "Alexander stream corrected card indexed by mapped landmark")
    check("מצפור קרן הכרמל" in next(card for card in cards if 'id="r-df98cfab89"' in card), "Horshan corrected card indexed by mapped landmark")
    print("PASS: geometry trust quality gate complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
