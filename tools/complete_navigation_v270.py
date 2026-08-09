"""השלמת ניווט ל־59 כרטיסים — גרסת מסמך 1.0.2; גרסת מוצר 2.7.0."""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_VERSION = "2.7.0"
DOCUMENT_VERSION = "2.5.0"
ROUTES_DOCUMENT_VERSION = "2.3.0"
NAV_DOCUMENT_VERSION = "1.0.0"


def google_directions(origin: str, destination: str, *waypoints: str) -> str:
    params = {
        "api": "1",
        "origin": origin,
        "destination": destination,
        "travelmode": "driving",
    }
    if waypoints:
        params["waypoints"] = "|".join(waypoints)
    return "https://www.google.com/maps/dir/?" + urllib.parse.urlencode(params)


def google_search(query: str) -> str:
    return "https://www.google.com/maps/search/?" + urllib.parse.urlencode({"api": "1", "query": query})


OFFROAD = {
    93: ("6213988154867712", "תיאור סרטון המקור כולל קישור Off‑Road למסלול ״מחליקים אל המדבר״."),
    99: ("6577012560625664", "שם ההקלטה, הקצה המערבי, מקורות הירקון ותוואי הגאומטריה תואמים לכרטיס."),
    131: ("6210650408222720", "שם ההקלטה הוא ״לטרון למבוא חורון״ ותוואי המפה נפתח ונבדק."),
    170: ("6154984548466688", "תיאור סרטון המקור כולל קישור Off‑Road ל״ים החולות הגדול״."),
    193: ("4915330288451584", "תיאור סרטון המקור כולל קישור Off‑Road לנחל אמציהו ומעלה חצרה."),
    204: ("6213988154867712", "תיאור סרטון המקור כולל קישור Off‑Road למסלול ״מחליקים אל המדבר״."),
    210: ("5529651773177856", "תיאור סרטון המקור כולל קישור Off‑Road לנחל נקרות."),
    211: ("4915330288451584", "תיאור סרטון המקור כולל קישור Off‑Road לנחל אמציהו ומעלה חצרה."),
    214: ("6213988154867712", "תיאור סרטון המקור כולל קישור Off‑Road למסלול העונתי אחרי גשם."),
    215: ("4990937580961792", "תיאור הסרטון מפרט ערד, הר כיפון, נחל חמר, נחל סדום ומישור עמיעז ומקשר ל־Off‑Road."),
    216: ("4990937580961792", "תיאור הסרטון מפרט ערד, הר כיפון, נחל חמר, נחל סדום ומישור עמיעז ומקשר ל־Off‑Road."),
    218: ("5184467687440384", "הקלטת Off‑Road כוללת את מעיין מח״ר ותוואי הגאומטריה עובר בסמוך אליו."),
    221: ("4828634172620800", "תיאור סרטון המקור כולל קישור Off‑Road לאלכסנדרוני והג׳יפטליק."),
    238: ("4724504616763392", "תיאור סרטון המקור כולל קישור Off‑Road לדרך שמוט, מעלה מכוך ומעלה כוכב השחר."),
    249: ("5856218108919808", "תיאור סרטון המקור כולל קישור Off‑Road למרסבא ולסיבוב האתגרי."),
    272: ("4754005916647424", "תיאור סרטון המקור כולל קישור Off‑Road למסלול העליות והירידות סביב סרטבה."),
    278: ("5168691605667840", "תיאור סרטון המקור כולל קישור Off‑Road לנחל נעמ״ה ולמעלות הבקעה."),
    281: ("4797816835407872", "שם ההקלטה ותוואי הגאומטריה כוללים פצאל, סרטבה ועוג׳ה."),
    286: ("4842310306889728", "תיאור סרטון המקור כולל קישור Off‑Road לשדות הטבק ולעין יהודה."),
    294: ("6315700405403648", "תיאור סרטון המקור כולל קישור Off‑Road לעליות ולמורדות סביב נחל ערוגות."),
}


