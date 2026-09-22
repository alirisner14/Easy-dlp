/*
 * Collect every lesson's video link from a course that embeds Vimeo, along
 * with the handouts that come with it.
 *
 * These sites list their lesson addresses on the course page, but each
 * lesson's Vimeo id is only put into its page by scripts after it loads -
 * so fetching those pages in the background returns nothing useful, and
 * pasting the course page source finds nothing either.
 *
 * The way through is to let the browser do the work: each lesson is loaded
 * in a hidden frame, which runs its scripts as normal, and the Vimeo address
 * is read straight out of it. The site's own session is used, so nothing
 * needs signing in again. While the frame is open, any worksheet or project
 * file the lesson attaches is picked up too. It ends with a panel you can
 * copy from, in the "url | file name" form that Easy-dlp's Paste button
 * reads.
 *
 * To use it:
 *   1. open the course page - the one listing the lessons - while signed in
 *   2. F12, the Console tab
 *   3. paste this whole file, press Enter
 *      (the first time, Chrome makes you type "allow pasting" first)
 *   4. wait a few seconds a lesson, then Copy and Paste into the downloader
 *
 * Lessons are named Section.Lesson_Title, numbered by the order they appear
 * on the page, so they land in the folder in course order. A handout keeps
 * its lesson's number too, so it sorts beside the video it belongs to.
 *
 * Nothing is downloaded here and nothing is changed on the site - it only
 * reads addresses the browser already has.
 */
