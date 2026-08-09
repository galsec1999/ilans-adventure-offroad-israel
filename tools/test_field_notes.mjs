/* בדיקות יומן שטח מקומי — גרסת מסמך 1.1.0; גרסת מוצר 2.6.0 */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const qaModules = process.env.ROUTE_NOTES_QA_MODULES;
if (!qaModules) throw new Error('ROUTE_NOTES_QA_MODULES is required');
const {Window} = await import(pathToFileURL(path.join(qaModules, 'happy-dom', 'lib', 'index.js')));
const fakeIndexedDb = await import(pathToFileURL(path.join(qaModules, 'fake-indexeddb', 'build', 'esm', 'index.js')));

const window = new Window({url:'http://127.0.0.1:8766/'});
const {document} = window;
Object.defineProperty(window, 'indexedDB', {value:fakeIndexedDb.indexedDB, configurable:true});
Object.defineProperty(window.navigator, 'storage', {value:{persist:async()=>true, estimate:async()=>({usage:2048, quota:104857600})}, configurable:true});
Object.defineProperty(window.navigator, 'onLine', {value:true, configurable:true});
window.confirm = () => true;
window.URL.createObjectURL = () => 'blob:qa';
window.URL.revokeObjectURL = () => {};
window.scrollTo = () => {};

document.body.innerHTML = `
  <nav class="hero-actions"></nav>
  <details class="route-card" id="r-qa-route" data-region="צפון" data-subregion="גליל" data-difficulty="בינוני" data-source="QA">
    <summary><span class="route-title">מסלול בדיקת יומן</span></summary>
    <div class="route-body"><div class="meta">
      <div><small>אזור</small><b>צפון</b></div><div><small>תת־אזור</small><b>גליל</b></div>
      <div><small>דירוג מקור</small><b>בינוני</b></div><div><small>אורך / זמן</small><b>42 ק״מ · שעתיים</b></div>
    </div><div class="route-actions"><button class="export-html">ייצוא</button></div></div>
  </details>
  <div class="toast" id="toast"></div>`;

const source = await fs.readFile(new URL('../assets/js/field-notes.js', import.meta.url), 'utf8');
window.eval(source);
await new Promise(resolve => setTimeout(resolve, 80));

assert.equal(document.querySelectorAll('.field-notes-action').length, 1, 'route notes button is injected');
assert.equal(document.querySelector('#fieldNotesHubButton').textContent, 'היומן שלי · 0', 'hub starts empty');
document.querySelector('.field-notes-action').click();
await new Promise(resolve => setTimeout(resolve, 30));
assert.equal(document.querySelector('#fieldNotesModal').hidden, false, 'route modal opens');

document.querySelector('#field-note-date').value = '2026-08-09';
document.querySelector('#field-note-author').value = 'רוכב QA';
document.querySelector('#field-note-source-type').value = 'internet';
document.querySelector('#field-note-source-type').dispatchEvent(new window.Event('change', {bubbles:true}));
document.querySelector('#field-note-source-url').value = 'https://example.com/review';
document.querySelector('#field-note-rating').value = '4';
document.querySelector('#field-note-difficulty').value = 'בינוני עבורי';
document.querySelector('#field-note-bike').value = 'Adventure 700';
document.querySelector('#field-note-text').value = 'שער צדדי היה פתוח, אבל נדרש אימות חוזר.';
document.querySelector('#field-note-review').value = 'מסלול זורם עם קטע דרדרתי קצר.';
document.querySelector('#field-note-videos').value = 'https://www.youtube.com/watch?v=qa-test';
document.querySelector('[name="field-note-tag"][value="needs-check"]').checked = true;
document.querySelector('#field-note-form').dispatchEvent(new window.Event('submit', {bubbles:true, cancelable:true}));
await new Promise(resolve => setTimeout(resolve, 160));