FILES = {
    48: {
        "name": "route-048-zippori.gpx",
        "url": "https://www.kkl.org.il/travel/files/Navigation_files_trips/2702/Zippori.gpx",
        "externalOnly": True,
        "label": "GPX רשמי — דרך נוף יערות ציפורי",
        "basis": "קובץ GPX שפורסם בעמוד המסלול הרשמי של קק״ל; 16 ק״מ ו־3–5 שעות לפי המקור.",
    },
    49: {
        "name": "route-048-zippori.gpx",
        "url": "https://www.kkl.org.il/travel/files/Navigation_files_trips/2702/Zippori.gpx",
        "externalOnly": True,
        "label": "GPX רשמי — דרך נוף יערות ציפורי",
        "basis": "הכרטיס מתאר את הכניסה המערבית לאותו מסלול קק״ל; חובר לקובץ ה־GPX הרשמי.",
    },
    52: {
        "name": "route-052-shaar-hagay.gpx",
        "url": "https://drive.google.com/uc?export=download&id=1EKMaoLfb8BXHoS6sGwzilewnjKWWzGDp",
        "label": "GPX מקור — מצפור שער הגיא ונחלי מאיר–נחשון",
        "basis": "קובץ המקור נפתח כ־GPX תקין: 577 נקודות ואורך גאומטרי 10.1 ק״מ.",
    },
    158: {
        "name": "route-158-park-canada.gpx",
        "url": "https://drive.google.com/uc?export=download&id=1KmA_2fhGSXyqJxiw42iGNnluOw8-yWPP",
        "label": "GPX מקור — סובב פארק קנדה",
        "basis": "קובץ המקור נפתח כ־GPX תקין: 1,716 נקודות, מסלול מעגלי ואורך גאומטרי 9.7 ק״מ.",
    },
    171: {
        "name": "route-171-ashalim-shivta.gpx",
        "url": "https://www.4x4.co.il/files/%D7%9E%D7%A1%D7%9C%D7%95%D7%9C_%D7%98%D7%99%D7%95%D7%9C%20%D7%9E%D7%90%D7%A9%D7%9C%D7%99%D7%9D%20%D7%9C%D7%A9%D7%91%D7%98%D7%94%20-%20%D7%90%D7%AA%D7%A8%20%D7%94%D7%A9%D7%98%D7%97.gpx",
        "label": "GPX מקור — אשלים לשבטה",
        "basis": "קובץ ה־GPX פורסם בכתבת המקור ונפתח בפועל; הקו שנשמר הוא 47.4 ק״מ ולכן אינו מחליף את נתון 61 הק״מ שבכרטיס.",
    },
    176: {
        "name": "route-176-yatir.kmz",
        "url": "https://www.kkl.org.il/travel/files/Navigation_files_trips/2048/2048_KMZ.kmz",
        "externalOnly": True,
        "label": "KMZ רשמי — יער יתיר והר עמשא",
        "basis": "קובץ ניווט KMZ שפורסם בעמוד המסלול הרשמי של קק״ל.",
    },
    194: {
        "name": "route-194-roy-shapira.gpx",
        "url": "https://drive.google.com/uc?export=download&id=19A8FQHkd-eukjvpoJLPsHi1yzE-2ivHc",
        "label": "GPX מקור — הקפה ארוכה, רועי שפירא",
        "basis": "קובץ המקור נפתח כ־GPX תקין: 1,248 נקודות, מסלול מעגלי ואורך גאומטרי 15.3 ק״מ.",
    },
    228: {
        "name": "route-228-amir-felman.gpx",
        "url": "https://drive.google.com/uc?export=download&id=16QJfP4WbGD-kaEjc_pn8TdD0wF1iPU1T",
        "label": "GPX מקור — אמיר פלמן",
        "basis": "קובץ המקור נפתח כ־GPX תקין: 1,172 נקודות ואורך גאומטרי 10.4 ק״מ.",
    },
    269: {
        "name": "route-269-yaniv-yarimi.gpx",
        "url": "https://drive.google.com/uc?export=download&id=1_sFHnFUmIvSYqZz-oxBd4iVFbOm9slvF",
        "label": "GPX מקור — יניב ירימי",
        "basis": "קובץ המקור נפתח כ־GPX תקין: 336 נקודות ואורך גאומטרי 10.1 ק״מ.",
    },
    287: {
        "name": "route-287-lena-draft.gpx",
        "url": "https://drive.google.com/uc?export=download&id=10f87k8mJcAJGq2JdNxnPzM5dmQAdYqls",
        "label": "GPX מקור — טיוטת לנה",
        "basis": "קובץ המקור נפתח כ־GPX תקין: 2,603 נקודות ואורך גאומטרי 10.1 ק״מ; הוא נשאר מסומן כטיוטה.",
    },
    293: {
        "name": "route-293-assaf-birger.gpx",
        "url": "https://drive.google.com/uc?export=download&id=1GbPX7z1t4zyrt2rrzeuIq3IBK4pKjV0X",
        "label": "GPX מקור — אסף בירגר, מסלול מורחב",
        "basis": "קובץ המקור נפתח כ־GPX תקין: 2,003 נקודות ואורך גאומטרי 20.8 ק״מ.",
    },
    295: {
        "name": "route-295-navigation-120.gpx",
        "url": "https://drive.google.com/uc?export=download&id=1rgMuNp1YCuwXh7woK292UVcLh2FsRoXy",
        "label": "GPX מקור — משימת ניווט 120",
        "basis": "קובץ המקור נפתח כ־GPX תקין: 631 נקודות ואורך גאומטרי 17.9 ק״מ.",
    },
    296: {
        "name": "route-296-mishlat-yad.gpx",
        "url": "https://drive.google.com/uc?export=download&id=1H7obQuhNNNhuPNDpqHZ3dFMLxOyCzy4L",
        "label": "GPX מקור — משלט י״ד ודרך הנוף הדרומית",
        "basis": "קובץ המקור נפתח כ־GPX תקין: 515 נקודות ואורך גאומטרי 12.4 ק״מ.",
    },
    300: {
        "name": "route-300-ein-iyov.gpx",
        "url": "https://drive.google.com/uc?export=download&id=1o0T2hKMe23OTKIoUt9WvvBKSVdYTWzRS",
        "label": "GPX מקור — עין איוב ורכס התותחים",
        "basis": "קובץ המקור נפתח כ־GPX תקין: 505 נקודות ואורך גאומטרי 11.4 ק״מ.",
    },
    302: {
        "name": "route-302-cannon-ridge.gpx",
        "url": "https://drive.google.com/uc?export=download&id=1BujmFOaUp9lkF9PDiczP6oS_JpnPl63a",
        "label": "GPX מקור — רכס התותחים ועמק המעיינות",
        "basis": "קובץ המקור נפתח כ־GPX תקין: 430 נקודות ואורך גאומטרי 11.1 ק״מ.",
    },
    304: {
        "name": "route-304-tel-aqed.gpx",
        "url": "https://drive.google.com/uc?export=download&id=1bJNRorHU2FuZq-doITEZ6VuezSDw0avx",
        "label": "GPX מקור — תל עקד, עין יוני ועמק המעיינות",
        "basis": "קובץ המקור נפתח כ־GPX תקין: 994 נקודות ואורך גאומטרי 10.5 ק״מ.",
    },
}


