# דוח בקרת איכות — גרסת מסמך 2.1.7

גרסת מוצר שנבדקה: **2.1.0**  
גרסת המסמך הראשי: **2.1.4**  
תוצאה: **עבר — 68/68 בדיקות עברו**

## ספירות מאומתות

- כרטיסים: 339.
- כרטיסים מן המאגר המקורי: 304.
- כרטיסי Off‑Road חדשים שאומתו: 35.
- כרטיסים עם ניווט: 276.
- מזהי Track פעילים וייחודיים בקטלוג: 295.
- חלוקת שלמות: {"כרטיס שימושי חלקית": 189, "כרטיס מלא": 69, "מידע חסר": 74, "סגור / לא זמין": 7}.

## בדיקות

1. **עבר — 339 route cards**: found 339
2. **עבר — 304 legacy cards**: found 304
3. **עבר — 35 verified Off-Road cards**: found 35
4. **עבר — unique route ids**: unique 339
5. **עבר — research cards removed from catalog**: no research lead rendered as a route
6. **עבר — old appendix removed**: appendix is absent
7. **עבר — legacy ids and order preserved**: preserved 304 ids
8. **עבר — every card has an image**: images 339/339
9. **עבר — every route image has alt**: all route images have alt attributes
10. **עבר — HTML export on every card**: found 339
11. **עבר — invite generator on every card**: found 339
12. **עבר — closed routes keep invite disabled**: disabled 7
13. **עבר — 276 cards with navigation**: found 276
14. **עבר — all new Off-Road cards have map link**: 35/35
15. **עבר — all new Off-Road cards have local QR**: 35/35
16. **עבר — new cards expose distance**: 35/35
17. **עבר — new cards disclose source verification**: 35/35
18. **עבר — new cards include ratings section**: 35/35
19. **עבר — seven verified Off-Road source photos are local**: found 7
20. **עבר — quality classification complete**: {"כרטיס שימושי חלקית": 189, "כרטיס מלא": 69, "מידע חסר": 74, "סגור / לא זמין": 7}
21. **עבר — source classification complete**: all cards have an honest source class
22. **עבר — original order stored**: 1..339
23. **עבר — surface false-positive fixed**: לא צוין
24. **עבר — unverified difficulty stays unknown**: לא אומת
25. **עבר — alternate hard mention no longer overrides primary**: בינוני
26. **עבר — legacy difficulty wording preserved**: 12/12 corrected
27. **עבר — explicit linear route shape takes priority**: 4/4 corrected
28. **עבר — filter and sort controls exist**: q, region, subregion, difficulty, surface, shape, status, quality, source, map, sort, theme
29. **עבר — sort modes are declared**: original, title, region, difficulty, quality, distance-asc, distance-desc
30. **עבר — light theme is first default option**: light, dark, system
31. **עבר — rich invite controls exist**: 14 required controls
32. **עבר — invite date and times disable browser autofill**: ["off", "off", "off", "off"]
33. **עבר — route JSON counts**: 339/304/35
34. **עבר — research archive preserves 100**: found 100
35. **עבר — research navigation status matches links**: {"not_found_in_technical_crawl": 55, "technically_discovered_not_route-verified": 45}
36. **עבר — unavailable archive preserves one**: found 1
37. **עבר — Off-Road evidence preserves 36**: records 36
38. **עבר — JSON documents show versions**: 2.1.4
39. **עבר — safety document versions agree**: 2.1.4/2.1.4 2.1.0/2.1.0
40. **עבר — stale v2.0 QA artifact removed**: qa-result.json absent
41. **עבר — 295 live Track ids in catalog**: found 295
42. **עבר — manifest versions**: 2.1.0/2.1.4
43. **עבר — manifest relative start and scope**: ./ ./
44. **עבר — standalone display**: standalone
45. **עבר — manifest icons exist**: 3 icons
46. **עבר — PWA icon dimensions**: {"./icons/icon-192.png": [192, 192], "./icons/icon-512.png": [512, 512], "./icons/maskable-512.png": [512, 512]}
47. **עבר — service worker versioned**: v2.1 namespace
48. **עבר — service worker deletion scoped**: only own namespace is deleted
49. **עבר — service worker relative shell**: relative app shell
50. **עבר — robots.txt blocks crawling**: exact expected content
51. **עבר — no sitemap**: no sitemap files
52. **עבר — all HTML has exact noindex**: checked 2 HTML files
53. **עבר — all shipped HTML shows document version**: checked 2 HTML files
54. **עבר — main title shows product and document version**: ספר מסלולי האדוונצ׳ר והאופרוד בישראל של אילן · גרסת מוצר 2.1.0 · גרסת מסמך 2.1.4
55. **עבר — support documents show versions**: README_HE.md, CHANGELOG.md, SOURCE_NOTES.md, BUILD_INFO.txt, QA_REPORT.md
56. **עבר — app has real sort implementation**: sortCards and distance modes
57. **עבר — app includes Off-Road maps in invitation**: map list in makeInvite
58. **עבר — app includes poster and HTML export**: poster + export functions
59. **עבר — invite map control resets on every opening**: reset label and disabled state
60. **עבר — invite validates and normalizes time order and whole-number group size**: normalized time order + sanitized integer 1..100
61. **עבר — poster discloses image provenance**: both image states disclosed
62. **עבר — HTML export embeds images concurrently with timeout**: bounded concurrent embedding
63. **עבר — invite errors clear after field correction**: live correction
64. **עבר — poster share has non-cancel fallback**: download + copy fallback
65. **עבר — AI prompt requires unknown answer**: explicit unknown rule
66. **עבר — no private WhatsApp group link embedded**: no private group invite URL
67. **עבר — index local references exist**: all resolved
68. **עבר — no base64 images in main HTML**: assets remain external files

## מגבלות

- בדיקות אלה מאמתות מבנה, נתונים וקבצים מקומיים. מצב מסלול בשטח אינו ניתן לאימות באמצעות הקוד.
- התקנת PWA, Service Worker, תצוגת מובייל, מצב כהה, מחולל ההזמנה וייצוא HTML נבדקים גם בדפדפן בנפרד.
- WhatsApp שולט בתצוגה המקדימה של קישורים; המדריך מספק קישור מפה ישיר אך אינו יכול לכפות תמונת preview בתוך WhatsApp.
