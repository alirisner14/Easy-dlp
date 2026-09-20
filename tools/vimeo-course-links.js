/*
 * Collect every lesson's video link from a course that embeds Vimeo.
 *
 * These sites list their lesson addresses on the course page, but each
 * lesson's Vimeo id is only put into its page by scripts after it loads -
 * so fetching those pages in the background returns nothing useful, and
 * pasting the course page source finds nothing either.
 *
 * The way through is to let the browser do the work: each lesson is loaded
 * in a hidden frame, which runs its scripts as normal, and the Vimeo address
 * is read straight out of it. The site's own session is used, so nothing
 * needs signing in again. It ends with a panel you can copy from, in the
 * "url | file name" form that Easy Video Downloader's Paste button reads.
 *
 * To use it:
 *   1. open the course page - the one listing the lessons - while signed in
 *   2. F12, the Console tab
 *   3. paste this whole file, press Enter
 *      (the first time, Chrome makes you type "allow pasting" first)
 *   4. wait a few seconds a lesson, then Copy and Paste into the downloader
 *
 * Lessons are named Section.Lesson_Title, numbered by the order they appear
 * on the page, so they land in the folder in course order.
 *
 * Nothing is downloaded here and nothing is changed on the site - it only
 * reads addresses the browser already has.
 */
(async () => {
  const VIMEO = 'iframe[src*="vimeo"]';
  const camel = s => (s.match(/[A-Za-z0-9]+/g) || [])
    .map(w => w[0].toUpperCase() + w.slice(1)).join('');

  // every lesson link on the page, kept in the order they are listed, with
  // the section they sit under so the numbering matches the course
  const lessons = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/lessons/"]')) {
    const href = a.getAttribute('href') || '';
    if (!/\/lessons\/\d+/.test(href) || seen.has(href)) continue;
    seen.add(href);
    const section = (href.match(/\/sections\/(\d+)/) || [])[1] || '0';
    const title = (a.textContent || '').replace(/\s+/g, ' ').trim()
      .replace(/\b\d{1,2}:\d{2}\b/g, '').trim();
    lessons.push({ href, section, title: title || 'Lesson' });
  }
  if (!lessons.length) {
    alert('No lessons found. Open the course page that lists the lessons.');
    return;
  }

  const sections = [];
  for (const l of lessons) if (!sections.includes(l.section)) sections.push(l.section);
  const counters = {};
  for (const l of lessons) {
    const s = sections.indexOf(l.section) + 1;
    counters[s] = (counters[s] || 0) + 1;
    l.number = s + '.' + String(counters[s]).padStart(2, '0');
  }
  console.log('[evd] %d lessons across %d sections', lessons.length, sections.length);

  // load each lesson out of sight and read the player address from it
  const readLesson = href => new Promise(resolve => {
    const frame = document.createElement('iframe');
    frame.style.cssText = 'position:fixed;left:-9999px;top:0;width:1280px;height:800px;border:0';
    frame.src = href;
    document.body.appendChild(frame);
    let tries = 0;
    const timer = setInterval(() => {
      tries++;
      let url = null;
      try {
        const doc = frame.contentDocument;
        const player = doc && doc.querySelector(VIMEO);
        if (player) url = (player.src || '').split('?')[0];
      } catch (e) {
        clearInterval(timer); frame.remove(); resolve(null); return;
      }
      if (url || tries >= 25) {           // 25 seconds is generous
        clearInterval(timer); frame.remove(); resolve(url);
      }
    }, 1000);
  });

  const found = [];
  for (const l of lessons) {
    const url = await readLesson(l.href);
    console.log('[evd] %s %s %s', l.number, l.title.slice(0, 40), url ? 'ok' : 'MISSED');
    found.push(Object.assign({ url }, l));
  }

  const lines = found.filter(f => f.url)
    .map(f => f.url + ' | ' + f.number + '_' + camel(f.title));
  const missed = found.filter(f => !f.url).map(f => f.number).join(', ');

  document.getElementById('evd-box')?.remove();
  const wrap = document.createElement('div');
  wrap.id = 'evd-box';
  wrap.style.cssText = 'position:fixed;inset:5% 8%;z-index:2147483647;background:#0e1020;'
    + 'color:#e8ecff;border:2px solid #6c7cff;border-radius:14px;padding:16px;'
    + 'font:13px system-ui;display:flex;flex-direction:column;gap:10px;'
    + 'box-shadow:0 20px 60px rgba(0,0,0,.6)';
  wrap.innerHTML = '<div style="font-size:16px;font-weight:600">'
    + lines.length + ' of ' + lessons.length + ' lesson links</div>'
    + '<div style="opacity:.8">Copy, then press Paste in Easy Video Downloader.'
    + (missed ? ' <b style="color:#ffb4b4">Missed: ' + missed + '</b> - run it again.' : '')
    + '</div>';

  const box = document.createElement('textarea');
  box.value = lines.join('\n');
  box.style.cssText = 'flex:1;width:100%;background:#05060f;color:#9fe8b0;'
    + 'border:1px solid #2a2f52;border-radius:8px;padding:10px;'
    + 'font:11px ui-monospace,Consolas,monospace;white-space:pre;overflow:auto';

  const copy = document.createElement('button');
  copy.textContent = 'Copy to clipboard';
  copy.style.cssText = 'align-self:flex-start;background:#6c7cff;color:#fff;border:0;'
    + 'border-radius:8px;padding:9px 16px;font:600 13px system-ui;cursor:pointer';
  copy.onclick = () => {
    box.focus(); box.select(); document.execCommand('copy'); copy.textContent = 'Copied';
  };

  const close = document.createElement('button');
  close.textContent = 'Close';
  close.style.cssText = 'position:absolute;top:10px;right:12px;background:transparent;'
    + 'color:#8b93c7;border:0;font:13px system-ui;cursor:pointer';
  close.onclick = () => wrap.remove();

  wrap.append(box, copy, close);
  document.body.appendChild(wrap);
})();