GOOGLE_FULL = {
    27: (
        google_directions("סרטבה, ישראל", "הר הגלבוע, ישראל", "מאגר תרצה", "גן השלושה הסחנה"),
        "Google Maps — מסלול כבישי דרך נקודות היום",
        "הכרטיס מתאר יום כבישי; נקודות סרטבה, מאגר תרצה, הסחנה והגלבוע הוזנו בסדר המתועד.",
    ),
    177: (
        "https://www.google.com/maps/dir/?api=1&origin=Paz+Hof+HaCarmel&destination=Meitar+Country+Club&waypoints=Cici+Bar+Kfar+Chabad%7CBeit+Kama+Junction%7CNova+Memorial+Reim&travelmode=driving",
        "Google Maps — חוף הכרמל עד מיתר",
        "קישור המקור כולל מוצא, יעד ושלוש נקודות דרך תואמות לכותרת.",
    ),
    200: (
        google_directions("ניצנה, ישראל", "מצפור בר לב כביש 10", "עזוז, ישראל"),
        "Google Maps — גישה לקטע הצפוני של כביש 10",
        "הקישור מחבר את נקודות הכביש המתועדות; פתיחת כביש 10 מחייבת בדיקה עדכנית.",
    ),
    201: (
        google_directions("ניצנה, ישראל", "צומת הרוחות, ישראל", "הר חריף"),
        "Google Maps — ניצנה, הר חריף וצומת הרוחות",
        "נקודות הדרך הוזנו לפי הכרטיס; Google עשוי לשנות את הנתיב אם כביש 10 סגור.",
    ),
    246: (
        "https://maps.app.goo.gl/Lrc5k9AhQHEh1jJc7?g_st=ic",
        "Google Maps — יקום לסחנה דרך בקעת הירדן",
        "זהו קישור Google Maps ששורשר במקור הכרטיס ונפתח כקישור מסלול.",
    ),
}