assert.equal(document.querySelector('#fieldNotesHubButton').textContent, 'היומן שלי · 1', 'hub count updates');
assert.equal(document.querySelector('.field-note-count').textContent, '1', 'route badge updates');
assert.match(document.querySelector('#field-note-list').textContent, /שער צדדי היה פתוח/, 'saved note renders');
assert.match(document.querySelector('#field-note-list').textContent, /ביקורת מהאינטרנט/, 'review source renders');

const exported = await window.R123FieldNotes.exportPackage();
assert.equal(exported.schemaVersion, 1, 'export schema version');
assert.equal(exported.reports.length, 1, 'one report exported');
assert.equal(exported.reports[0].routeId, 'r-qa-route', 'stable route id exported');
assert.equal(exported.reports[0].sourceType, 'internet', 'source type exported');
assert.equal(exported.reports[0].sourceUrl, 'https://example.com/review', 'source URL exported');
assert.equal(exported.reports[0].sharing.syncState, 'local-only', 'future sync field remains local only');
assert.equal(exported.reports[0].rating, 4, 'rating exported');

const routeHtml = await window.R123FieldNotes.routeExportHtml('r-qa-route');
assert.match(routeHtml, /הערות וביקורות מקומיות/, 'route HTML contains local notes section');
assert.match(routeHtml, /מסלול זורם עם קטע דרדרתי קצר/, 'route HTML contains review');
assert.match(routeHtml, /סרטון מצורף/, 'route HTML contains video link');

document.querySelector('[data-edit-report]').click();
await new Promise(resolve => setTimeout(resolve, 40));
assert.equal(document.querySelector('#field-note-author').value, 'רוכב QA', 'edit restores report');
document.querySelector('#field-note-review').value = 'ביקורת מעודכנת לאחר בדיקה נוספת.';
document.querySelector('#field-note-form').dispatchEvent(new window.Event('submit', {bubbles:true, cancelable:true}));
await new Promise(resolve => setTimeout(resolve, 140));
const updated = await window.R123FieldNotes.exportPackage();
assert.equal(updated.reports.length, 1, 'editing does not duplicate report');
assert.equal(updated.reports[0].reviewText, 'ביקורת מעודכנת לאחר בדיקה נוספת.', 'editing persists');
const importPayload = structuredClone(updated);
importPayload.reports[0].sourceUrl = 'javascript:alert(1)';
importPayload.reports[0].videoLinks.push('javascript:alert(2)');

document.querySelector('[data-delete-report]').click();
await new Promise(resolve => setTimeout(resolve, 120));
assert.equal((await window.R123FieldNotes.exportPackage()).reports.length, 0, 'deletion removes report');
assert.equal(document.querySelector('#fieldNotesHubButton').textContent, 'היומן שלי · 0', 'deletion updates hub count');

document.querySelector('#fieldNotesHubButton').click();
await new Promise(resolve => setTimeout(resolve, 30));
const backupFile = new window.File([JSON.stringify(importPayload)], 'field-notes-backup.json', {type:'application/json'});
const importInput = document.querySelector('#field-import-backup');
Object.defineProperty(importInput, 'files', {value:[backupFile], configurable:true});
importInput.dispatchEvent(new window.Event('change', {bubbles:true}));
await new Promise(resolve => setTimeout(resolve, 180));
const imported = await window.R123FieldNotes.exportPackage();
assert.equal(imported.reports.length, 1, 'backup import restores report');
assert.equal(imported.reports[0].reviewText, 'ביקורת מעודכנת לאחר בדיקה נוספת.', 'import preserves updated review');
assert.equal(imported.reports[0].sourceUrl, '', 'import rejects unsafe source URL');
assert.equal(imported.reports[0].videoLinks.length, 1, 'import rejects unsafe video URL');

console.log(JSON.stringify({result:'passed', reports:imported.reports.length, routeId:imported.reports[0].routeId, schemaVersion:imported.schemaVersion, importVerified:true, deleteVerified:true}));
