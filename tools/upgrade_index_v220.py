#!/usr/bin/env python3
"""שדרוג index.html למהדורת המוצר 2.2.0 — גרסת מסמך 1.0.3.

הקובץ הראשי נוצר כשורת HTML ארוכה מאוד. הסקריפט מבצע החלפות מדויקות,
בודק שכל עוגן הופיע פעם אחת בלבד, ושומר UTF-8 בלי לשנות את תוכן הכרטיסים.
"""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    original = subprocess.run(
        ["git", "show", "HEAD:index.html"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    text = original.decode("utf-8")

    if "גרסת מוצר 2.1.0" not in text or "גרסת מסמך 2.1.5" not in text:
        raise RuntimeError("unexpected source versions in index.html")

    text = text.replace("גרסת מוצר 2.1.0", "גרסת מוצר 2.2.0")
    text = text.replace("גרסת מסמך 2.1.5", "גרסת מסמך 2.1.6")

    text = replace_once(
        text,
        '<link rel="stylesheet" href="./assets/css/app.css">',
        '<link rel="stylesheet" href="./assets/css/app.css?v=2.1.6">',
        "stylesheet cache buster",
    )
    text = replace_once(
        text,
        '<script src="./data/offroad-all-metadata.js" defer></script>',
        '<script src="./data/offroad-all-metadata.js?v=2.1.6" defer></script>',
        "metadata cache buster",
    )
    text = replace_once(
        text,
        '<script src="./assets/js/app.js" defer></script>',
        '<script src="./assets/js/app.js?v=2.1.6" defer></script>',
        "application cache buster",
    )
    text = replace_once(
        text,
        '<div class="stat"><b>100</b>מקורות נשמרו למחקר</div>',
        '<div class="stat"><b>100</b>מקורות נשמרו למחקר</div><div class="stat visit-stat"><b id="visitCount">—</b>כניסות שנמדדו<small id="visitCountStatus" aria-live="polite">טוען מונה ציבורי…</small></div>',
        "visit counter card",
    )
    text = replace_once(
        text,
        '<button id="invite-whatsapp" class="whatsapp" type="button">פתיחה ב־WhatsApp</button>',
        '<button id="invite-whatsapp" class="whatsapp" type="button">פתיחה ב־WhatsApp</button><button id="invite-short-whatsapp" class="whatsapp" type="button">WhatsApp — הזמנה קצרה</button><button id="invite-short-copy" type="button">העתקת הזמנה קצרה</button>',
        "short invitation actions",
    )
    text = replace_once(
        text,
        'WhatsApp מקבל טקסט וקישור מפה. כרזת ה־PNG ניתנת לשיתוף בנפרד וכוללת QR למפה. המחולל אינו מאשר את המסלול.',
        'WhatsApp מקבל טקסט וקישור מפה. אפשר לבחור הזמנה עשירה או קצרה. כרזת ה־PNG ניתנת לשיתוף בנפרד וכוללת QR למפה. המחולל אינו מאשר את המסלול.',
        "invitation note",
    )
    text = replace_once(
        text,
        'המחולל אינו מאשר את המסלול.</p>\r\n    </div></div>\r\n    <div class="dialog-shell" id="aiModal"',
        'המחולל אינו מאשר את המסלול.</p>\n    </div></div>\r\n    <div class="dialog-shell" id="aiModal"',
        "changed invitation line ending",
    )

    INDEX.write_bytes(text.encode("utf-8"))
    print("upgraded index.html to product 2.2.0 / document 2.1.6")


if __name__ == "__main__":
    main()