ACCESS_ONLY = {
    21: (google_directions("כפר קיש, ישראל", "גן לאומי כוכב הירדן", "שמורת טבע נחל תבור"), "גישה לנחל תבור ולכוכב הירדן"),
    34: (google_directions("אליקים, ישראל", "פארק רמת מנשה", "יער קרן הכרמל"), "גישה לאליקים, קרן הכרמל ורמת מנשה"),
    45: (google_directions("חיפה, ישראל", "עין הוד, ישראל", "מצפה עופר"), "גישה מחיפה דרך יער עופר לעין הוד"),
    53: (google_directions("דרך נוף כרמל", "אליקים, ישראל", "יקנעם, ישראל"), "גישה לנוף כרמל, יקנעם ואליקים"),
    115: (google_directions("הקסטל, ישראל", "עין נקופה", "מעלה החמישה"), "גישה להקסטל, מעלה החמישה ועין נקופה"),
    121: (google_directions("אלונית טל שחר", "אלונית טל שחר", "נחל שורק ליד טל שחר", "יער צרעה"), "לולאת גישה סביב טל שחר"),
    126: (google_directions("לטרון, ישראל", "תחנת דלק תעוז", "פארק קנדה"), "גישה מלטרון לתעוז"),
    143: (google_directions("לטרון, ישראל", "כרמי יוסף, ישראל", "תעוז, ישראל"), "גישה מלטרון דרך תעוז לכרמי יוסף"),
    179: (google_directions("צומת בית קמה", "יער יתיר", "יער להב"), "גישה מבית קמה דרך יער להב ליער יתיר"),
    185: (google_directions("פז רופין", "שמורת טבע נחל תנינים", "רמת מנשה", "פארק אלונה"), "גישה מפז רופין לנחל תנינים"),
    192: (google_directions("דריג'את, ישראל", "ים המלח", "ערד, ישראל", "ראש זוהר"), "גישה מדריג׳את/ערד דרך ראש זוהר לים המלח"),
    203: (google_directions("אילת, ישראל", "צומת שיזפון", "פארק תמנע"), "גישה מאילת צפונה"),
    206: (google_directions("מצוקי דרגות", "ערד, ישראל", "עין גדי"), "גישה ממצוקי דרגות לערד"),
    217: (google_search("שביל מטמור אבן חול קווארצית כביש 225"), "נקודת ההתחלה הרשמית של שביל מטמור"),
    229: (google_directions("קאסר אל יהוד", "מבצר דוק יריחו", "מבצר קיפרוס יריחו"), "גישה לארץ המנזרים ולמבצרים"),
    253: (google_directions("מישור אדומים", "נבי מוסא", "צומת אלמוג", "קליה"), "גישה למישור אדומים, אלמוג, קליה ונבי מוסא"),
    282: (google_directions("קריית חרושת, ישראל", "32.789395,35.027927", "אלוני אבא"), "גישה מקריית חרושת לבאר אבא"),
}


MISSING = {
    289: "למקור אין אזור, נקודת התחלה, נקודת סיום או קובץ. הוספת מפה במקרה זה תהיה המצאה; הכרטיס הועבר למצב טיוטה שאינה מוכנה ליציאה.",
}


REGION_FIXES = {
    52: ("מרכז", "לטרון, שפלת יהודה והרי ירושלים"),
    158: ("מרכז", "לטרון, שפלת יהודה והרי ירושלים"),
    185: ("צפון", "עמק המעיינות, רמות מנשה והכרמל"),
    194: ("מרכז", "לטרון, שפלת יהודה והרי ירושלים"),
    228: ("מרכז", "לטרון, שפלת יהודה והרי ירושלים"),
    269: ("מרכז", "לטרון, שפלת יהודה והרי ירושלים"),
    282: ("צפון", "כרמל, רמות מנשה והעמקים"),
    286: ("דרום ומדבר", "שומרון, בקעת הירדן ומדבר יהודה"),
    287: ("מרכז", "לטרון, שפלת יהודה והרי ירושלים"),
    293: ("מרכז", "לטרון, שפלת יהודה והרי ירושלים"),
    295: ("מרכז", "לטרון, שפלת יהודה והרי ירושלים"),
    296: ("מרכז", "לטרון, שפלת יהודה והרי ירושלים"),
    300: ("מרכז", "לטרון, שפלת יהודה והרי ירושלים"),
    302: ("מרכז", "לטרון, שפלת יהודה והרי ירושלים"),
    304: ("מרכז", "לטרון, שפלת יהודה והרי ירושלים"),
}