(async () => {
  const VIMEO = 'iframe[src*="vimeo"]';
  const camel = s => (s.match(/[A-Za-z0-9]+/g) || [])
    .map(w => w[0].toUpperCase() + w.slice(1)).join('');

  // -- handouts ------------------------------------------------------------
  // A link ending .pdf or .zip is the worksheet it looks like. A link ending
  // .png is as likely to be the site's logo, so an image comes along only
  // when the page says outright that it is meant to be saved.
  const FILE_EXT = new RegExp(
    '\\.(pdf|zip|rar|7z|psd|psb|ai|eps|clip|procreate|brushset|brush|abr|atn'
    + '|tpl|blend|obj|fbx|doc|docx|rtf|xls|xlsx|csv|ppt|pptx|key|epub|mobi'
    + '|otf|ttf)$', 'i');
  const IMAGE_EXT = /\.(png|jpe?g|gif|webp|tiff?|svg|txt)$/i;
  const SAYS = /download|worksheet|handout|attachment|resource|material|template/i;
  const ONLY = /^\s*(download|get|save)( it| file| now)?\s*$/i;
  const takenFiles = new Set();

  const filesIn = doc => {
    const out = [];
    for (const a of doc.querySelectorAll('a[href]')) {
      const url = a.href;                       // already absolute
      if (!/^https?:/i.test(url) || takenFiles.has(url)) continue;
      const label = ((a.textContent || '') + ' '
                     + (a.getAttribute('aria-label') || '')).replace(/\s+/g, ' ').trim();
      const attr = a.getAttribute('download');
      let ext = (url.split('?')[0].split('#')[0].match(/\.([A-Za-z0-9]{1,10})$/) || [])[1];
      if (attr) ext = (attr.match(/\.([A-Za-z0-9]{1,10})$/) || [])[1] || ext;
      if (!ext) continue;
      const dotted = '.' + ext;
      if (!(FILE_EXT.test(dotted)
            || (IMAGE_EXT.test(dotted) && (attr !== null || SAYS.test(label))))) continue;
      takenFiles.add(url);
      // the link's own words name it; a button reading only "Download" does not
      let name = ONLY.test(label) ? '' : label;
      if (!name && attr) name = attr.replace(/\.[^.]+$/, '');
      if (!name) {
        name = decodeURIComponent(url.split('?')[0].split('#')[0].split('/').pop() || '')
          .replace(/\.[^.]+$/, '');
      }
      out.push({ url: url, name: camel(name) || 'Resource', ext: ext.toLowerCase() });
    }
    return out;
  };

  // -- the lesson list -----------------------------------------------------
  // These sites lay a course out in more than one way. A structured course
  // numbers its lessons under sections; a library of tutorials is a list of
  // posts with no numbering at all; and a tutorial can simply be a page of
  // its own with the video on it. All three are worth handling, because the
  // links come out the same either way.
  const LESSON = /\/lessons\/\d+/;                 // a course lesson
  const POST = /^\/c\/[A-Za-z0-9-]+\/[A-Za-z0-9-]+/;   // a tutorial post

  const lessons = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href]')) {
    const href = a.getAttribute('href') || '';
    const isLesson = LESSON.test(href);
    const isPost = POST.test(href) && !LESSON.test(href);
    if ((!isLesson && !isPost) || seen.has(href)) continue;
    seen.add(href);
    const section = (href.match(/\/sections\/(\d+)/) || [])[1] || '';
    let title = (a.textContent || '').replace(/\s+/g, ' ').trim()
      .replace(/\b\d{1,2}:\d{2}\b/g, '').trim();
    if (!title) title = decodeURIComponent(href.split('/').pop() || '').replace(/-/g, ' ');
    lessons.push({ href, section, title: title || 'Lesson' });
  }

  // a single tutorial page: the video is right here, so there is nothing
  // to walk
  if (!lessons.length) {
    const here = document.querySelector(VIMEO);
    if (here) {
      const name = (document.title || 'Video').split('|')[0].split('–')[0].trim();
      lessons.push({ href: null, section: '', title: name,
                     url: (here.src || '').split('?')[0], files: filesIn(document) });
    } else {
      alert('Nothing found. Open a course page listing its lessons, a library '
          + 'of tutorials, or a single tutorial page with the video on it.');
      return;
    }
  }

  // Numbered by section where the site numbers them, otherwise straight
  // through: a library of tutorials has no chapters to follow.
  const sections = [];
  for (const l of lessons) if (l.section && !sections.includes(l.section)) sections.push(l.section);
  const counters = {};
  let plain = 0;
  for (const l of lessons) {
    if (l.section) {
      const s = sections.indexOf(l.section) + 1;
      counters[s] = (counters[s] || 0) + 1;
      l.number = s + '.' + String(counters[s]).padStart(2, '0');
    } else {
      plain += 1;
      l.number = String(plain).padStart(2, '0');
    }
  }
  console.log('[evd] %d to fetch%s', lessons.length,
              sections.length ? ' across ' + sections.length + ' sections' : '');

  // Load each lesson out of sight and read the player address from it. A
  // lesson page is heavy, so they are fetched a few at a time rather than one
  // after another - waiting the full timeout on each in turn takes minutes on
  // a course of any size.
  const PATIENCE = 14;        // seconds to give one lesson
  const AT_ONCE = 3;

  const readLesson = href => new Promise(resolve => {
    const frame = document.createElement('iframe');
    frame.style.cssText = 'position:fixed;left:-9999px;top:0;width:1280px;height:800px;border:0';
    frame.src = href;
    document.body.appendChild(frame);
    let tries = 0;
    const timer = setInterval(() => {
      tries++;
      let url = null, doc = null;
      try {
        doc = frame.contentDocument;
        const player = doc && doc.querySelector(VIMEO);
        if (player) url = (player.src || '').split('?')[0];
      } catch (e) {
        clearInterval(timer); frame.remove(); resolve({ url: null, files: [] }); return;
      }
      if (url || tries >= PATIENCE) {
        // the handouts sit in the same page, so read them before it goes
        let files = [];
        try { files = doc ? filesIn(doc) : []; } catch (e) { files = []; }
        clearInterval(timer); frame.remove(); resolve({ url, files });
      }
    }, 1000);
  });

  const found = [];
  window.evdProgress = { done: 0, of: lessons.length };
  const queue = lessons.slice();
  const workers = Array.from({ length: Math.min(AT_ONCE, queue.length) }, async () => {
    while (queue.length) {
      const l = queue.shift();
      // a single page already has its video; everything else is fetched
      const got = l.url ? { url: l.url, files: l.files || [] } : await readLesson(l.href);
      window.evdProgress.done++;
      console.log('[evd] %s/%s  %s %s %s%s', window.evdProgress.done, lessons.length,
                  l.number, l.title.slice(0, 40), got.url ? 'ok' : 'MISSED',
                  got.files.length ? ' +' + got.files.length + ' file(s)' : '');
      found.push(Object.assign({}, l, got));
    }
  });
  await Promise.all(workers);
  found.sort((a, b) => a.number.localeCompare(b.number, undefined, { numeric: true }));

  // Anything the course page itself offers, read last so that whatever the
  // lessons already claimed is not counted twice. A course-wide workbook
  // lives here rather than on any one lesson.
  const courseFiles = filesIn(document);

  const lines = [];
  let fileCount = 0;
  for (const r of courseFiles) {
    lines.push(r.url + ' | 00_' + r.name + '.' + r.ext);
    fileCount++;
  }
  for (const f of found) {
    const stem = f.number + '_' + camel(f.title);
    if (f.url) lines.push(f.url + ' | ' + stem);
    for (const r of (f.files || [])) {
      // a handout keeps its lesson's number, so it sorts beside the video
      lines.push(r.url + ' | ' + stem + '_' + r.name + '.' + r.ext);
      fileCount++;
    }
  }
  const missed = found.filter(f => !f.url).map(f => f.number).join(', ');

  document.getElementById('evd-box')?.remove();
  const wrap = document.createElement('div');
  wrap.id = 'evd-box';
  wrap.style.cssText = 'position:fixed;inset:5% 8%;z-index:2147483647;background:#0e1020;'
    + 'color:#e8ecff;border:2px solid #6c7cff;border-radius:14px;padding:16px;'
    + 'font:13px system-ui;display:flex;flex-direction:column;gap:10px;'
    + 'box-shadow:0 20px 60px rgba(0,0,0,.6)';
  wrap.innerHTML = '<div style="font-size:16px;font-weight:600">'
    + (lines.length - fileCount) + ' of ' + lessons.length + ' lesson links'
    + (fileCount ? ' and ' + fileCount + ' resource' + (fileCount === 1 ? '' : 's') : '')
    + '</div>'
    + '<div style="opacity:.8">Copy, then press Paste in Easy-dlp.'
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
