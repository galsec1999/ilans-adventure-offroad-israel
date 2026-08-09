/* יומן שטח מקומי — גרסת מסמך 2.4.0; גרסת מוצר 2.6.0 */
(() => {
  'use strict';

  const PRODUCT_VERSION = '2.6.0';
  const DOC_VERSION = '2.4.0';
  const EXPORT_SCHEMA_VERSION = 1;
  const DB_NAME = 'ilans-adventure-route-field-notes';
  const DB_VERSION = 1;
  const REPORT_STORE = 'reports';
  const MEDIA_STORE = 'media';
  const SETTINGS_STORE = 'settings';
  const MAX_PHOTOS_PER_REPORT = 6;
  const MAX_SOURCE_PHOTO_BYTES = 10 * 1024 * 1024;
  const MAX_PHOTO_EDGE = 1600;
  const cards = [...document.querySelectorAll('.route-card')];
  const objectUrls = new Set();
  let dbPromise;
  let activeRouteId = '';
  let editingReportId = '';
  let lastFocus = null;

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const plain = value => String(value || '').replace(/\s+/g, ' ').trim();
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

  function uuid() {
    if (crypto.randomUUID) return crypto.randomUUID();
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = [...bytes].map(value => value.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
  }

  function showToast(message) {
    const toast = $('#toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.remove('show'), 3200);
  }

  function openDb() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onerror = () => reject(request.error);
      request.onblocked = () => reject(new Error('מסד ההערות חסום בכרטיסייה אחרת'));
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(REPORT_STORE)) {
          const reports = db.createObjectStore(REPORT_STORE, {keyPath:'id'});
          reports.createIndex('routeId', 'routeId', {unique:false});
          reports.createIndex('updatedAt', 'updatedAt', {unique:false});
          reports.createIndex('syncState', 'sharing.syncState', {unique:false});
        }
        if (!db.objectStoreNames.contains(MEDIA_STORE)) {
          const media = db.createObjectStore(MEDIA_STORE, {keyPath:'id'});
          media.createIndex('reportId', 'reportId', {unique:false});
        }
        if (!db.objectStoreNames.contains(SETTINGS_STORE)) db.createObjectStore(SETTINGS_STORE, {keyPath:'key'});
      };
      request.onsuccess = () => resolve(request.result);
    });
    return dbPromise;
  }

  async function transaction(storeNames, mode, work) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeNames, mode);
      const stores = Object.fromEntries(storeNames.map(name => [name, tx.objectStore(name)]));
      let result;
      try { result = work(stores, tx); }
      catch (error) { tx.abort(); reject(error); return; }
      tx.oncomplete = () => resolve(result);
      tx.onerror = () => reject(tx.error || new Error('שמירת הנתונים נכשלה'));
      tx.onabort = () => reject(tx.error || new Error('שמירת הנתונים בוטלה'));
    });
  }

  function requestResult(request) {
    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async function allReports(routeId = '') {
    const db = await openDb();
    const tx = db.transaction(REPORT_STORE, 'readonly');
    const store = tx.objectStore(REPORT_STORE);
    const request = routeId ? store.index('routeId').getAll(routeId) : store.getAll();
    const reports = await requestResult(request);
    return reports.sort((a, b) => String(b.riddenOn || b.updatedAt).localeCompare(String(a.riddenOn || a.updatedAt)));
  }

  async function reportMedia(reportId) {
    const db = await openDb();
    const tx = db.transaction(MEDIA_STORE, 'readonly');
    return requestResult(tx.objectStore(MEDIA_STORE).index('reportId').getAll(reportId));
  }

  async function allMedia() {
    const db = await openDb();
    const tx = db.transaction(MEDIA_STORE, 'readonly');
    return requestResult(tx.objectStore(MEDIA_STORE).getAll());
  }

  function cardFor(routeId) {
    return document.getElementById(routeId);
  }

  function routeSnapshot(card) {
    const meta = {};
    $$('.meta > div', card).forEach(item => {
      const key = plain($('small', item)?.textContent);
      if (key) meta[key] = plain($('b', item)?.textContent);
    });
    return {
      id: card.id,
      title: plain($('.route-title', card)?.textContent),
      region: meta['אזור'] || card.dataset.region || 'לא צוין',
      subregion: meta['תת־אזור'] || card.dataset.subregion || 'לא צוין',
      difficulty: meta['דירוג מקור'] || card.dataset.difficulty || 'לא אומת',
      distanceDuration: meta['אורך / זמן'] || 'לא צוין',
      source: card.dataset.source || 'לא צוין',
      cardUrl: `${location.href.split('#')[0]}#${card.id}`
    };
  }

  function validHttpUrl(value) {
    if (!plain(value)) return '';
    try {
      const url = new URL(value);
      return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
    } catch (_) { return ''; }
  }

  function boundedText(value, maximum) {
    return String(value ?? '').slice(0, maximum);
  }

  function parseVideoLinks(value) {
    const invalid = [];
    const links = [...new Set(String(value || '').split(/\r?\n/).map(plain).filter(Boolean).map(raw => {
      const url = validHttpUrl(raw);
      if (!url) invalid.push(raw);
      return url;
    }).filter(Boolean))];
    if (invalid.length) throw new Error('קישור סרטון חייב להתחיל ב־http או https');
    return links;
  }

  async function deviceId() {
    const db = await openDb();
    const tx = db.transaction(SETTINGS_STORE, 'readwrite');
    const store = tx.objectStore(SETTINGS_STORE);
    const existing = await requestResult(store.get('deviceId'));
    if (existing?.value) return existing.value;
    const value = uuid();
    store.put({key:'deviceId', value, createdAt:new Date().toISOString()});
    return value;
  }

  function fileToImage(file) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      const url = URL.createObjectURL(file);
      image.onload = () => { URL.revokeObjectURL(url); resolve(image); };
      image.onerror = () => { URL.revokeObjectURL(url); reject(new Error('לא ניתן לקרוא את התמונה')); };
      image.src = url;
    });
  }

  async function compressPhoto(file) {
    if (!file.type.startsWith('image/')) throw new Error(`${file.name}: הקובץ אינו תמונה`);
    if (file.size > MAX_SOURCE_PHOTO_BYTES) throw new Error(`${file.name}: התמונה גדולה מ־10MB`);
    const image = await fileToImage(file);
    const scale = Math.min(1, MAX_PHOTO_EDGE / Math.max(image.naturalWidth, image.naturalHeight));
    const width = Math.max(1, Math.round(image.naturalWidth * scale));
    const height = Math.max(1, Math.round(image.naturalHeight * scale));
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    canvas.getContext('2d', {alpha:false}).drawImage(image, 0, 0, width, height);
    const preferredType = canvas.toDataURL('image/webp').startsWith('data:image/webp') ? 'image/webp' : 'image/jpeg';
    const blob = await new Promise(resolve => canvas.toBlob(resolve, preferredType, .82));
    if (!blob) throw new Error(`${file.name}: דחיסת התמונה נכשלה`);
    return {
      id:uuid(),
      name:file.name.replace(/[^\p{L}\p{N}._ -]+/gu, '_').slice(0, 120) || 'photo',
      type:blob.type,
      size:blob.size,
      width,
      height,
      blob,
      createdAt:new Date().toISOString(),
      exifRemoved:true
    };
  }

  async function requestPersistentStorage() {
    if (!navigator.storage?.persist) return false;
    try { return await navigator.storage.persist(); }
    catch (_) { return false; }
  }

  async function storageSummary() {
    if (!navigator.storage?.estimate) return 'האחסון המקומי פעיל';
    try {
      const {usage = 0, quota = 0} = await navigator.storage.estimate();
      const mb = value => (value / 1024 / 1024).toLocaleString('he-IL', {maximumFractionDigits:1});
      return `בשימוש ${mb(usage)}MB מתוך מכסה משוערת של ${mb(quota)}MB`;
    } catch (_) { return 'האחסון המקומי פעיל'; }
  }

  function buildUi() {
    const hubButton = document.createElement('button');
    hubButton.id = 'fieldNotesHubButton';
    hubButton.className = 'field-notes-hub-button';
    hubButton.type = 'button';
    hubButton.textContent = 'היומן שלי · 0';
    $('.hero-actions')?.append(hubButton);

    cards.forEach(card => {
      const actions = $('.route-actions', card);
      if (!actions || $('.field-notes-action', actions)) return;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'field-notes-action';
      button.innerHTML = 'הערות וביקורות <span class="field-note-count">0</span>';
      actions.prepend(button);
    });

    document.body.insertAdjacentHTML('beforeend', `
      <div class="dialog-shell field-notes-shell" id="fieldNotesModal" role="dialog" aria-modal="true" aria-labelledby="field-notes-title" hidden><div class="dialog-panel">
        <button class="dialog-close" type="button" data-field-close aria-label="סגירת יומן המסלול">×</button>
        <h2 id="field-notes-title">הערות וביקורות מהשטח</h2><p class="dialog-route" id="field-notes-route"></p>
        <div class="local-only-banner"><b>נשמר רק במכשיר ובדפדפן הזה.</b> ההערות אינן נשלחות לאילן או למשתמשים אחרים. מחיקת נתוני האתר עלולה למחוק אותן, ולכן מומלץ לבצע גיבוי לאחר כל טיול.</div>
        <div class="field-notes-layout">
          <form id="field-note-form" class="field-note-form">
            <input id="field-note-id" type="hidden">
            <section class="form-section"><h3>הרכיבה והמקור</h3><div class="dialog-grid">
              <label>תאריך הרכיבה<input id="field-note-date" type="date"></label>
              <label>שם או כינוי<input id="field-note-author" maxlength="80" autocomplete="name" placeholder="אופציונלי"></label>
              <label>מקור הדיווח<select id="field-note-source-type"><option value="personal">חוויה אישית שלי</option><option value="rider">דיווח שקיבלתי מרוכב אחר</option><option value="internet">ביקורת שמצאתי באינטרנט</option></select></label>
              <label id="field-note-source-url-wrap" hidden>קישור למקור<input id="field-note-source-url" type="url" inputmode="url" placeholder="https://…"></label>
              <label>דירוג כללי<select id="field-note-rating"><option value="">ללא דירוג</option><option value="5">5 — מצוין</option><option value="4">4 — טוב מאוד</option><option value="3">3 — טוב</option><option value="2">2 — דרוש שיפור</option><option value="1">1 — לא מומלץ במצב שנבדק</option></select></label>
              <label>הקושי שחוויתי<select id="field-note-difficulty"><option value="">לא צוין</option><option>קל עבורי</option><option>קל–בינוני עבורי</option><option>בינוני עבורי</option><option>בינוני–קשה עבורי</option><option>קשה עבורי</option><option>לא רכבתי בעצמי</option></select></label>
              <label>אופנוע / צמיגים<input id="field-note-bike" maxlength="140" placeholder="לדוגמה: Ténéré 700, צמיגי 50/50"></label>
              <label>מצב הקרקע<input id="field-note-surface" maxlength="140" placeholder="יבש, בוץ, דרדרת…"></label>
              <label>מזג אוויר<input id="field-note-weather" maxlength="140"></label>
              <label>מרחק בפועל בק״מ<input id="field-note-distance" type="number" min="0" max="2000" step="0.1" inputmode="decimal"></label>
              <label>משך בפועל בדקות<input id="field-note-duration" type="number" min="0" max="2880" step="1" inputmode="numeric"></label>
            </div></section>
            <section class="form-section"><h3>מה חשוב לעדכן</h3><div class="field-note-tags">
              <label><input type="checkbox" name="field-note-tag" value="recommended">מומלץ</label>
              <label><input type="checkbox" name="field-note-tag" value="needs-check">דורש בדיקה</label>
              <label><input type="checkbox" name="field-note-tag" value="route-change">שינוי בתוואי</label>
              <label><input type="checkbox" name="field-note-tag" value="blocked">חסימה / שער</label>
              <label><input type="checkbox" name="field-note-tag" value="hazard">מפגע / סכנה</label>
              <label><input type="checkbox" name="field-note-tag" value="closed">ייתכן שסגור</label>
            </div>
            <label>הערות מהשטח<textarea id="field-note-text" rows="5" maxlength="6000" placeholder="מה עברתם, מה השתנה, נקודות קשות, עצירות ומידע שימושי…"></textarea></label>
            <label>ביקורת והמלצה<textarea id="field-note-review" rows="4" maxlength="4000" placeholder="למי המסלול מתאים, מה אהבתם ומה כדאי לשפר…"></textarea></label>
            <label>קישורי סרטונים — קישור בכל שורה<textarea id="field-note-videos" rows="3" maxlength="6000" dir="ltr" placeholder="https://youtube.com/…"></textarea></label>
            <label>תמונות — עד ${MAX_PHOTOS_PER_REPORT}, נשמרות לאחר הקטנה וללא EXIF<input id="field-note-photos" type="file" accept="image/*" multiple></label>
            <p class="field-note-existing-media" id="field-note-existing-media"></p></section>
            <p class="form-error" id="field-note-error" role="alert"></p>
            <div class="dialog-actions"><button class="field-note-save" type="submit">שמירת הדיווח</button><button id="field-note-reset" type="button">דיווח חדש</button><button id="field-note-export-route" class="secondary" type="button">ייצוא נתוני המסלול</button></div>
          </form>
          <section class="field-note-list-panel"><div class="field-note-list-head"><h3>דיווחים שמורים</h3><span id="field-note-route-count"></span></div><div id="field-note-list" class="field-note-list"></div></section>
        </div>
      </div></div>
      <div class="dialog-shell field-notes-shell" id="fieldNotesHub" role="dialog" aria-modal="true" aria-labelledby="field-notes-hub-title" hidden><div class="dialog-panel">
        <button class="dialog-close" type="button" data-field-close aria-label="סגירת היומן">×</button>
        <h2 id="field-notes-hub-title">היומן המקומי שלי</h2><p>כל ההערות והביקורות נשמרות במכשיר הנוכחי בלבד.</p>
        <div class="local-only-banner"><b>כדי להעביר חומר לאילן או למכשיר אחר:</b> השתמשו ב„שיתוף גיבוי” או „הורדת גיבוי”. קובץ הגיבוי כולל את הנתונים והתמונות. מחיקת נתוני האתר עלולה למחוק את העותק המקומי.</div>
        <div class="field-hub-stats"><b id="field-hub-count">0 דיווחים</b><span id="field-storage-summary">בודק אחסון…</span></div>
        <div class="field-hub-actions">
          <button id="field-export-report" type="button">דוח HTML לקריאה</button>
          <button id="field-share-backup" type="button">שיתוף גיבוי מלא</button>
          <button id="field-download-backup" type="button">הורדת גיבוי מלא</button>
          <label class="field-import-label">ייבוא גיבוי<input id="field-import-backup" type="file" accept="application/json,.json"></label>
        </div>
        <p class="dialog-note">הייבוא ממזג רשומות לפי מזהה ושומר את העדכון החדש יותר. הוא אינו מוחק דיווחים אחרים.</p>
        <div id="field-hub-list" class="field-note-list field-hub-list"></div>
      </div></div>`);
  }

  function openModal(modal) {
    lastFocus = document.activeElement;
    modal.hidden = false;
    document.body.classList.add('modal-open');
    setTimeout(() => $('.dialog-close', modal)?.focus(), 0);
  }

  function closeModal(modal) {
    modal.hidden = true;
    document.body.classList.remove('modal-open');
    lastFocus?.focus?.();
  }

  function clearObjectUrls() {
    objectUrls.forEach(url => URL.revokeObjectURL(url));
    objectUrls.clear();
  }

  function sourceLabel(value) {
    return {personal:'חוויה אישית', rider:'דיווח מרוכב אחר', internet:'ביקורת מהאינטרנט'}[value] || 'לא צוין';
  }

  function tagLabel(value) {
    return {recommended:'מומלץ','needs-check':'דורש בדיקה','route-change':'שינוי בתוואי',blocked:'חסימה / שער',hazard:'מפגע / סכנה',closed:'ייתכן שסגור'}[value] || value;
  }

  function reportTitle(report) {
    return report.routeSnapshot?.title || plain($('.route-title', cardFor(report.routeId))?.textContent) || report.routeId;
  }

  function formatDate(value) {
    if (!value) return 'ללא תאריך רכיבה';
    const date = new Date(`${value}T12:00:00`);
    return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString('he-IL');
  }

  async function reportCardHtml(report, includeRouteTitle = false) {
    const media = await reportMedia(report.id);
    const photos = media.map(item => {
      const url = URL.createObjectURL(item.blob);
      objectUrls.add(url);
      return `<img src="${url}" alt="${escapeHtml(item.name || 'תמונה מהשטח')}">`;
    }).join('');
    const links = (report.videoLinks || []).map(validHttpUrl).filter(Boolean).map(url => `<a href="${escapeHtml(url)}" target="_blank" rel="noopener">פתיחת סרטון</a>`).join('');
    const tags = (report.tags || []).map(tag => `<span>${escapeHtml(tagLabel(tag))}</span>`).join('');
    return `<article class="field-report-card" data-report-id="${escapeHtml(report.id)}">
      ${includeRouteTitle ? `<h3>${escapeHtml(reportTitle(report))}</h3>` : ''}
      <div class="field-report-meta"><b>${escapeHtml(formatDate(report.riddenOn))}</b><span>${escapeHtml(sourceLabel(report.sourceType))}</span>${report.rating ? `<span>${'★'.repeat(report.rating)}${'☆'.repeat(5-report.rating)}</span>` : ''}</div>
      ${tags ? `<div class="field-report-tags">${tags}</div>` : ''}
      ${report.noteText ? `<p>${escapeHtml(report.noteText).replace(/\n/g,'<br>')}</p>` : ''}
      ${report.reviewText ? `<blockquote>${escapeHtml(report.reviewText).replace(/\n/g,'<br>')}</blockquote>` : ''}
      <dl>${report.author ? `<div><dt>שם / כינוי</dt><dd>${escapeHtml(report.author)}</dd></div>` : ''}${report.difficultyExperienced ? `<div><dt>קושי שנחווה</dt><dd>${escapeHtml(report.difficultyExperienced)}</dd></div>` : ''}${report.motorcycle ? `<div><dt>אופנוע</dt><dd>${escapeHtml(report.motorcycle)}</dd></div>` : ''}${report.surfaceCondition ? `<div><dt>קרקע</dt><dd>${escapeHtml(report.surfaceCondition)}</dd></div>` : ''}${report.weather ? `<div><dt>מזג אוויר</dt><dd>${escapeHtml(report.weather)}</dd></div>` : ''}${report.actualDistanceKm != null ? `<div><dt>מרחק בפועל</dt><dd>${escapeHtml(report.actualDistanceKm)} ק״מ</dd></div>` : ''}${report.actualDurationMinutes != null ? `<div><dt>משך בפועל</dt><dd>${escapeHtml(report.actualDurationMinutes)} דקות</dd></div>` : ''}</dl>
      ${validHttpUrl(report.sourceUrl) ? `<p><a href="${escapeHtml(validHttpUrl(report.sourceUrl))}" target="_blank" rel="noopener">מקור הביקורת</a></p>` : ''}${links ? `<div class="field-report-links">${links}</div>` : ''}${photos ? `<div class="field-report-photos">${photos}</div>` : ''}
      <div class="field-report-actions"><button type="button" data-edit-report="${escapeHtml(report.id)}">עריכה</button><button class="danger" type="button" data-delete-report="${escapeHtml(report.id)}">מחיקה</button></div>
    </article>`;
  }

  async function refreshBadges() {
    const reports = await allReports();
    const counts = new Map();
    reports.forEach(report => counts.set(report.routeId, (counts.get(report.routeId) || 0) + 1));
    cards.forEach(card => {
      const count = counts.get(card.id) || 0;
      const badge = $('.field-note-count', card);
      if (badge) badge.textContent = String(count);
      card.classList.toggle('has-local-notes', count > 0);
    });
    const hub = $('#fieldNotesHubButton');
    if (hub) hub.textContent = `היומן שלי · ${reports.length}`;
  }

  async function renderRouteReports() {
    clearObjectUrls();
    const reports = await allReports(activeRouteId);
    $('#field-note-route-count').textContent = `${reports.length} דיווחים`;
    $('#field-note-list').innerHTML = reports.length ? (await Promise.all(reports.map(report => reportCardHtml(report)))).join('') : '<div class="field-note-empty">עדיין אין הערות למסלול הזה.</div>';
  }

  async function renderHub() {
    clearObjectUrls();
    const reports = await allReports();
    $('#field-hub-count').textContent = `${reports.length} דיווחים על ${new Set(reports.map(item => item.routeId)).size} מסלולים`;
    $('#field-storage-summary').textContent = await storageSummary();
    $('#field-hub-list').innerHTML = reports.length ? (await Promise.all(reports.map(report => reportCardHtml(report, true)))).join('') : '<div class="field-note-empty">עדיין לא נשמרו דיווחים.</div>';
  }

  function resetForm() {
    editingReportId = '';
    $('#field-note-form').reset();
    $('#field-note-id').value = '';
    $('#field-note-date').value = new Date().toISOString().slice(0, 10);
    $('#field-note-source-url-wrap').hidden = true;
    $('#field-note-existing-media').textContent = '';
    $('#field-note-error').textContent = '';
    $('.field-note-save').textContent = 'שמירת הדיווח';
  }

  async function openRouteNotes(card) {
    activeRouteId = card.id;
    $('#field-notes-route').textContent = plain($('.route-title', card)?.textContent);
    resetForm();
    await renderRouteReports();
    openModal($('#fieldNotesModal'));
  }

  async function editReport(reportId) {
    const reports = await allReports();
    const report = reports.find(item => item.id === reportId);
    if (!report) return;
    activeRouteId = report.routeId;
    editingReportId = report.id;
    const card = cardFor(report.routeId);
    $('#field-notes-route').textContent = reportTitle(report);
    $('#field-note-id').value = report.id;
    $('#field-note-date').value = report.riddenOn || '';
    $('#field-note-author').value = report.author || '';
    $('#field-note-source-type').value = report.sourceType || 'personal';
    $('#field-note-source-url-wrap').hidden = report.sourceType !== 'internet';
    $('#field-note-source-url').value = report.sourceUrl || '';
    $('#field-note-rating').value = report.rating || '';
    $('#field-note-difficulty').value = report.difficultyExperienced || '';
    $('#field-note-bike').value = report.motorcycle || '';
    $('#field-note-surface').value = report.surfaceCondition || '';
    $('#field-note-weather').value = report.weather || '';
    $('#field-note-distance').value = report.actualDistanceKm ?? '';
    $('#field-note-duration').value = report.actualDurationMinutes ?? '';
    $('#field-note-text').value = report.noteText || '';
    $('#field-note-review').value = report.reviewText || '';
    $('#field-note-videos').value = (report.videoLinks || []).join('\n');
    $$('[name="field-note-tag"]').forEach(input => { input.checked = (report.tags || []).includes(input.value); });
    const media = await reportMedia(report.id);
    $('#field-note-existing-media').textContent = media.length ? `${media.length} תמונות קיימות יישמרו. אפשר להוסיף תמונות נוספות עד למגבלה.` : '';
    $('.field-note-save').textContent = 'שמירת השינויים';
    if (card && $('#fieldNotesModal').hidden) openModal($('#fieldNotesModal'));
    $('#field-note-form').scrollIntoView({block:'start', behavior:'smooth'});
  }

  function numberOrNull(value) {
    if (plain(value) === '') return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  async function saveReport(event) {
    event.preventDefault();
    const errorBox = $('#field-note-error');
    errorBox.textContent = '';
    try {
      const card = cardFor(activeRouteId);
      if (!card) throw new Error('כרטיס המסלול לא נמצא');
      const sourceType = $('#field-note-source-type').value;
      const sourceUrlRaw = plain($('#field-note-source-url').value);
      const sourceUrl = sourceUrlRaw ? validHttpUrl(sourceUrlRaw) : '';
      if (sourceType === 'internet' && !sourceUrl) throw new Error('ביקורת מהאינטרנט מחייבת קישור מקור תקין');
      const videoLinks = parseVideoLinks($('#field-note-videos').value);
      const files = [...$('#field-note-photos').files];
      const existingMedia = editingReportId ? await reportMedia(editingReportId) : [];
      if (existingMedia.length + files.length > MAX_PHOTOS_PER_REPORT) throw new Error(`אפשר לשמור עד ${MAX_PHOTOS_PER_REPORT} תמונות בדיווח`);
      const noteText = $('#field-note-text').value.trim();
      const reviewText = $('#field-note-review').value.trim();
      if (!noteText && !reviewText && !videoLinks.length && !files.length) throw new Error('יש לכתוב הערה או ביקורת, או לצרף תמונה או סרטון');
      const now = new Date().toISOString();
      const prior = editingReportId ? (await allReports()).find(item => item.id === editingReportId) : null;
      const reportId = prior?.id || uuid();
      const report = {
        schemaVersion:EXPORT_SCHEMA_VERSION,
        id:reportId,
        routeId:activeRouteId,
        routeSnapshot:routeSnapshot(card),
        riddenOn:$('#field-note-date').value || '',
        author:plain($('#field-note-author').value),
        sourceType,
        sourceUrl,
        rating:numberOrNull($('#field-note-rating').value),
        difficultyExperienced:$('#field-note-difficulty').value,
        motorcycle:plain($('#field-note-bike').value),
        surfaceCondition:plain($('#field-note-surface').value),
        weather:plain($('#field-note-weather').value),
        actualDistanceKm:numberOrNull($('#field-note-distance').value),
        actualDurationMinutes:numberOrNull($('#field-note-duration').value),
        tags:$$('[name="field-note-tag"]:checked').map(input => input.value),
        noteText,
        reviewText,
        videoLinks,
        mediaCount:existingMedia.length + files.length,
        createdAt:prior?.createdAt || now,
        updatedAt:now,
        deviceId:await deviceId(),
        connectivityAtSave:navigator.onLine ? 'online' : 'offline',
        sharing:{visibility:'private', syncState:'local-only', remoteId:null}
      };
      const compressed = [];
      for (const file of files) compressed.push({...await compressPhoto(file), reportId, routeId:activeRouteId});
      await transaction([REPORT_STORE, MEDIA_STORE], 'readwrite', stores => {
        stores[REPORT_STORE].put(report);
        compressed.forEach(item => stores[MEDIA_STORE].put(item));
      });
      await requestPersistentStorage();
      resetForm();
      await Promise.all([renderRouteReports(), refreshBadges()]);
      showToast('הדיווח נשמר במכשיר');
    } catch (error) {
      console.error(error);
      errorBox.textContent = error?.message || 'שמירת הדיווח נכשלה';
    }
  }

  async function deleteReport(reportId) {
    if (!confirm('למחוק את הדיווח ואת התמונות שצורפו אליו מהמכשיר?')) return;
    const media = await reportMedia(reportId);
    await transaction([REPORT_STORE, MEDIA_STORE], 'readwrite', stores => {
      stores[REPORT_STORE].delete(reportId);
      media.forEach(item => stores[MEDIA_STORE].delete(item.id));
    });
    if (editingReportId === reportId) resetForm();
    await Promise.all([renderRouteReports(), refreshBadges()]);
    if (!$('#fieldNotesHub').hidden) await renderHub();
    showToast('הדיווח נמחק');
  }

  function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  async function exportPackage(routeId = '') {
    const reports = await allReports(routeId);
    const allowed = new Set(reports.map(item => item.id));
    const media = (await allMedia()).filter(item => allowed.has(item.reportId));
    return {
      format:'ilans-adventure-route-field-notes',
      schemaVersion:EXPORT_SCHEMA_VERSION,
      productVersion:PRODUCT_VERSION,
      documentVersion:DOC_VERSION,
      exportedAt:new Date().toISOString(),
      scope:routeId ? {type:'route', routeId} : {type:'all'},
      reports,
      media:await Promise.all(media.map(async item => ({...item, blob:undefined, dataUrl:await blobToDataUrl(item.blob)})))
    };
  }

  function safeFileName(value) {
    return plain(value).replace(/[\\/:*?"<>|]+/g, '-').slice(0, 100) || 'route-notes';
  }

  function downloadBlob(blob, name) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  async function backupFile(routeId = '') {
    const data = await exportPackage(routeId);
    const suffix = routeId ? safeFileName(reportTitle(data.reports[0] || {routeId})) : 'כל-היומן';
    const name = `יומן-מסלולים_${suffix}_${new Date().toISOString().slice(0,10)}.json`;
    return new File([JSON.stringify(data, null, 2)], name, {type:'application/json'});
  }

  async function shareBackup() {
    const file = await backupFile();
    if (navigator.share && navigator.canShare?.({files:[file]})) {
      try { await navigator.share({title:'גיבוי יומן מסלולים', text:'גיבוי הערות וביקורות מהשטח', files:[file]}); return; }
      catch (error) { if (error?.name === 'AbortError') return; }
    }
    downloadBlob(file, file.name);
    showToast('השיתוף אינו נתמך כאן; קובץ הגיבוי הורד');
  }

  async function dataUrlToBlob(dataUrl) {
    const response = await fetch(dataUrl);
    return response.blob();
  }

  function validateImport(data) {
    if (!data || data.format !== 'ilans-adventure-route-field-notes' || data.schemaVersion !== EXPORT_SCHEMA_VERSION) throw new Error('זה אינו קובץ גיבוי נתמך של יומן המסלולים');
    if (!Array.isArray(data.reports) || !Array.isArray(data.media)) throw new Error('מבנה קובץ הגיבוי אינו תקין');
    if (data.reports.length > 10000 || data.media.length > 60000) throw new Error('קובץ הגיבוי חורג ממגבלות הייבוא');
  }

  function sanitizeImportedReport(report) {
    const importedSourceType = ['personal', 'rider', 'internet'].includes(report.sourceType) ? report.sourceType : 'rider';
    const sourceUrl = validHttpUrl(report.sourceUrl);
    const sourceType = importedSourceType === 'internet' && !sourceUrl ? 'rider' : importedSourceType;
    const allowedTags = new Set(['recommended', 'needs-check', 'route-change', 'blocked', 'hazard', 'closed']);
    const rating = Number(report.rating);
    const safeNumber = (value, maximum) => {
      if (value == null || value === '') return null;
      const number = Number(value);
      return Number.isFinite(number) && number >= 0 && number <= maximum ? number : null;
    };
    return {
      schemaVersion:EXPORT_SCHEMA_VERSION,
      id:boundedText(report.id, 128),
      routeId:boundedText(report.routeId, 128),
      routeSnapshot:{
        id:boundedText(report.routeSnapshot?.id || report.routeId, 128),
        title:boundedText(report.routeSnapshot?.title, 300),
        region:boundedText(report.routeSnapshot?.region, 120),
        subregion:boundedText(report.routeSnapshot?.subregion, 160),
        difficulty:boundedText(report.routeSnapshot?.difficulty, 120),
        distanceDuration:boundedText(report.routeSnapshot?.distanceDuration, 160),
        source:boundedText(report.routeSnapshot?.source, 160),
        cardUrl:validHttpUrl(report.routeSnapshot?.cardUrl)
      },
      riddenOn:/^\d{4}-\d{2}-\d{2}$/.test(report.riddenOn || '') ? report.riddenOn : '',
      author:boundedText(report.author, 80),
      sourceType,
      sourceUrl,
      rating:Number.isInteger(rating) && rating >= 1 && rating <= 5 ? rating : null,
      difficultyExperienced:boundedText(report.difficultyExperienced, 100),
      motorcycle:boundedText(report.motorcycle, 140),
      surfaceCondition:boundedText(report.surfaceCondition, 140),
      weather:boundedText(report.weather, 140),
      actualDistanceKm:safeNumber(report.actualDistanceKm, 2000),
      actualDurationMinutes:safeNumber(report.actualDurationMinutes, 2880),
      tags:[...new Set((Array.isArray(report.tags) ? report.tags : []).filter(tag => allowedTags.has(tag)))],
      noteText:boundedText(report.noteText, 6000),
      reviewText:boundedText(report.reviewText, 4000),
      videoLinks:[...new Set((Array.isArray(report.videoLinks) ? report.videoLinks : []).map(validHttpUrl).filter(Boolean))].slice(0, 30),
      mediaCount:safeNumber(report.mediaCount, MAX_PHOTOS_PER_REPORT) || 0,
      createdAt:boundedText(report.createdAt, 40),
      updatedAt:boundedText(report.updatedAt, 40) || new Date().toISOString(),
      deviceId:boundedText(report.deviceId, 128),
      connectivityAtSave:['online', 'offline'].includes(report.connectivityAtSave) ? report.connectivityAtSave : 'unknown',
      sharing:{visibility:'private', syncState:'local-only', remoteId:null}
    };
  }

  async function importBackup(file) {
    const data = JSON.parse(await file.text());
    validateImport(data);
    const existing = new Map((await allReports()).map(report => [report.id, report]));
    const reports = data.reports.filter(report => report?.id && report?.routeId).map(sanitizeImportedReport).filter(report => report.id && report.routeId).map(report => {
      const prior = existing.get(report.id);
      return prior && String(prior.updatedAt) > String(report.updatedAt) ? prior : report;
    });
    const importedReportIds = new Set(reports.map(report => report.id));
    const mediaCounts = new Map();
    const media = [];
    for (const item of data.media) {
      const dataUrl = String(item?.dataUrl || '');
      if (!item?.id || !item?.reportId || !importedReportIds.has(item.reportId)) continue;
      if (!/^data:image\/(?:png|jpeg|webp);base64,/i.test(dataUrl) || dataUrl.length > 12 * 1024 * 1024) continue;
      const count = mediaCounts.get(item.reportId) || 0;
      if (count >= MAX_PHOTOS_PER_REPORT) continue;
      const blob = await dataUrlToBlob(item.dataUrl);
      if (blob.size > 8 * 1024 * 1024 || !['image/png', 'image/jpeg', 'image/webp'].includes(blob.type)) continue;
      mediaCounts.set(item.reportId, count + 1);
      media.push({id:boundedText(item.id, 128), reportId:boundedText(item.reportId, 128), routeId:boundedText(item.routeId, 128), name:boundedText(item.name, 120), type:blob.type, size:blob.size, width:safeImportedDimension(item.width), height:safeImportedDimension(item.height), blob, createdAt:boundedText(item.createdAt, 40), exifRemoved:true});
    }
    await transaction([REPORT_STORE, MEDIA_STORE], 'readwrite', stores => {
      reports.forEach(report => stores[REPORT_STORE].put(report));
      media.forEach(item => stores[MEDIA_STORE].put(item));
    });
    await Promise.all([refreshBadges(), renderHub()]);
    showToast(`יובאו או מוזגו ${reports.length} דיווחים`);
  }

  function safeImportedDimension(value) {
    const number = Number(value);
    return Number.isInteger(number) && number > 0 && number <= 10000 ? number : null;
  }

  async function exportHtmlReport() {
    const reports = await allReports();
    const media = await allMedia();
    const mediaMap = new Map();
    for (const item of media) {
      if (!mediaMap.has(item.reportId)) mediaMap.set(item.reportId, []);
      mediaMap.get(item.reportId).push({...item, dataUrl:await blobToDataUrl(item.blob)});
    }
    const grouped = new Map();
    reports.forEach(report => {
      if (!grouped.has(report.routeId)) grouped.set(report.routeId, []);
      grouped.get(report.routeId).push(report);
    });
    const sections = [...grouped.entries()].map(([routeId, items]) => `<section class="route"><h2>${escapeHtml(reportTitle(items[0]))}</h2><p class="route-meta">${escapeHtml(items[0].routeSnapshot?.region || '')} · ${escapeHtml(items[0].routeSnapshot?.distanceDuration || '')} · מזהה ${escapeHtml(routeId)}</p>${items.map(report => {
      const photos = (mediaMap.get(report.id) || []).map(item => `<figure><img src="${item.dataUrl}" alt="${escapeHtml(item.name)}"><figcaption>${escapeHtml(item.name)}</figcaption></figure>`).join('');
      const tags = (report.tags || []).map(tag => `<span>${escapeHtml(tagLabel(tag))}</span>`).join('');
      const videos = (report.videoLinks || []).map(validHttpUrl).filter(Boolean).map(url => `<li><a href="${escapeHtml(url)}">${escapeHtml(url)}</a></li>`).join('');
      return `<article><header><b>${escapeHtml(formatDate(report.riddenOn))}</b>${report.rating ? `<strong>${'★'.repeat(report.rating)}${'☆'.repeat(5-report.rating)}</strong>` : ''}</header><p>${escapeHtml(sourceLabel(report.sourceType))}${report.author ? ` · ${escapeHtml(report.author)}` : ''}${report.motorcycle ? ` · ${escapeHtml(report.motorcycle)}` : ''}</p>${tags ? `<div class="tags">${tags}</div>` : ''}${report.noteText ? `<h3>הערות</h3><p>${escapeHtml(report.noteText).replace(/\n/g,'<br>')}</p>` : ''}${report.reviewText ? `<h3>ביקורת</h3><blockquote>${escapeHtml(report.reviewText).replace(/\n/g,'<br>')}</blockquote>` : ''}${validHttpUrl(report.sourceUrl) ? `<p><a href="${escapeHtml(validHttpUrl(report.sourceUrl))}">מקור הביקורת</a></p>` : ''}${videos ? `<h3>סרטונים</h3><ul>${videos}</ul>` : ''}${photos ? `<div class="photos">${photos}</div>` : ''}</article>`;
    }).join('')}</section>`).join('');
    const html = `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow,noarchive,nosnippet"><meta name="viewport" content="width=device-width,initial-scale=1"><title>דוח יומן מסלולים · גרסת מסמך ${DOC_VERSION}</title><style>*{box-sizing:border-box}body{margin:0;background:#f5efe5;color:#21312b;font-family:Arial,sans-serif;line-height:1.6}.page{max-width:1000px;margin:auto;padding:24px}h1,h2,h3{color:#285d45}.hero,.route,article{background:#fffdf8;border:1px solid #d9d0c1;border-radius:16px;padding:18px;margin:14px 0}.hero{background:#19382a;color:#fff}.hero h1{color:#fff}.route-meta{color:#66736d}.route article{background:#f7f2e9}.route article header{display:flex;justify-content:space-between}.tags{display:flex;gap:6px;flex-wrap:wrap}.tags span{background:#e4efe7;border-radius:999px;padding:4px 9px}.photos{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.photos figure{margin:0}.photos img{width:100%;max-height:430px;object-fit:cover;border-radius:12px}.photos figcaption{font-size:.8rem;color:#66736d}blockquote{border-right:5px solid #c76a42;margin:10px 0;padding:8px 13px;background:#fff}@media(max-width:650px){.page{padding:10px}.photos{grid-template-columns:1fr}}@media print{body{background:#fff}.page{max-width:none}.route{break-before:page}}</style></head><body><main class="page"><header class="hero"><h1>דוח הערות וביקורות מהשטח</h1><p>גרסת מוצר ${PRODUCT_VERSION} · גרסת מסמך ${DOC_VERSION} · הופק ${new Date().toLocaleString('he-IL')}</p><p>${reports.length} דיווחים על ${grouped.size} מסלולים. הדוח הופק מן האחסון המקומי של המשתמש.</p></header>${sections || '<section class="route"><p>אין דיווחים שמורים.</p></section>'}</main></body></html>`;
    downloadBlob(new Blob(['\ufeff', html], {type:'text/html;charset=utf-8'}), `דוח-יומן-מסלולים_${new Date().toISOString().slice(0,10)}_גרסת-מסמך-${DOC_VERSION}.html`);
    showToast('דוח ה־HTML הורד');
  }

  async function routeExportHtml(routeId) {
    const reports = await allReports(routeId);
    if (!reports.length) return '';
    const media = await allMedia();
    const allowed = new Set(reports.map(item => item.id));
    const mediaMap = new Map();
    for (const item of media.filter(item => allowed.has(item.reportId))) {
      if (!mediaMap.has(item.reportId)) mediaMap.set(item.reportId, []);
      mediaMap.get(item.reportId).push({...item, dataUrl:await blobToDataUrl(item.blob)});
    }
    const reportsHtml = reports.map(report => `<article class="local-report"><h3>${escapeHtml(formatDate(report.riddenOn))}${report.rating ? ` · ${'★'.repeat(report.rating)}${'☆'.repeat(5-report.rating)}` : ''}</h3><p><b>${escapeHtml(sourceLabel(report.sourceType))}</b>${report.author ? ` · ${escapeHtml(report.author)}` : ''}</p>${report.noteText ? `<p>${escapeHtml(report.noteText).replace(/\n/g,'<br>')}</p>` : ''}${report.reviewText ? `<blockquote>${escapeHtml(report.reviewText).replace(/\n/g,'<br>')}</blockquote>` : ''}${(report.videoLinks || []).map(validHttpUrl).filter(Boolean).map(url => `<p><a href="${escapeHtml(url)}">סרטון מצורף</a></p>`).join('')}${(mediaMap.get(report.id) || []).map(item => `<img src="${item.dataUrl}" alt="${escapeHtml(item.name)}" style="width:100%;max-height:480px;object-fit:cover;border-radius:12px;margin-top:8px">`).join('')}</article>`).join('');
    return `<section class="local-field-notes"><h2>הערות וביקורות מקומיות</h2><p>המידע הבא נשמר במכשיר המשתמש ולא אומת בידי עורך המדריך.</p>${reportsHtml}</section>`;
  }

  function bindEvents() {
    document.addEventListener('click', async event => {
      const routeButton = event.target.closest('.field-notes-action');
      if (routeButton) { await openRouteNotes(routeButton.closest('.route-card')); return; }
      if (event.target.closest('#fieldNotesHubButton')) { await renderHub(); openModal($('#fieldNotesHub')); return; }
      const close = event.target.closest('[data-field-close]');
      if (close) { clearObjectUrls(); closeModal(close.closest('.dialog-shell')); return; }
      if (event.target.classList.contains('field-notes-shell')) { clearObjectUrls(); closeModal(event.target); return; }
      const edit = event.target.closest('[data-edit-report]');
      if (edit) {
        if (!$('#fieldNotesHub').hidden) closeModal($('#fieldNotesHub'));
        await editReport(edit.dataset.editReport);
        return;
      }
      const remove = event.target.closest('[data-delete-report]');
      if (remove) { await deleteReport(remove.dataset.deleteReport); return; }
    });
    $('#field-note-form').addEventListener('submit', saveReport);
    $('#field-note-reset').addEventListener('click', resetForm);
    $('#field-note-source-type').addEventListener('change', event => { $('#field-note-source-url-wrap').hidden = event.target.value !== 'internet'; });
    $('#field-note-export-route').addEventListener('click', async () => {
      const file = await backupFile(activeRouteId);
      downloadBlob(file, file.name);
      showToast('נתוני המסלול והתמונות הורדו');
    });
    $('#field-download-backup').addEventListener('click', async () => {
      const file = await backupFile();
      downloadBlob(file, file.name);
      showToast('הגיבוי המלא הורד');
    });
    $('#field-share-backup').addEventListener('click', () => shareBackup().catch(error => { console.error(error); showToast('שיתוף הגיבוי נכשל'); }));
    $('#field-export-report').addEventListener('click', () => exportHtmlReport().catch(error => { console.error(error); showToast('הפקת הדוח נכשלה'); }));
    $('#field-import-backup').addEventListener('change', async event => {
      const file = event.target.files?.[0];
      event.target.value = '';
      if (!file) return;
      try {
        if (file.size > 150 * 1024 * 1024) throw new Error('קובץ הגיבוי גדול מ־150MB');
        await importBackup(file);
      }
      catch (error) { console.error(error); showToast(error?.message || 'ייבוא הגיבוי נכשל'); }
    });
  }

  async function initialize() {
    if (!('indexedDB' in window)) {
      console.warn('IndexedDB is unavailable; local field notes are disabled.');
      return;
    }
    buildUi();
    bindEvents();
    await openDb();
    await deviceId();
    await refreshBadges();
    window.R123FieldNotes = {routeExportHtml, exportPackage, schemaVersion:EXPORT_SCHEMA_VERSION};
    console.info(`Local field notes ready, schema ${EXPORT_SCHEMA_VERSION}, document ${DOC_VERSION}`);
  }

  initialize().catch(error => {
    console.error('Local field notes failed to initialize', error);
    showToast('היומן המקומי לא הופעל בדפדפן הזה');
  });
})();