def download_sources() -> dict[int, dict]:
    output_dir = ROOT / "assets" / "navigation"
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: dict[int, dict] = {}
    cached_names: set[str] = set()
    for ordinal, item in FILES.items():
        target = output_dir / item["name"]
        if item.get("externalOnly"):
            downloaded[ordinal] = {
                "localUrl": item["url"],
                "bytes": None,
                "sha256": None,
            }
            continue
        if item["name"] not in cached_names:
            request = urllib.request.Request(item["url"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
            if len(payload) < 500:
                raise RuntimeError(f"download too small for route {ordinal}: {len(payload)} bytes")
            if target.suffix.lower() == ".gpx" and b"<gpx" not in payload[:5000].lower():
                raise RuntimeError(f"download is not GPX for route {ordinal}")
            if target.suffix.lower() == ".kmz" and not payload.startswith(b"PK"):
                raise RuntimeError(f"download is not KMZ for route {ordinal}")
            target.write_bytes(payload)
            cached_names.add(item["name"])
        downloaded[ordinal] = {
            "localUrl": f"./assets/navigation/{item['name']}",
            "bytes": target.stat().st_size,
            "sha256": __import__("hashlib").sha256(target.read_bytes()).hexdigest(),
        }
    return downloaded


def record_for_route(route: dict, downloaded: dict[int, dict]) -> dict:
    ordinal = int(route["ordinal"])
    base = {"routeId": route["id"], "ordinal": ordinal, "title": route["title"]}
    if ordinal in OFFROAD:
        track_id, basis = OFFROAD[ordinal]
        return base | {
            "type": "offroad-track",
            "coverage": "full-track",
            "provider": "Off-Road",
            "url": f"https://off-road.io/track/{track_id}",
            "trackId": track_id,
            "label": "פתיחת המסלול ב־Off‑Road",
            "verificationBasis": basis,
        }
    if ordinal in FILES:
        item = FILES[ordinal]
        return base | {
            "type": "route-file",
            "coverage": "full-track",
            "provider": "GPX" if item["name"].endswith(".gpx") else "KMZ",
            "url": downloaded[ordinal]["localUrl"],
            "sourceUrl": item["url"],
            "label": item["label"],
            "verificationBasis": item["basis"],
            "bytes": downloaded[ordinal]["bytes"],
            "sha256": downloaded[ordinal]["sha256"],
        }
    if ordinal in GOOGLE_FULL:
        url, label, basis = GOOGLE_FULL[ordinal]
        return base | {
            "type": "google-directions",
            "coverage": "road-route",
            "provider": "Google Maps",
            "url": url,
            "label": label,
            "verificationBasis": basis,
        }
    if ordinal in ACCESS_ONLY:
        url, label = ACCESS_ONLY[ordinal]
        return base | {
            "type": "google-access",
            "coverage": "access-only",
            "provider": "Google Maps",
            "url": url,
            "label": label,
            "verificationBasis": "הנקודות נלקחו מן הכותרת ומתיאור הכרטיס. Google Maps משמש לגישה בלבד ואינו משחזר את תוואי השטח.",
        }
    if ordinal in MISSING:
        return base | {
            "type": "unresolved",
            "coverage": "none",
            "provider": None,
            "url": None,
            "label": "אין מספיק נתונים לבניית מפה",
            "verificationBasis": MISSING[ordinal],
        }
    raise RuntimeError(f"route {ordinal} missing navigation decision")


def section_html(record: dict) -> str:
    coverage = record["coverage"]
    if coverage == "full-track":
        title = "ניווט מלא שנמצא ואומת"
        note = "זהו תוואי מסלול, אך עדיין חובה לבדוק פתיחה, חוקיות, שערים, שטחי אש ותנאי יום לפני יציאה."
        action = html.escape(record["label"])
    elif coverage == "road-route":
        title = "מסלול Google Maps שנבנה מן הנקודות המתועדות"
        note = "זהו ניווט כבישי. יש לבדוק את המסלול שמציע Google לפני היציאה ואת זמינות הכבישים ביום הטיול."
        action = html.escape(record["label"])
    elif coverage == "access-only":
        title = "מפת גישה ונקודות דרך — לא תוואי שטח"
        note = "הקישור עוזר להגיע לנקודות המתועדות, אך אינו מחליף GPX או מפת Off‑Road. אין לנווט לפיו בתוך השטח."
        action = html.escape(record["label"])
    else:
        return (
            '<section class="navigation-supplement unresolved" data-navigation-coverage="none">'
            '<h3>טיוטה שאינה מוכנה ליציאה</h3>'
            f'<p>{html.escape(record["verificationBasis"])}</p>'
            '<p class="navigation-warning"><b>מה צריך להשלים:</b> אזור או נקודת התחלה, יעד וקובץ GPX/קישור Off‑Road מן המקור.</p>'
            '</section>'
        )
    href = html.escape(record["url"], quote=True)
    download = " download" if record["type"] == "route-file" else ""
    usage = ""
    if record["type"] == "route-file":
        usage = (
            '<ol class="navigation-steps"><li>לחצו על הורדת הקובץ.</li>'
            '<li>בטלפון פתחו או שתפו אותו לאפליקציית Off‑Road/ניווט שתומכת GPX או KMZ.</li>'
            '<li>ודאו באפליקציה שהשם, האזור והקו תואמים לכרטיס לפני יציאה.</li></ol>'
        )
    return (
        f'<section class="navigation-supplement {html.escape(coverage)}" data-navigation-coverage="{html.escape(coverage)}">'
        f'<h3>{title}</h3><p>{html.escape(record["verificationBasis"])}</p>'
        f'<p class="navigation-warning">{note}</p>{usage}'
        f'<div class="navigation-actions"><a class="navigation-primary" href="{href}" target="_blank" rel="noopener noreferrer"{download}>{action}</a></div>'
        '</section>'
    )


def update_index(records: list[dict]) -> None:
    path = ROOT / "index.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace("2.6.0", PRODUCT_VERSION).replace("2.4.0", DOCUMENT_VERSION)
    text = text.replace("מהדורה 2.6 מוסיפה", "מהדורה 2.7 מוסיפה")
    text = text.replace('<div class="quality-number">2.6</div>', '<div class="quality-number">2.7</div>')
    text = text.replace(
        "מהדורה מלאה עם 339 כרטיסי טיול, ספריית מחקר ויומן שטח מקומי.",
        "מהדורה מלאה עם 339 כרטיסים, ניווט משלים, ספריית מחקר ויומן שטח מקומי.",
    )
    text = text.replace('<div class="stat"><b>280</b>כרטיסים עם ניווט</div>', '<div class="stat"><b>321</b>כרטיסים עם תוואי/מסלול</div><div class="stat"><b>17</b>מפות גישה בלבד</div>')
    old_transparency = '<div><b>280</b><span>כרטיסים עם ניווט</span></div>'
    text = text.replace(old_transparency, '<div><b>321</b><span>עם תוואי או מסלול כבישי</span></div>')
    text = text.replace('<div><b>59</b><span>ללא ניווט מאומת</span></div>', '<div><b>17</b><span>עם מפת גישה בלבד</span></div><div><b>1</b><span>טיוטה ללא אזור למיפוי</span></div>')
    marker = '<section class="wrap data-transparency"'
    release = (
        '<section class="wrap navigation-release" aria-labelledby="navigation-release-title">'
        '<h2 id="navigation-release-title">מהדורת ניווט: 58 מתוך 59 הכרטיסים קיבלו מפה שימושית</h2>'
        '<p><b>20</b> כרטיסים חוברו ל־Off‑Road, <b>16</b> לקובצי GPX/KMZ: 13 נשמרו באתר ושלושה נפתחים ממקור קק״ל הרשמי, '
        '<b>5</b> למסלולי Google Maps כבישיים ו־<b>17</b> למפות גישה שמסומנות במפורש ככאלה. '
        'כרטיס אחד נשאר טיוטה מפני שאין במקור אפילו אזור או נקודת מוצא; לא הומצאה עבורו מפה.</p>'
        '<p><a href="./data/navigation-supplements.json">דוח הניווט המלא — כל 59 ההחלטות והמקורות</a></p></section>'
    )
    if "navigation-release-title" not in text:
        text = text.replace(marker, release + marker, 1)

    for record in records:
        route_id = re.escape(record["routeId"])
        match = re.search(rf'<details class="route-card" id="{route_id}".*?</details>', text, re.DOTALL)
        if not match:
            raise RuntimeError(f"card not found: {record['routeId']}")
        block = match.group(0)
        if "navigation-supplement" in block:
            raise RuntimeError(f"navigation already inserted: {record['routeId']}")
        if record["coverage"] != "none":
            block = block.replace('data-map="0"', 'data-map="1"', 1)
        chip = {
            "full-track": "תוואי ניווט מאומת",
            "road-route": "מסלול Google מאומת",
            "access-only": "מפת גישה בלבד",
            "none": "טיוטה ללא מיקום",
        }[record["coverage"]]
        block = block.replace('<span class="no-map">ללא ניווט מאומת</span>', f'<span class="nav-supplement-chip">{chip}</span>', 1)
        closing = block.rfind("</div></details>")
        if closing < 0:
            raise RuntimeError(f"route body closing not found: {record['routeId']}")
        block = block[:closing] + section_html(record) + block[closing:]
        text = text[:match.start()] + block + text[match.end():]
    path.write_text(text, encoding="utf-8")


def update_routes(records: list[dict]) -> None:
    path = ROOT / "data" / "routes.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    by_ordinal = {int(record["ordinal"]): record for record in records}
    for route in document["routes"]:
        ordinal = int(route["ordinal"])
        if ordinal not in by_ordinal:
            continue
        record = by_ordinal[ordinal]
        map_info = route.setdefault("map", {})
        if record["type"] == "offroad-track":
            map_info.update({"hasMap": True, "trackIds": [record["trackId"]]})
        elif record["type"] == "route-file":
            map_info.update({
                "hasFileNavigation": True,
                "fileNavigationStatus": "verified",
                "fileNavigationUrl": record["url"],
                "fileNavigationFormat": record["provider"],
            })
        elif record["type"] == "google-directions":
            map_info.update({"hasDirections": True, "directionsStatus": "verified", "directionsUrl": record["url"]})
        elif record["type"] == "google-access":
            map_info.update({"hasAccessMap": True, "accessMapStatus": "verified-access-only", "accessMapUrl": record["url"]})
        route["navigationSupplement"] = {
            key: record.get(key)
            for key in ("type", "coverage", "provider", "url", "trackId", "label", "verificationBasis")
            if record.get(key) is not None
        }
        if ordinal in REGION_FIXES:
            route["region"], route["subregion"] = REGION_FIXES[ordinal]
        if ordinal == 289:
            route["status"] = "טיוטה — חסרים אזור וקובץ ניווט"
            route["quality"] = "לא מוכן ליציאה"
            route["lengthTimeDisplay"] = "60–70 ק״מ · 2 שעות ו־45 דקות לפי דיווח המקור"
            route["distanceKm"] = 60.0
            route["sourceDurationDisplay"] = "2 שעות ו־45 דקות כולל הפסקה"
    document["title"] = f"נתוני ספר המסלולים — גרסת מסמך {ROUTES_DOCUMENT_VERSION}"
    document["productVersion"] = PRODUCT_VERSION
    document["documentVersion"] = ROUTES_DOCUMENT_VERSION
    document["generatedAt"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    document["navigationCoverage"] = {
        "fullOrRoadRoute": 321,
        "accessOnly": 17,
        "unresolved": 1,
        "supplementedThisRelease": 59,
    }
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_versions_and_styles(records: list[dict]) -> None:
    replacements = {
        ROOT / "assets" / "js" / "app.js": [("2.6.0", PRODUCT_VERSION), ("2.4.0", DOCUMENT_VERSION)],
        ROOT / "assets" / "js" / "field-notes.js": [("2.6.0", PRODUCT_VERSION), ("2.4.0", DOCUMENT_VERSION)],
        ROOT / "assets" / "css" / "app.css": [("2.6.0", PRODUCT_VERSION), ("2.4.0", DOCUMENT_VERSION)],
        ROOT / "offline.html": [("2.6.0", PRODUCT_VERSION), ("2.4.0", DOCUMENT_VERSION)],
    }
    for path, pairs in replacements.items():
        value = path.read_text(encoding="utf-8")
        for old, new in pairs:
            value = value.replace(old, new)
        path.write_text(value, encoding="utf-8")

    css_path = ROOT / "assets" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    styles = """

/* ניווט משלים — גרסת מסמך 2.5.0; גרסת מוצר 2.7.0 */
.navigation-release{margin-block:18px;padding:20px;border:1px solid var(--line);border-radius:var(--radius);background:linear-gradient(135deg,color-mix(in srgb,var(--surface) 88%,var(--success)),var(--surface));box-shadow:var(--shadow-soft)}
.navigation-release h2{margin-top:0;color:var(--forest)}
.navigation-supplement{clear:both;margin:18px 0;padding:16px;border:1px solid color-mix(in srgb,var(--success) 42%,var(--line));border-right:6px solid var(--success);border-radius:15px;background:color-mix(in srgb,var(--surface) 92%,var(--success));overflow-wrap:anywhere}
.navigation-supplement.google-access,.navigation-supplement.access-only{border-right-color:var(--warning);background:color-mix(in srgb,var(--surface) 93%,var(--sand))}
.navigation-supplement.unresolved{border-right-color:var(--danger);background:color-mix(in srgb,var(--surface) 92%,var(--danger))}
.navigation-supplement h3{margin:0 0 8px;color:var(--forest)}
.navigation-warning{font-weight:700}
.navigation-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.navigation-primary{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:10px 15px;border-radius:11px;background:var(--forest);color:#fff!important;text-decoration:none;font-weight:800}
.navigation-primary:hover{background:var(--forest-deep)}
.navigation-steps{margin:10px 0;padding-inline-start:22px}
.nav-supplement-chip{background:color-mix(in srgb,var(--success) 20%,var(--surface))!important;border-color:color-mix(in srgb,var(--success) 55%,var(--line))!important;color:var(--ink)!important}
@media(max-width:600px){.navigation-supplement{padding:13px}.navigation-primary{width:100%}}
"""
    if "ניווט משלים — גרסת מסמך" not in css:
        css_path.write_text(css + styles, encoding="utf-8")

    manifest_path = ROOT / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["name"] = f"ספר מסלולי האדוונצ׳ר והאופרוד בישראל של אילן · גרסת מסמך {DOCUMENT_VERSION}"
    manifest["description"] = "מדריך קהילתי עם ניווט Off-Road, קובצי GPX/KMZ, מפות גישה, יומן שטח, ביקורות, הזמנות WhatsApp, ייצוא HTML, בטיחות ו-AI מקומי"
    manifest["version"] = PRODUCT_VERSION
    manifest["document_version"] = DOCUMENT_VERSION
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sw_path = ROOT / "sw.js"
    sw = sw_path.read_text(encoding="utf-8").replace("2.6.0", PRODUCT_VERSION).replace("2.4.0", DOCUMENT_VERSION)
    sw = sw.replace("'./data/route-map-trust-audit.json'", "'./data/route-map-trust-audit.json','./data/navigation-supplements.json'")
    sw_path.write_text(sw, encoding="utf-8")


def write_navigation_document(records: list[dict]) -> None:
    document = {
        "title": f"השלמות ניווט ל־59 כרטיסים — גרסת מסמך {NAV_DOCUMENT_VERSION}",
        "productVersion": PRODUCT_VERSION,
        "documentVersion": NAV_DOCUMENT_VERSION,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "policy": "Off-Road ממקור תואם קודם; אחריו GPX/KMZ שנפתחו; Google למסלול כבישי או לגישה בלבד. לא נוצר תוואי שטח משוער.",
        "summary": {
            "reviewed": 59,
            "offRoad": 20,
            "routeFiles": 16,
            "googleRoadRoutes": 5,
            "googleAccessOnly": 17,
            "unresolved": 1,
        },
        "records": records,
    }
    (ROOT / "data" / "navigation-supplements.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def refresh_release_text() -> None:
    path = ROOT / "index.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        '<div class="field"><label for="map">ניווט</label><select id="map"><option value="">עם או בלי ניווט</option><option value="1">כולל ניווט</option><option value="0">ללא ניווט מאומת</option></select></div>',
        '<div class="field"><label for="map">מפה</label><select id="map"><option value="">עם או בלי מפה</option><option value="1">עם תוואי או מפת גישה</option><option value="0">ללא מפה שימושית</option></select></div>',
    )
    text = text.replace(
        '<b>16</b> לקובצי GPX/KMZ שנפתחו ונשמרו באתר,',
        '<b>16</b> לקובצי GPX/KMZ: 13 נשמרו באתר ושלושה נפתחים ממקור קק״ל הרשמי,',
    )
    text, count = re.subn(
        r'<p class="hero-copy">.*?</p>',
        '<p class="hero-copy">מדריך PWA עם 339 כרטיסי טיול אמיתיים: 304 מן המאגר המקורי ועוד 35 Tracks שקיבלו כרטיס מלא. כל 307 מזהי ה־Track שבספר נבדקו מול Off‑Road: 302 זמינים עם מרחק, זמן כשנמסר, פעילות וקושי מן המקור; חמישה מסומנים כלא זמינים. מהדורה 2.7 משלימה ניווט ל־58 מתוך 59 הכרטיסים החסרים ושומרת את יומן השטח המקומי, הביקורות, התמונות, הגיבוי וייצוא ה־HTML.</p>',
        text,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError(f"hero copy replacement count: {count}")
    replacements = {
        '<div class="stat"><b>295</b>מזהי Track שנבדקו</div>': '<div class="stat"><b>307</b>מזהי Track שנבדקו</div>',
        '<div><b>287</b><span>כרטיסים עם מרחק</span></div>': '<div><b>306</b><span>כרטיסים עם מרחק</span></div>',
        '<div><b>259</b><span>כרטיסים עם סיווג קושי מאומת</span></div>': '<div><b>265</b><span>כרטיסים עם סיווג קושי מאומת</span></div>',
        '<div><b>52</b><span>ללא מרחק ידוע</span></div>': '<div><b>33</b><span>ללא מרחק ידוע</span></div>',
        '<div><b>80</b><span>ללא קושי מאומת</span></div>': '<div><b>74</b><span>ללא קושי מאומת</span></div>',
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new, 1)
        elif new not in text:
            raise RuntimeError(f"release statistic missing: {old}")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    routes_document = json.loads((ROOT / "data" / "routes.json").read_text(encoding="utf-8"))
    targets = [
        route for route in routes_document["routes"]
        if not route.get("map", {}).get("hasMap")
        and not (
            route.get("map", {}).get("hasDirections")
            and route.get("map", {}).get("directionsStatus") == "verified"
        )
    ]
    if len(targets) != 59:
        raise RuntimeError(f"expected 59 targets, found {len(targets)}")
    decisions = set(OFFROAD) | set(FILES) | set(GOOGLE_FULL) | set(ACCESS_ONLY) | set(MISSING)
    target_ordinals = {int(route["ordinal"]) for route in targets}
    if decisions != target_ordinals:
        raise RuntimeError(f"decision coverage mismatch: missing={target_ordinals-decisions}, extra={decisions-target_ordinals}")
    downloaded = download_sources()
    records = [record_for_route(route, downloaded) for route in targets]
    write_navigation_document(records)
    update_routes(records)
    update_index(records)
    update_versions_and_styles(records)
    print(json.dumps({
        "productVersion": PRODUCT_VERSION,
        "documentVersion": DOCUMENT_VERSION,
        "reviewed": len(records),
        "offRoad": len(OFFROAD),
        "routeFiles": len(FILES),
        "googleRoadRoutes": len(GOOGLE_FULL),
        "googleAccessOnly": len(ACCESS_ONLY),
        "unresolved": len(MISSING),
    }, ensure_ascii=False))


if __name__ == "__main__":
    if "--refresh-text" in sys.argv:
        refresh_release_text()
    else:
        main()
