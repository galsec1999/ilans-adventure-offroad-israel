/* ספר מסלולי אדוונצ׳ר ואופרוד — גרסת מסמך 2.1.5; גרסת מוצר 2.1.0 */
(() => {
  'use strict';

  const PRODUCT_VERSION = '2.1.0';
  const DOC_VERSION = '2.1.5';
  const OFFROAD_METADATA = window.OFFROAD_TRACK_METADATA?.records || {};
  const INVITE_STORAGE_KEY = 'routeGuideInviteDefaultsV21';
  const THEME_STORAGE_KEY = 'routeGuideThemeV21';
  const cards = [...document.querySelectorAll('.route-card')];
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const toast = $('#toast');
  let toastTimer;
  let deferredInstallPrompt = null;
  let activeCard = null;
  let lastFocus = null;
  let invitePreviewDirty = false;

  function plain(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  }

  function showToast(message) {
    clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.add('show');
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
  }

  function cardTitle(card) {
    return plain($('.route-title', card)?.textContent);
  }

  function cardMeta(card) {
    const result = {};
    $$('.meta > div', card).forEach(item => {
      const key = plain($('small', item)?.textContent);
      const value = plain($('b', item)?.textContent);
      if (key) result[key] = value;
    });
    return result;
  }

  function trackIds(card) {
    return [...new Set($$('a[href*="off-road.io/track/"]', card).map(link => link.href.match(/\/track\/(\d+)/)?.[1]).filter(Boolean))];
  }

  function trackRecords(card) {
    return trackIds(card).map(trackId => OFFROAD_METADATA[trackId] || {
      trackId,
      publicUrl:`https://off-road.io/track/${trackId}`,
      status:'missing'
    });
  }

  function sourceDistanceDuration(record) {
    if (!record || record.status !== 'verified') return 'לא זמין במקור';
    const parts = [];
    if (Number(record.distanceKm) > 0) parts.push(`${Number(record.distanceKm).toLocaleString('he-IL', {maximumFractionDigits:1})} ק״מ`);
    if (record.durationDisplay) parts.push(record.durationDisplay);
    return parts.join(' · ') || 'לא צוין במקור';
  }

  function sourceTrackSummary(record, index, total) {
    const prefix = total > 1 ? `הקלטה ${index + 1}: ` : '';
    if (!record || record.status !== 'verified') return `${prefix}הנתונים אינם זמינים עוד ב־Off-Road`;
    return `${prefix}${record.title || `Track ${record.trackId}`} — ${sourceDistanceDuration(record)} · ${record.activityDisplay || 'פעילות לא צוינה'} · ${record.difficultyDisplay || 'קושי לא דורג'}`;
  }

  function addMetaItem(card, label, value) {
    const meta = $('.meta', card);
    if (!meta || !value) return;
    const existing = $$('.meta > div', card).find(item => plain($('small', item)?.textContent) === label);
    if (existing) {
      const target = $('b', existing);
      if (target) target.textContent = value;
      return;
    }
    const item = document.createElement('div');
    const small = document.createElement('small');
    const strong = document.createElement('b');
    small.textContent = label;
    strong.textContent = value;
    item.append(small, strong);
    meta.append(item);
  }

  function enrichOffroadCards() {
    cards.forEach(card => {
      const records = trackRecords(card);
      if (!records.length) return;
      const verified = records.filter(record => record.status === 'verified');
      const primary = verified[0];

      if (records.length === 1 && primary) {
        const currentMeta = cardMeta(card);
        if (!/ק״מ|שעה|דקות/.test(currentMeta['אורך / זמן'] || '')) addMetaItem(card, 'אורך / זמן', sourceDistanceDuration(primary));
        if (!currentMeta['פעילות במקור']) addMetaItem(card, 'פעילות במקור', primary.activityDisplay || 'לא צוין במקור');
        addMetaItem(card, 'קושי ב־Off-Road', primary.difficultyDisplay || 'לא דורג במקור');
        if (!card.dataset.distance && Number(primary.distanceKm) > 0) card.dataset.distance = String(primary.distanceKm);
        const facts = $('.summary-facts', card);
        if (facts && !/ק״מ/.test(facts.textContent) && sourceDistanceDuration(primary) !== 'לא צוין במקור') {
          facts.textContent += ` · ${sourceDistanceDuration(primary)}`;
        }
      }

      const nav = $('.nav-block', card);
      if (!nav || $('.offroad-source-data', nav)) return;
      const section = document.createElement('section');
      section.className = 'offroad-source-data';
      const heading = document.createElement('h5');
      heading.textContent = records.length > 1 ? 'נתוני Off-Road לכל ההקלטות בכרטיס' : 'נתוני Off-Road של ההקלטה';
      const grid = document.createElement('div');
      grid.className = 'offroad-source-grid';
      records.forEach((record, index) => {
        const item = document.createElement('article');
        item.className = `offroad-source-item ${record.status === 'verified' ? 'verified' : 'unavailable'}`;
        const title = document.createElement('strong');
        title.textContent = record.status === 'verified' ? (record.title || `Track ${record.trackId}`) : `Track ${record.trackId}`;
        const facts = document.createElement('span');
        facts.textContent = sourceTrackSummary(record, index, records.length).replace(/^הקלטה \d+: /, '').replace(/^.*? — /, '');
        const note = document.createElement('small');
        note.textContent = record.status === 'verified'
          ? 'מטא־דאטה מן המקור; אינו אישור שהמסלול תקין, פתוח או מתאים היום.'
          : 'ה־Track אינו זמין כעת ב־API; הקישור נשמר לבדיקה ידנית.';
        item.append(title, facts, note);
        grid.append(item);
      });
      section.append(heading, grid);
      nav.prepend(section);
    });
  }

  enrichOffroadCards();

  function sectionText(card, heading) {
    const section = $$('.content-block, .warning, .reviews-block', card).find(item => plain($('h4', item)?.textContent).includes(heading));
    if (!section) return '';
    const clone = section.cloneNode(true);
    clone.querySelector('h4')?.remove();
    return plain(clone.textContent);
  }

  function routeData(card) {
    const meta = cardMeta(card);
    const offroadTracks = trackRecords(card);
    const primarySource = offroadTracks.find(record => record.status === 'verified');
    const sourceActivities = [...new Set(offroadTracks.filter(record => record.status === 'verified').map(record => record.activityDisplay).filter(Boolean))];
    const mapUrls = [...new Set($$('a[href*="off-road.io/track/"]', card).map(link => link.href))];
    const primaryMap = mapUrls[0] || '';
    const trackMatch = primaryMap.match(/\/track\/(\d+)/);
    const photo = $('.route-photo img', card);
    const qr = $('.nav-block img.qr', card);
    const marketing = plain($('.marketing p', card)?.textContent);
    const factual = sectionText(card, 'תיאור עובדתי') || sectionText(card, 'תיאור המקור') || sectionText(card, 'נתוני המקור');
    return {
      id: card.id,
      title: cardTitle(card),
      region: meta['אזור'] || card.dataset.region || 'לא צוין',
      subregion: meta['תת־אזור'] || card.dataset.subregion || 'לא צוין',
      start: meta['יציאה'] || meta['נקודת התחלה'] || 'לא צוין',
      finish: meta['סיום'] || meta['נקודת סיום'] || 'לא צוין',
      difficultySource: offroadTracks.length > 1 ? 'מופיע לכל הקלטה בנפרד' : (primarySource?.difficultyDisplay || meta['דירוג מקור'] || meta['קושי במקור'] || meta['קושי'] || 'לא דורג'),
      difficultyNormalized: card.dataset.difficulty || 'לא אומת',
      distanceDuration: offroadTracks.length > 1 ? `${offroadTracks.length} הקלטות — הנתונים מפורטים בנפרד` : (primarySource ? sourceDistanceDuration(primarySource) : (meta['אורך / זמן'] || 'לא צוין')),
      routeType: sourceActivities.length ? sourceActivities.join(' / ') : (meta['סוג'] || meta['פעילות במקור'] || 'אופרוד / אדוונצ׳ר'),
      verificationStatus: card.dataset.status || 'נדרש אימות עדכני',
      quality: card.dataset.quality || 'חלקי',
      description: marketing || factual || 'בכרטיס לא קיים תיאור מסלול מפורט.',
      mapUrls,
      offroadTracks,
      offroadTrackSummaries: offroadTracks.map((record, index) => sourceTrackSummary(record, index, offroadTracks.length)),
      primaryMap,
      trackId: trackMatch?.[1] || '',
      photoUrl: photo?.src || '',
      photoAlt: photo?.alt || '',
      photoCaption: plain($('.route-photo figcaption', card)?.textContent),
      qrUrl: qr?.src || '',
      sights: sectionText(card, 'מה רואים') || sectionText(card, 'נקודות עניין'),
      warnings: sectionText(card, 'לפני יציאה') || sectionText(card, 'חשוב לפני יציאה'),
      reviews: sectionText(card, 'דירוגי משתמשים'),
      cardUrl: `${location.href.split('#')[0]}#${card.id}`
    };
  }

  async function copyText(text, success = 'הטקסט הועתק') {
    try {
      await navigator.clipboard.writeText(text);
    } catch (_) {
      const box = document.createElement('textarea');
      box.value = text;
      box.style.position = 'fixed';
      box.style.opacity = '0';
      document.body.appendChild(box);
      box.select();
      document.execCommand('copy');
      box.remove();
    }
    showToast(success);
  }

  function fillSelect(select, values, allLabel) {
    if (!select) return;
    const current = select.value;
    select.replaceChildren(new Option(allLabel, ''));
    [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b, 'he')).forEach(value => select.add(new Option(value, value)));
    if ([...select.options].some(option => option.value === current)) select.value = current;
  }

  const filterIds = ['q', 'region', 'subregion', 'difficulty', 'surface', 'shape', 'status', 'quality', 'source', 'map'];
  const filters = Object.fromEntries(filterIds.map(id => [id, $('#' + id)]));
  const sortSelect = $('#sort');

  function updateSubregions() {
    const region = filters.region.value;
    const values = cards.filter(card => !region || card.dataset.region === region).map(card => card.dataset.subregion || 'לא צוין');
    fillSelect(filters.subregion, values, 'כל תתי־האזורים');
  }

  function sortCards() {
    const routeList = $('#routes');
    const order = sortSelect?.value || 'original';
    const difficultyOrder = {'קל':1,'קל–בינוני':2,'בינוני':3,'בינוני–קשה':4,'קשה / מומחים':5,'לא אומת':99};
    const qualityOrder = {'כרטיס מלא':1,'כרטיס שימושי חלקית':2,'מידע חסר':3,'סגור / לא זמין':4};
    const sorted = [...cards].sort((a, b) => {
      if (order === 'title') return cardTitle(a).localeCompare(cardTitle(b), 'he');
      if (order === 'region') return (a.dataset.region || '').localeCompare(b.dataset.region || '', 'he') || cardTitle(a).localeCompare(cardTitle(b), 'he');
      if (order === 'difficulty') return (difficultyOrder[a.dataset.difficulty] ?? 90) - (difficultyOrder[b.dataset.difficulty] ?? 90) || cardTitle(a).localeCompare(cardTitle(b), 'he');
      if (order === 'quality') return (qualityOrder[a.dataset.quality] ?? 90) - (qualityOrder[b.dataset.quality] ?? 90) || Number(a.dataset.originalOrder) - Number(b.dataset.originalOrder);
      if (order === 'distance-asc' || order === 'distance-desc') {
        const av = Number(a.dataset.distance || Number.POSITIVE_INFINITY);
        const bv = Number(b.dataset.distance || Number.POSITIVE_INFINITY);
        if (Number.isFinite(av) && Number.isFinite(bv) && av !== bv) return order === 'distance-asc' ? av - bv : bv - av;
        if (Number.isFinite(av) !== Number.isFinite(bv)) return Number.isFinite(av) ? -1 : 1;
      }
      return Number(a.dataset.originalOrder) - Number(b.dataset.originalOrder);
    });
    const empty = $('#empty');
    sorted.forEach(card => routeList.insertBefore(card, empty));
  }

  function applyFilters() {
    const query = plain(filters.q.value).toLocaleLowerCase('he');
    let visible = 0;
    cards.forEach(card => {
      const surfaces = (card.dataset.surface || '').split('|');
      const matches = (!query || (card.dataset.search || card.textContent).toLocaleLowerCase('he').includes(query)) &&
        (!filters.region.value || card.dataset.region === filters.region.value) &&
        (!filters.subregion.value || card.dataset.subregion === filters.subregion.value) &&
        (!filters.difficulty.value || card.dataset.difficulty === filters.difficulty.value) &&
        (!filters.surface.value || surfaces.includes(filters.surface.value)) &&
        (!filters.shape.value || card.dataset.shape === filters.shape.value) &&
        (!filters.status.value || card.dataset.status === filters.status.value) &&
        (!filters.quality.value || card.dataset.quality === filters.quality.value) &&
        (!filters.source.value || card.dataset.source === filters.source.value) &&
        (!filters.map.value || card.dataset.map === filters.map.value);
      card.hidden = !matches;
      if (matches) visible += 1;
    });
    $('#resultCount').textContent = `${visible} מתוך ${cards.length} כרטיסים`;
    $('#empty').style.display = visible ? 'none' : 'block';
    sortCards();
  }

  fillSelect(filters.region, cards.map(card => card.dataset.region), 'כל האזורים');
  fillSelect(filters.difficulty, cards.map(card => card.dataset.difficulty), 'כל רמות הקושי');
  fillSelect(filters.surface, cards.flatMap(card => (card.dataset.surface || '').split('|')), 'כל סוגי התוואי');
  fillSelect(filters.shape, cards.map(card => card.dataset.shape), 'כל צורות המסלול');
  fillSelect(filters.status, cards.map(card => card.dataset.status), 'כל מצבי האימות');
  fillSelect(filters.quality, cards.map(card => card.dataset.quality), 'כל רמות השלמות');
  fillSelect(filters.source, cards.map(card => card.dataset.source), 'כל מקורות הכרטיסים');
  updateSubregions();
  filterIds.forEach(id => filters[id].addEventListener(id === 'q' ? 'input' : 'change', () => {
    if (id === 'region') updateSubregions();
    applyFilters();
  }));
  sortSelect?.addEventListener('change', applyFilters);
  $('#resetFilters').addEventListener('click', () => {
    filterIds.forEach(id => { filters[id].value = ''; });
    if (sortSelect) sortSelect.value = 'original';
    updateSubregions();
    applyFilters();
    filters.q.focus();
  });
  $('#expandVisible').addEventListener('click', () => cards.filter(card => !card.hidden).forEach(card => { card.open = true; }));
  $('#collapseAll').addEventListener('click', () => cards.forEach(card => { card.open = false; }));
  applyFilters();

  const themeSelect = $('#theme');
  function applyTheme(preference) {
    const theme = preference === 'system' ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : preference;
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#151c18' : '#285d45');
  }
  themeSelect.value = localStorage.getItem(THEME_STORAGE_KEY) || 'light';
  applyTheme(themeSelect.value);
  themeSelect.addEventListener('change', () => {
    localStorage.setItem(THEME_STORAGE_KEY, themeSelect.value);
    applyTheme(themeSelect.value);
  });
  matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', () => {
    if (themeSelect.value === 'system') applyTheme('system');
  });

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

  $$('.dialog-shell').forEach(modal => {
    modal.addEventListener('click', event => {
      if (event.target === modal || event.target.closest('[data-close]')) closeModal(modal);
    });
  });

  document.addEventListener('keydown', event => {
    const modal = $('.dialog-shell:not([hidden])');
    if (!modal) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      closeModal(modal);
      return;
    }
    if (event.key !== 'Tab') return;
    const focusables = $$('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])', modal).filter(el => !el.closest('[hidden]'));
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });

  function validClock(value) {
    return /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(String(value || ''));
  }

  function clockMinutes(value) {
    const [hours, minutes] = String(value || '').split(':').map(Number);
    return hours * 60 + minutes;
  }

  function safeInviteTimes(meetupTime, departureTime) {
    if (!validClock(meetupTime) || !validClock(departureTime) || clockMinutes(departureTime) <= clockMinutes(meetupTime)) {
      return {meetupTime:'07:00', departureTime:'07:15'};
    }
    return {meetupTime, departureTime};
  }

  function validInviteLimit(value) {
    const limit = Number(plain(value));
    return plain(value) !== '' && Number.isInteger(limit) && limit >= 1 && limit <= 100;
  }

  function safeInviteLimit(value) {
    return validInviteLimit(value) ? String(Number(value)) : '12';
  }

  function clockValue(minutes) {
    const safeMinutes = Math.max(0, Math.min(1439, minutes));
    return `${String(Math.floor(safeMinutes / 60)).padStart(2, '0')}:${String(safeMinutes % 60).padStart(2, '0')}`;
  }

  function normalizeInviteTimeOrder(changedId) {
    const meetup = $('#invite-meetup-time');
    const departure = $('#invite-departure-time');
    if (!validClock(meetup.value) || !validClock(departure.value) || clockMinutes(departure.value) > clockMinutes(meetup.value)) return;
    if (changedId === 'invite-departure-time' && clockMinutes(departure.value) >= 15) {
      meetup.value = clockValue(clockMinutes(departure.value) - 15);
      return;
    }
    if (clockMinutes(meetup.value) <= 1424) {
      departure.value = clockValue(clockMinutes(meetup.value) + 15);
      return;
    }
    meetup.value = '23:30';
    departure.value = '23:45';
  }

  function readInviteDefaults() {
    try {
      const defaults = JSON.parse(localStorage.getItem(INVITE_STORAGE_KEY) || '{}');
      return {...defaults, limit: safeInviteLimit(defaults.limit), ...safeInviteTimes(defaults.meetupTime, defaults.departureTime)};
    }
    catch (_) { return {meetupTime:'07:00', departureTime:'07:15'}; }
  }

  function saveInviteDefaults() {
    const times = safeInviteTimes($('#invite-meetup-time').value, $('#invite-departure-time').value);
    if (times.meetupTime !== $('#invite-meetup-time').value || times.departureTime !== $('#invite-departure-time').value) return;
    if (!validInviteLimit($('#invite-limit').value)) return;
    const limit = Number($('#invite-limit').value);
    const safe = {
      meetupTime: times.meetupTime,
      departureTime: times.departureTime,
      pace: $('#invite-pace').value,
      limit: String(limit),
      registrationMode: $('#invite-registration-mode').value
    };
    localStorage.setItem(INVITE_STORAGE_KEY, JSON.stringify(safe));
  }

  function value(id) {
    return plain($('#invite-' + id)?.value);
  }

  function formatHebrewDate(dateValue) {
    if (!dateValue) return '';
    const date = new Date(`${dateValue}T12:00:00`);
    if (Number.isNaN(date.getTime())) return dateValue;
    return new Intl.DateTimeFormat('he-IL', {weekday:'long',day:'numeric',month:'long',year:'numeric'}).format(date);
  }

  function chosenPace() {
    return value('pace') === 'אחר' ? value('pace-custom') : value('pace');
  }

  function makeInvite(card) {
    const data = routeData(card);
    const registrationMode = value('registration-mode');
    const groupUrl = value('group-url');
    const maps = data.mapUrls;
    const mapLines = maps.length ? [
      '🗺️ מפת המסלול ב־Off‑Road:',
      maps[0],
      ...(maps.length > 1 ? ['', 'מפות חלופיות:', ...maps.slice(1).map((url, index) => `${index + 1}. ${url}`)] : [])
    ] : ['🗺️ אין בכרטיס קישור ניווט מאומת — המוביל חייב להשלים ניווט לפני פרסום ויציאה.'];
    const sourceLines = data.offroadTrackSummaries.length
      ? ['📊 נתוני Off‑Road מן ההקלטה:', ...data.offroadTrackSummaries]
      : [];
    const registration = registrationMode === 'קבוצת WhatsApp ייעודית'
      ? `✅ הרשמה: הצטרפות לקבוצת WhatsApp ייעודית${groupUrl ? `\n${groupUrl}` : ''}`
      : '✅ הרשמה: אישור אישי בהודעה פרטית למוביל';
    return [
      `🏍️ טיול אדוונצ׳ר / אופרוד — ${data.title}`,
      '',
      `📅 ${formatHebrewDate(value('date')) || '[יש להשלים תאריך]'}`,
      `📍 מפגש: ${value('meet') || '[יש להשלים נקודת מפגש]'}`,
      `🕖 שעת מפגש: ${value('meetup-time') || '[יש להשלים שעה]'}`,
      `🚦 יציאה: ${value('departure-time') || '[יש להשלים שעה]'}`,
      '',
      '🌿 מה בתכנון:',
      data.description,
      '',
      `🧭 אזור: ${data.region}${data.subregion && data.subregion !== 'לא צוין' ? ` — ${data.subregion}` : ''}`,
      `⚙️ קושי מתועד במקור: ${data.difficultySource}`,
      `📏 אורך / זמן: ${data.distanceDuration}`,
      `🏍️ פעילות במקור: ${data.routeType}`,
      `🏍️ קצב: ${chosenPace() || '[יש לבחור קצב]'}`,
      `👥 עד ${value('limit') || '[X]'} רוכבים`,
      '',
      ...mapLines,
      ...(sourceLines.length ? ['', ...sourceLines] : []),
      '',
      registration,
      value('notes') ? `ℹ️ הערות: ${value('notes')}` : '',
      '',
      '⚠️ רכיבת חברים באחריות כל רוכב. יש לוודא סמוך ליציאה חוקיות, פתיחה, מזג אוויר, שטחי אש, ביטחון, מצב השטח והתאמה לקבוצה. רמת קושי היא סובייקטיבית. המדריך אינו אישור למסלול.',
      '',
      `📖 כרטיס הטיול המלא: ${data.cardUrl}`
    ].filter((line, index, all) => line || (index > 0 && all[index - 1])).join('\n').replace(/\n{3,}/g, '\n\n').trim();
  }

  function setConditionalInviteFields() {
    const custom = value('pace') === 'אחר';
    $('#invite-pace-custom-wrap').hidden = !custom;
    const group = value('registration-mode') === 'קבוצת WhatsApp ייעודית';
    $('#invite-group-url-wrap').hidden = !group;
  }

  function updateCharacterCount() {
    $('#invite-char-count').textContent = `${$('#invite-preview').value.length.toLocaleString('he-IL')} תווים`;
  }

  function refreshInvite(force = false) {
    if (!activeCard) return;
    setConditionalInviteFields();
    if (!validInviteLimit(value('limit'))) {
      $('#invite-error').textContent = 'מגבלת המשתתפים חייבת להיות מספר שלם בין 1 ל־100.';
      updateCharacterCount();
      return;
    }
    if (!invitePreviewDirty || force) {
      $('#invite-preview').value = makeInvite(activeCard);
      invitePreviewDirty = false;
    }
    updateCharacterCount();
    saveInviteDefaults();
    drawInvitePoster().catch(() => {});
  }

  function clearInviteError() {
    $('#invite-error').textContent = '';
  }

  function validationError(message, field) {
    $('#invite-error').textContent = message;
    field?.focus();
    return false;
  }

  function validateInvite() {
    $('#invite-error').textContent = '';
    const required = [
      ['date', 'יש להשלים תאריך טיול.'],
      ['meet', 'יש להשלים נקודת מפגש.'],
      ['meetup-time', 'יש להשלים שעת מפגש.'],
      ['departure-time', 'יש להשלים שעת יציאה.'],
      ['pace', 'יש לבחור קצב רכיבה.'],
      ['limit', 'יש להשלים מגבלת משתתפים.']
    ];
    for (const [id, message] of required) {
      const field = $('#invite-' + id);
      if (!plain(field.value)) return validationError(message, field);
    }
    if (!validInviteLimit(value('limit'))) return validationError('מגבלת המשתתפים חייבת להיות מספר שלם בין 1 ל־100.', $('#invite-limit'));
    if (clockMinutes(value('departure-time')) <= clockMinutes(value('meetup-time'))) return validationError('שעת היציאה חייבת להיות מאוחרת משעת המפגש.', $('#invite-departure-time'));
    if (value('pace') === 'אחר' && !value('pace-custom')) return validationError('יש להשלים את תיאור הקצב.', $('#invite-pace-custom'));
    if (value('registration-mode') === 'קבוצת WhatsApp ייעודית') {
      const field = $('#invite-group-url');
      if (!/^https:\/\/(?:chat\.whatsapp\.com|wa\.me)\//i.test(field.value.trim())) return validationError('יש להזין קישור WhatsApp תקין שמתחיל ב־https://.', field);
    }
    const data = routeData(activeCard);
    if (!data.primaryMap && !$('#invite-no-map-confirm').checked) return validationError('אין בכרטיס מפה מאומתת. יש לאשר שהמוביל ישלים ניווט לפני פרסום.', $('#invite-no-map-confirm'));
    if (/\[(?:יש להשלים|X)/.test($('#invite-preview').value)) return validationError('בתצוגה המקדימה נשארו פרטים שלא הושלמו.', $('#invite-preview'));
    return true;
  }

  function loadImage(src) {
    return new Promise((resolve, reject) => {
      if (!src) return reject(new Error('missing image'));
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = src;
    });
  }

  function drawCover(ctx, image, width, height) {
    const scale = Math.max(width / image.naturalWidth, height / image.naturalHeight);
    const drawWidth = image.naturalWidth * scale;
    const drawHeight = image.naturalHeight * scale;
    ctx.drawImage(image, (width - drawWidth) / 2, (height - drawHeight) / 2, drawWidth, drawHeight);
  }

  function wrapCanvasText(ctx, text, x, y, maxWidth, lineHeight, maxLines = 4) {
    const words = plain(text).split(' ');
    const lines = [];
    let line = '';
    words.forEach(word => {
      const test = line ? `${line} ${word}` : word;
      if (ctx.measureText(test).width > maxWidth && line) { lines.push(line); line = word; }
      else line = test;
    });
    if (line) lines.push(line);
    const clipped = lines.slice(0, maxLines);
    if (lines.length > maxLines) clipped[maxLines - 1] = clipped[maxLines - 1].replace(/[.…]*$/, '') + '…';
    clipped.forEach((row, index) => ctx.fillText(row, x, y + index * lineHeight));
    return y + clipped.length * lineHeight;
  }

  async function drawInvitePoster() {
    if (!activeCard) return;
    const canvas = $('#invite-poster');
    const ctx = canvas.getContext('2d');
    const data = routeData(activeCard);
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#1d3428';
    ctx.fillRect(0, 0, width, height);
    try {
      const image = await loadImage(data.photoUrl);
      drawCover(ctx, image, width, 690);
    } catch (_) {
      const gradient = ctx.createLinearGradient(0, 0, width, 690);
      gradient.addColorStop(0, '#315c46');
      gradient.addColorStop(1, '#9d5e3f');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, 690);
    }
    const overlay = ctx.createLinearGradient(0, 160, 0, 760);
    overlay.addColorStop(0, 'rgba(18,33,25,.06)');
    overlay.addColorStop(1, 'rgba(18,33,25,.96)');
    ctx.fillStyle = overlay;
    ctx.fillRect(0, 0, width, 790);
    ctx.direction = 'rtl';
    ctx.textAlign = 'right';
    ctx.fillStyle = '#f4cf9d';
    ctx.font = '700 31px Arial';
    ctx.fillText('טיול אדוונצ׳ר / אופרוד', width - 74, 90);
    ctx.font = '600 21px Arial';
    ctx.fillText(data.photoCaption.includes('אינו צילום') ? 'איור אווירה — אינו צילום מהמסלול' : 'תמונת מקור Off‑Road — מצב השטח עשוי להשתנות', width - 74, 126);
    ctx.fillStyle = '#ffffff';
    ctx.font = '800 62px Arial';
    let y = wrapCanvasText(ctx, data.title, width - 74, 170, width - 148, 72, 3);
    ctx.fillStyle = '#f7e8d3';
    ctx.font = '600 30px Arial';
    y = wrapCanvasText(ctx, data.description, width - 74, y + 26, width - 148, 42, 4);
    ctx.fillStyle = '#f7f2e9';
    ctx.fillRect(0, 760, width, height - 760);
    ctx.fillStyle = '#21312b';
    ctx.font = '800 38px Arial';
    ctx.fillText(formatHebrewDate(value('date')) || 'מועד יושלם לפני הפרסום', width - 74, 835);
    ctx.font = '700 29px Arial';
    const facts = [
      `מפגש: ${value('meet') || 'טרם נקבע'}`,
      `שעות: ${value('meetup-time') || '—'} / יציאה ${value('departure-time') || '—'}`,
      `קושי במקור: ${data.difficultySource}`,
      `אורך / זמן: ${data.distanceDuration}`,
      `עד ${value('limit') || '—'} רוכבים`
    ];
    facts.forEach((fact, index) => ctx.fillText(fact, width - 74, 902 + index * 48));
    ctx.fillStyle = '#285d45';
    ctx.fillRect(0, height - 150, width, 150);
    ctx.fillStyle = '#fff';
    ctx.font = '800 30px Arial';
    ctx.fillText(data.primaryMap ? 'סרקו לפתיחת מפת Off‑Road' : 'אין בכרטיס ניווט מאומת', width - 74, height - 93);
    ctx.font = '500 20px Arial';
    ctx.fillText(`יש לבדוק מסלול ותנאים סמוך ליציאה · גרסת מסמך ${DOC_VERSION}`, width - 74, height - 51);
    if (data.qrUrl) {
      try {
        const qr = await loadImage(data.qrUrl);
        ctx.fillStyle = '#fff';
        ctx.fillRect(58, height - 252, 212, 212);
        ctx.drawImage(qr, 68, height - 242, 192, 192);
      } catch (_) {}
    }
  }

  function showInvite(card) {
    if (card.dataset.status === 'סגור / לא זמין') {
      showToast('לא יוצרים הזמנה למסלול שמסומן כסגור או לא זמין');
      return;
    }
    activeCard = card;
    const data = routeData(card);
    const defaults = readInviteDefaults();
    $('#invite-route').textContent = data.title;
    $('#invite-meet').value = data.start !== 'לא צוין' && !/^\d+\.\d+/.test(data.start) ? data.start : '';
    $('#invite-meetup-time').value = defaults.meetupTime || '07:00';
    $('#invite-departure-time').value = defaults.departureTime || '07:15';
    $('#invite-pace').value = defaults.pace || 'ייקבע לפי הרוכבים שיגיעו';
    $('#invite-limit').value = defaults.limit || '12';
    $('#invite-registration-mode').value = defaults.registrationMode || 'אישור אישי בהודעה פרטית';
    $('#invite-date').value = '';
    $('#invite-notes').value = '';
    $('#invite-group-url').value = '';
    $('#invite-no-map-confirm').checked = false;
    $('#invite-no-map-wrap').hidden = Boolean(data.primaryMap);
    const status = $('#invite-map-status');
    status.className = `map-status ${data.primaryMap ? 'ok' : 'missing'}`;
    status.querySelector('strong').textContent = data.primaryMap ? 'מפת Off‑Road מחוברת להזמנה' : 'אין בכרטיס ניווט מאומת';
    $('#invite-map-link').hidden = !data.primaryMap;
    $('#invite-map-link').href = data.primaryMap || '#';
    $('#invite-map-toggle').hidden = !data.trackId;
    $('#invite-map-toggle').disabled = false;
    $('#invite-map-toggle').textContent = 'הצגת המפה בתוך המחולל';
    $('#invite-map-slot').replaceChildren();
    $('#invite-error').textContent = '';
    invitePreviewDirty = false;
    refreshInvite(true);
    openModal($('#inviteModal'));
    setTimeout(() => {
      const safeTimes = safeInviteTimes($('#invite-meetup-time').value, $('#invite-departure-time').value);
      $('#invite-meetup-time').value = safeTimes.meetupTime;
      $('#invite-departure-time').value = safeTimes.departureTime;
      refreshInvite(true);
    }, 120);
  }

  $$('#inviteModal input, #inviteModal select').forEach(element => element.addEventListener('input', event => {
    clearInviteError();
    if (event.currentTarget.id === 'invite-meetup-time' || event.currentTarget.id === 'invite-departure-time') {
      normalizeInviteTimeOrder(event.currentTarget.id);
    }
    if (event.currentTarget.id === 'invite-limit' && plain(event.currentTarget.value)) {
      if (!validInviteLimit(event.currentTarget.value)) {
        $('#invite-error').textContent = 'מגבלת המשתתפים חייבת להיות מספר שלם בין 1 ל־100.';
        return;
      }
    }
    refreshInvite(false);
  }));
  $('#invite-notes').addEventListener('input', () => { clearInviteError(); refreshInvite(false); });
  $('#invite-preview').addEventListener('input', () => { invitePreviewDirty = true; updateCharacterCount(); });
  $('#invite-refresh').addEventListener('click', () => refreshInvite(true));
  $('#invite-map-toggle').addEventListener('click', () => {
    const data = routeData(activeCard);
    const slot = $('#invite-map-slot');
    if (!data.trackId || slot.querySelector('iframe')) return;
    const iframe = document.createElement('iframe');
    iframe.loading = 'lazy';
    iframe.referrerPolicy = 'no-referrer-when-downgrade';
    iframe.title = `מפת Off‑Road עבור ${data.title}`;
    iframe.src = `https://off-road.io/_v2/track/${data.trackId}?embedded=true`;
    slot.appendChild(iframe);
    $('#invite-map-toggle').textContent = 'המפה נטענה';
    $('#invite-map-toggle').disabled = true;
  });
  $('#invite-copy').addEventListener('click', () => { if (validateInvite()) copyText($('#invite-preview').value, 'ההזמנה הועתקה'); });
  $('#invite-whatsapp').addEventListener('click', () => { if (validateInvite()) window.open(`https://wa.me/?text=${encodeURIComponent($('#invite-preview').value)}`, '_blank', 'noopener'); });

  function canvasBlob() {
    return new Promise(resolve => $('#invite-poster').toBlob(resolve, 'image/png', 1));
  }

  function safeFileName(value) {
    return plain(value).replace(/[\\/:*?"<>|]/g, '-').replace(/\s+/g, '_').slice(0, 110) || 'trip';
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1200);
  }

  $('#invite-poster-download').addEventListener('click', async () => {
    await drawInvitePoster();
    const blob = await canvasBlob();
    if (blob) downloadBlob(blob, `הזמנה_${safeFileName(cardTitle(activeCard))}.png`);
  });
  $('#invite-poster-share').addEventListener('click', async () => {
    if (!validateInvite()) return;
    await drawInvitePoster();
    const blob = await canvasBlob();
    const file = blob ? new File([blob], `הזמנה_${safeFileName(cardTitle(activeCard))}.png`, {type:'image/png'}) : null;
    if (file && navigator.canShare?.({files:[file]})) {
      try { await navigator.share({title:cardTitle(activeCard), text:$('#invite-preview').value, files:[file]}); }
      catch (error) {
        if (error?.name === 'AbortError') return;
        if (blob) downloadBlob(blob, `הזמנה_${safeFileName(cardTitle(activeCard))}.png`);
        await copyText($('#invite-preview').value, 'השיתוף נכשל; התמונה נשמרה והטקסט הועתק');
      }
    } else {
      if (blob) downloadBlob(blob, `הזמנה_${safeFileName(cardTitle(activeCard))}.png`);
      await copyText($('#invite-preview').value, 'התמונה נשמרה והטקסט הועתק');
    }
  });

  function buildAiPrompt(card) {
    const data = routeData(card);
    const meta = cardMeta(card);
    const question = plain($('#ai-question').value) || 'סכם את המסלול והדגש מה חסר לבדיקה לפני יציאה.';
    const payload = {
      title:data.title,
      id:data.id,
      region:data.region,
      subregion:data.subregion,
      normalizedDifficulty:data.difficultyNormalized,
      sourceDifficulty:data.difficultySource,
      distanceDuration:data.distanceDuration,
      sourceMetadata:meta,
      routeDescription:data.description,
      sights:data.sights || null,
      warnings:data.warnings || null,
      reviewsSummary:data.reviews || null,
      mapUrls:data.mapUrls,
      offroadTrackMetadata:data.offroadTracks,
      verificationStatus:data.verificationStatus,
      motorcycleSuitability:'לא אומתה אלא אם נאמר אחרת במפורש בנתונים'
    };
    return `אתה מסייע לרוכב לקרוא כרטיס מסלול, אך אינך מאמת את המסלול בזמן אמת. ה-AI אינו מאשר תקינות, בטיחות, חוקיות או פתיחה של מסלול.\n\nשאלת המשתמש: ${question}\n\nנתוני הכרטיס:\n${JSON.stringify(payload, null, 2)}\n\nכללי תשובה מחייבים:\n1. ענה בעברית ובקצרה ורק על בסיס הנתונים שסופקו.\n2. אם התשובה אינה נמצאת בנתונים, אמור במפורש: "אין מספיק נתונים בכרטיס כדי לדעת". אל תמציא, אל תנחש ואל תשלים עובדות.\n3. אל תקבע שהמסלול פתוח, חוקי, בטוח, עביר או מתאים לאופנוע אדוונצ׳ר כבד ללא נתון מפורש ועדכני.\n4. קושי הוא סובייקטיבי ותלוי ברוכב, באופנוע, בצמיגים, בעומס ובתנאי היום. אפשר לציין נקודות שבהן אחרים התקשו רק כדיווח עבר, עם ההסתייגות הזו.\n5. הפרד בין עובדות מתועדות, דיווחי מקור, מידע חסר והמלצות לבדיקה.\n6. המלץ לבדוק סמוך ליציאה מקורות רשמיים, תוואי, מזג אוויר, שיטפונות, ביטחון, שטחי אש, שמורות, שערים ושילוט.\n7. אל תציג את המדריך כאישור מסלול ואל תייחס ידע לאילן או לעורך המדריך.\n8. אם אתה מוסיף מידע חיצוני, סמן אותו במפורש, ציין מקור וקישור, והזהר שהוא דורש אימות עדכני.`;
  }

  function refreshAi() {
    if (activeCard) $('#ai-prompt').value = buildAiPrompt(activeCard);
  }
  $('#ai-question').addEventListener('input', refreshAi);
  function showAi(card) {
    activeCard = card;
    $('#ai-route').textContent = cardTitle(card);
    refreshAi();
    openModal($('#aiModal'));
  }
  $('#ai-copy').addEventListener('click', () => copyText($('#ai-prompt').value, 'הפרומפט הועתק — אפשר להדביק ב־AI שבמכשיר'));
  $('#ai-share').addEventListener('click', async () => {
    const text = $('#ai-prompt').value;
    if (navigator.share) {
      try { await navigator.share({title:`שאלה על ${cardTitle(activeCard)}`, text}); }
      catch (error) { if (error?.name !== 'AbortError') await copyText(text, 'השיתוף נכשל; הפרומפט הועתק'); }
    } else await copyText(text, 'השיתוף אינו נתמך כאן; הפרומפט הועתק');
  });

  function speakCard(card) {
    if (!('speechSynthesis' in window)) { showToast('הדפדפן אינו תומך בהקראה קולית'); return; }
    speechSynthesis.cancel();
    const data = routeData(card);
    const text = `${data.title}. אזור: ${data.region}. קושי מתועד: ${data.difficultySource}. אורך או זמן: ${data.distanceDuration}. ${data.description}. ${data.sights ? `נקודות בדרך: ${data.sights}.` : ''} ${data.warnings ? `נקודות לבדיקה: ${data.warnings}.` : ''} המידע אינו אישור למסלול ועלול להשתנות. יש לבדוק את כל הפרטים סמוך ליציאה.`;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'he-IL';
    utterance.rate = .94;
    const voice = speechSynthesis.getVoices().find(candidate => /^he/i.test(candidate.lang));
    if (voice) utterance.voice = voice;
    speechSynthesis.speak(utterance);
    showToast('ההקראה התחילה — לחיצה נוספת עוצרת');
  }

  async function embedLocalImages(container) {
    const images = $$('img', container);
    await Promise.all(images.map(async image => {
      const raw = image.getAttribute('src');
      if (!raw || raw.startsWith('data:')) return;
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 5000);
      try {
        const response = await fetch(new URL(raw, location.href), {signal:controller.signal});
        if (!response.ok) return;
        const blob = await response.blob();
        const dataUrl = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result);
          reader.onerror = reject;
          reader.readAsDataURL(blob);
        });
        image.setAttribute('src', dataUrl);
      } catch (_) {}
      finally { clearTimeout(timer); }
    }));
  }

  async function exportTripHtml(card) {
    const data = routeData(card);
    const clone = $('.route-body', card).cloneNode(true);
    $$('.route-actions,.copy-copy,.load-map,.map-slot,button,canvas,script', clone).forEach(node => node.remove());
    $$('[hidden]', clone).forEach(node => node.removeAttribute('hidden'));
    $$('a[href]', clone).forEach(link => link.setAttribute('href', new URL(link.getAttribute('href'), location.href).href));
    await embedLocalImages(clone);
    const mapFrame = data.trackId ? `<section class="map"><h2>מפת Off‑Road</h2><p><a href="${escapeHtml(data.primaryMap)}">פתיחת המסלול ב־Off‑Road</a></p><iframe title="מפת Off‑Road — ${escapeHtml(data.title)}" loading="lazy" src="https://off-road.io/_v2/track/${data.trackId}?embedded=true"></iframe></section>` : '<section class="notice"><h2>ניווט</h2><p>לכרטיס זה אין קישור ניווט מאומת. המוביל חייב להשלים ולאמת ניווט לפני יציאה.</p></section>';
    const html = `<!doctype html>
<html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive,nosnippet"><title>${escapeHtml(data.title)} · גרסת מסמך ${DOC_VERSION}</title>
<style>:root{color-scheme:light;--ink:#21312b;--forest:#285d45;--clay:#c76a42;--paper:#f7f2e9;--surface:#fffdf8;--line:#d9d0c1}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:Arial,sans-serif;line-height:1.65}.page{max-width:980px;margin:auto;padding:24px}.hero{background:linear-gradient(125deg,#192d25,#3d6b52);color:#fff;border-radius:22px;padding:24px;margin-bottom:18px}.hero h1{margin:.2em 0;font-size:clamp(2rem,6vw,3.7rem)}.version{color:#f4cf9d;font-weight:800}.route-body>*,.map,.notice{background:var(--surface);border:1px solid var(--line);border-radius:15px;padding:15px;margin:12px 0}.route-photo{padding:0;background:transparent;border:0}.route-photo img{width:100%;max-height:480px;object-fit:cover;border-radius:16px}.route-photo figcaption{color:#66736d;font-size:.82rem}.meta{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.meta div{background:#f5eee3;border:1px solid var(--line);border-radius:10px;padding:9px}.meta small{display:block;color:var(--forest);font-weight:800}.marketing{border-right:6px solid var(--clay)!important}.warning,.notice{border-right:6px solid #a33c3c}.nav-block{border-right:6px solid var(--forest)}.qr{width:130px;height:130px;background:#fff}.map iframe{width:100%;height:620px;border:0;border-radius:12px}.footer{margin-top:20px;border-top:1px solid var(--line);padding-top:14px;color:#66736d}@media(max-width:650px){.page{padding:12px}.meta{grid-template-columns:1fr 1fr}.map iframe{height:480px}}@media print{body{background:#fff}.page{max-width:none}.map iframe{display:none}}</style></head>
<body><main class="page"><header class="hero"><div class="version">גרסת מוצר ${PRODUCT_VERSION} · גרסת מסמך ${DOC_VERSION}</div><h1>${escapeHtml(data.title)}</h1><p>${escapeHtml(data.region)} · ${escapeHtml(data.difficultySource)} · ${escapeHtml(data.distanceDuration)}</p></header>${clone.innerHTML}${mapFrame}<section class="notice"><h2>אחריות ובטיחות</h2><p>מסמך זה מרכז מידע קיים ואינו אישור שהמסלול פתוח, חוקי, עביר, בטוח או מתאים לקבוצה. המוביל והקבוצה חייבים לבדוק סמוך ליציאה מזג אוויר, שיטפונות, שטחי אש, ביטחון, שמורות, שערים, מצב השטח ורמת הרוכבים. קושי הוא סובייקטיבי.</p></section><footer class="footer"><b>כרטיס טיול עצמאי · גרסת מסמך ${DOC_VERSION}</b><p>מקור הכרטיס בספר: <a href="${escapeHtml(data.cardUrl)}">${escapeHtml(data.cardUrl)}</a></p></footer></main></body></html>`;
    const blob = new Blob(['\ufeff', html], {type:'text/html;charset=utf-8'});
    downloadBlob(blob, `${safeFileName(data.title)}_גרסת_מסמך_${DOC_VERSION}.html`);
    showToast('קובץ ה־HTML המלא הורד');
  }

  document.addEventListener('click', event => {
    const mapButton = event.target.closest('.load-map');
    if (mapButton) {
      const slot = mapButton.closest('.nav-block').querySelector('.map-slot');
      if (!slot.querySelector('iframe')) {
        const iframe = document.createElement('iframe');
        iframe.loading = 'lazy';
        iframe.referrerPolicy = 'no-referrer-when-downgrade';
        iframe.title = 'מפת Off‑Road מדויקת';
        iframe.src = `https://off-road.io/_v2/track/${mapButton.dataset.track}?embedded=true`;
        slot.appendChild(iframe);
        mapButton.textContent = 'המפה נטענה';
        mapButton.disabled = true;
      }
      return;
    }
    const card = event.target.closest('.route-card');
    if (!card) return;
    if (event.target.closest('.open-invite')) showInvite(card);
    if (event.target.closest('.ai-action')) showAi(card);
    if (event.target.closest('.voice-action')) {
      if (speechSynthesis.speaking) { speechSynthesis.cancel(); showToast('ההקראה נעצרה'); }
      else speakCard(card);
    }
    if (event.target.closest('.copy-link')) copyText(`${location.href.split('#')[0]}#${card.id}`, 'קישור הכרטיס הועתק');
    if (event.target.closest('.export-html')) exportTripHtml(card).catch(error => { console.error(error); showToast('ייצוא ה־HTML נכשל'); });
  });

  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    deferredInstallPrompt = event;
    $('#installButton').dataset.ready = '1';
  });
  $('#installButton').addEventListener('click', async () => {
    if (deferredInstallPrompt) {
      deferredInstallPrompt.prompt();
      await deferredInstallPrompt.userChoice;
      deferredInstallPrompt = null;
    } else openModal($('#installHelp'));
  });
  window.addEventListener('appinstalled', () => {
    $('#installButton').textContent = 'האפליקציה הותקנה';
    showToast('האפליקציה הותקנה');
  });
  if ('serviceWorker' in navigator) window.addEventListener('load', async () => {
    try {
      await navigator.serviceWorker.register('./sw.js');
      $('#pwaStatus').textContent = 'Service Worker פעיל';
    } catch (error) {
      $('#pwaStatus').textContent = 'Service Worker לא הופעל';
      console.error(error);
    }
  });

  if (location.hash) {
    const target = document.getElementById(location.hash.slice(1));
    if (target?.matches('.route-card')) {
      target.open = true;
      setTimeout(() => target.scrollIntoView({block:'start'}), 120);
    }
  }
  document.documentElement.dataset.js = 'ready';
  console.info(`Adventure Route Guide product ${PRODUCT_VERSION}, document ${DOC_VERSION}, ${cards.length} cards`);
})();
