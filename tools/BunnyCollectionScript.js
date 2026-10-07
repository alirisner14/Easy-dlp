/*
 * Collect every lesson's video link from a Freya course.
 *
 * Freya's video host now signs each address, and a page carries the
 * signature only for the lesson open on it. Pasting one page's source into
 * Easy-dlp therefore unlocks that one lesson; the rest come back "403
 * Forbidden". This reads each lesson's own page in the background - with
 * your signed-in session, so nothing needs signing in again - and takes the
 * signed address out of it.
 *
 * To use it:
 *   1. open the course, or any lesson in it, while signed in
 *   2. F12, the Console tab
 *   3. paste this whole file, press Enter
 *      (the first time, Chrome makes you type "allow pasting" first)
 *   4. Copy, then press Paste in Easy-dlp
 *
 * The signatures run out after a few hours, so download soon after
 * collecting. If a download later fails with 403, run this again.
 *
 * Lessons are named Section.Lesson_Title, the way the course numbers them.
 * Nothing is downloaded here and nothing is changed on the site.
 */
(async () => {
  if (window.evdControl && window.evdControl.running) {
    alert('Already collecting on this page. Press Stop on the bar in the corner first.');
    return;
  }
  const camel = s => (s.match(/[A-Za-z0-9]+/g) || [])
    .map(w => w[0].toUpperCase() + w.slice(1)).join('');
  const GUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
  const LESSON = /^\/courses\/[^/]+\/lessons\/[0-9a-f-]{36}$/i;
  const SIGNED = /https:\/\/[A-Za-z0-9.-]*b-cdn\.net\/bcdn_token=[^"'\s\/]*\/([0-9a-f-]{36})\/playlist\.m3u8/gi;
  const NUMBER = /\b(\d{1,2})\.(\d{1,2})\b(?!\d)/;
  const META = /^(?:Lesson|\d{1,2}\.\d{1,2}|\d{1,2}:\d{2}(?::\d{2})?|[^\w])+$/i;
  const wait = ms => new Promise(res => setTimeout(res, ms));
  const bare = h => h.split('#')[0].split('?')[0].replace(/\/+$/, '');

  // -- the lesson list, from the links on this page --------------------------
  const lessons = [];
  const seen = new Set();
  const add = (href, card) => {
    if (seen.has(href)) return;
    seen.add(href);
    const paras = card ? [...card.querySelectorAll('p')]
      .map(p => (p.textContent || '').replace(/\s+/g, ' ').trim()).filter(Boolean) : [];
    const title = paras.find(p => !META.test(p)) || '';
    const num = ((card ? card.textContent : '') || '').match(NUMBER);
    const img = card && card.querySelector('img[src*="b-cdn.net"]');
    lessons.push({
      href, title,
      number: num ? num[1] + '.' + num[2].padStart(2, '0') : '',
      guid: img ? ((img.getAttribute('src') || '').match(GUID) || [''])[0].toLowerCase() : '',
    });
  };
  for (const a of document.querySelectorAll('a[href]')) {
    const href = bare(new URL(a.getAttribute('href'), location.href).pathname);
    if (LESSON.test(href)) add(href, a);
  }
  // the lesson open now is not always linked from its own sidebar
  const here = bare(location.pathname);
  if (LESSON.test(here)) add(here, null);
  if (!lessons.length) {
    alert('No lessons found. Open a Freya course, or a lesson in it, while signed in.');
    return;
  }

  // -- the bar: progress and Stop --------------------------------------------
  const control = { running: true, stopped: false };
  window.evdControl = control;
  window.evdStop = () => { control.stopped = true; return 'stopping'; };
  const bar = document.createElement('div');
  bar.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:2147483647;'
    + 'background:#0e1020;color:#e8ecff;border:2px solid #6c7cff;border-radius:12px;'
    + 'padding:10px 12px;font:13px system-ui;display:flex;gap:10px;align-items:center';
  const barText = document.createElement('span');
  const stopBtn = document.createElement('button');
  stopBtn.textContent = 'Stop';
  stopBtn.style.cssText = 'border:0;border-radius:8px;padding:7px 12px;cursor:pointer;'
    + 'font:600 12px system-ui;color:#fff;background:#b3424a';
  stopBtn.onclick = () => window.evdStop();
  bar.append(barText, stopBtn);
  document.body.appendChild(bar);

  // -- read each lesson's page for its signed address --------------------------
  const flatten = t => t.replace(/\\"/g, '"').replace(/\\\//g, '/')
    .replace(/\\u0026/g, '&').replace(/&amp;/g, '&');
  let done = 0;
  for (const l of lessons) {
    if (control.stopped) { l.why = 'not reached'; continue; }
    barText.textContent = 'Reading lesson ' + (++done) + ' of ' + lessons.length;
    try {
      const res = await fetch(l.href, { credentials: 'include' });
      if (!res.ok) throw new Error('the site answered ' + res.status);
      const page = flatten(await res.text());
      const found = [...page.matchAll(SIGNED)];
      // a page signs only its own lesson, but match the thumbnail when we can
      const pick = found.find(m => m[1].toLowerCase() === l.guid) || found[0];
      if (pick) {
        l.url = pick[0];
        if (!l.title) {
          const doc = new DOMParser().parseFromString(page, 'text/html');
          const h = doc.querySelector('h1');
          l.title = h ? h.textContent.trim() : (doc.title || '').split('|')[0].trim();
        }
      } else {
        l.why = 'no video on the page';
      }
    } catch (e) {
      l.why = e.message || 'could not be read';
    }
    console.log('[evd] %s %s %s', l.number, l.title.slice(0, 40), l.url ? 'ok' : 'MISSED - ' + l.why);
    await wait(300);   // be gentle with the site
  }
  bar.remove();
  control.running = false;

  // -- the panel ---------------------------------------------------------------
  const ordered = lessons.slice().sort(
    (a, b) => (a.number || '99').localeCompare(b.number || '99', undefined, { numeric: true }));
  const lines = [];
  const urls = new Set();
  for (const l of ordered) {
    if (!l.url || urls.has(l.url)) continue;
    urls.add(l.url);
    lines.push(l.url + ' | ' + (l.number ? l.number + '_' : '') + (camel(l.title) || 'Lesson'));
  }
  const missed = ordered.filter(l => !l.url);

  document.getElementById('evd-box')?.remove();
  const panel = document.createElement('div');
  panel.id = 'evd-box';
  panel.style.cssText = 'position:fixed;inset:5% 8% 76px 8%;z-index:2147483646;background:#0e1020;'
    + 'color:#e8ecff;border:2px solid #6c7cff;border-radius:14px;padding:16px;'
    + 'font:13px system-ui;display:flex;flex-direction:column;gap:10px';
  const heading = document.createElement('div');
  heading.innerHTML = '<div style="font-size:16px;font-weight:600">' + lines.length
    + ' of ' + lessons.length + ' lesson links</div>'
    + '<div style="opacity:.8">Copy, then press Paste in Easy-dlp. These links stop '
    + 'working after a few hours, so download soon.'
    + (missed.length ? ' <b style="color:#ffb4b4">Not collected: '
       + missed.map(l => (l.number || l.title) + ' (' + l.why + ')').join(', ') + '</b>' : '')
    + '</div>';
  const box = document.createElement('textarea');
  box.value = lines.join(String.fromCharCode(10));
  box.style.cssText = 'flex:1;width:100%;background:#05060f;color:#9fe8b0;'
    + 'border:1px solid #2a2f52;border-radius:8px;padding:10px;'
    + 'font:11px ui-monospace,Consolas,monospace;white-space:pre;overflow:auto';
  const copy = document.createElement('button');
  copy.textContent = 'Copy to clipboard';
  copy.style.cssText = 'align-self:flex-start;border:0;border-radius:8px;padding:9px 16px;'
    + 'cursor:pointer;font:600 13px system-ui;background:#6c7cff;color:#fff';
  copy.onclick = () => {
    box.focus(); box.select(); document.execCommand('copy');
    copy.textContent = 'Copied';
  };
  const close = document.createElement('button');
  close.textContent = 'Close';
  close.style.cssText = 'position:absolute;top:10px;right:12px;border:0;background:transparent;'
    + 'color:#8b93c7;cursor:pointer;font:13px system-ui';
  close.onclick = () => panel.remove();
  panel.append(heading, box, copy, close);
  document.body.appendChild(panel);
})();
