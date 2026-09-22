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
 * On a big library - a hundred tutorials or more - expect several minutes.
 * Lessons are fetched three at a time, which is enough to slow the site down,
 * so some will time out; anything that does is tried again at the end with
 * the browser to itself, which is usually all it needed. Only what is still
 * missing after that second pass is reported as missed.
 *
 * Scroll to the bottom of the page first. Only the tutorials the page has
 * actually drawn are collected, and these sites add more as you scroll.
 *
 * Lessons are named Section.Lesson_Title, numbered by the order they appear
 * on the page, so they land in the folder in course order. A handout keeps
 * its lesson's number too, so it sorts beside the video it belongs to.
 *
 * Nothing is downloaded here and nothing is changed on the site - it only
 * reads addresses the browser already has.
 */
(async () => {
  const camel = s => (s.match(/[A-Za-z0-9]+/g) || [])
    .map(w => w[0].toUpperCase() + w.slice(1)).join('');

  // The player is usually an iframe by the time the page settles, but some
  // pages only insert it when it scrolls into view. The address is in the
  // markup either way, so that is worth a look before giving up on one.
  //
  // Not every post on one of these sites is a Vimeo post either. A library
  // built over years collects the odd YouTube or Wistia embed, and yt-dlp
  // handles those just as well - so take whatever player is there rather
  // than reporting a tutorial as missing because it is on the wrong host.
  const PLAYERS = [
    ['vimeo', /https?:\/\/player\.vimeo\.com\/video\/\d+/],
    ['youtube', /https?:\/\/www\.youtube(?:-nocookie)?\.com\/embed\/[\w-]+/],
    ['wistia', /https?:\/\/fast\.wistia\.net\/embed\/iframe\/\w+/],
    ['loom', /https?:\/\/www\.loom\.com\/embed\/\w+/],
  ];
  const PLAYER_FRAME = 'iframe[src*="vimeo"],iframe[src*="youtube"],'
    + 'iframe[src*="wistia"],iframe[src*="loom.com"]';

  const playerIn = (doc, deep) => {
    const frame = doc.querySelector(PLAYER_FRAME);
    if (frame && frame.src) return frame.src.split('?')[0];
    if (!deep) return null;
    // one read of the whole page, on the way out, for a player that was
    // never inserted because nobody scrolled to it
    const html = doc.documentElement ? doc.documentElement.innerHTML : '';
    for (const [, pattern] of PLAYERS) {
      const match = html.match(pattern);
      if (match) return match[0];
    }
    return null;
  };

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
    const here = document.querySelector(PLAYER_FRAME);
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
  //
  // The timeout is the thing that decides how many come back MISSED. Three
  // full pages at a time is enough to slow the site down, and on a library of
  // a hundred or more the slow ones are simply the ones that happened to load
  // while the browser was busiest - nothing is wrong with them. So: poll
  // often, to hand a slot back the moment a page is ready rather than on the
  // next whole second, and give whatever still timed out a second pass at the
  // end, when there is no longer a queue behind it.
  const POLL = 350;             // ms between looks at a loading page
  const PATIENCE = 22000;       // ms to give one lesson on the first pass
  // Every hidden frame is a whole copy of the site's app, running in the same
  // renderer as the page you are watching. Three at a time is fine for a
  // course; on a library of a hundred and more it is enough to lock the tab
  // up, and a tab that cannot keep up is what produces a page of MISSED.
  const AT_ONCE = lessons.length > 60 ? 2 : 3;
  const STAGGER = 700;          // ms between starting one frame and the next

  const readLesson = (href, patience) => new Promise(resolve => {
    const frame = document.createElement('iframe');
    // big enough for a player to decide it is visible, no bigger: every
    // pixel of it is laid out for real
    frame.style.cssText = 'position:fixed;left:-9999px;top:0;width:900px;height:600px;border:0';
    frame.src = href;
    document.body.appendChild(frame);
    const deadline = Date.now() + (patience || PATIENCE);
    const timer = setInterval(() => {
      const last = Date.now() >= deadline;
      let url = null, doc = null, loaded = false;
      try {
        doc = frame.contentDocument;
        url = doc ? playerIn(doc, last) : null;
        // Only worth asking on the way out, and worth asking carefully: these
        // pages put a root element in place long before they render anything
        // into it, so "has a body" says nothing. A finished page with real
        // text on it and no player genuinely has no video; anything less than
        // that is a page that ran out of time, and those are worth retrying.
        if (last && !url) {
          loaded = doc && doc.readyState === 'complete' && doc.body
                   && (doc.body.innerText || '').trim().length > 400;
        }
        // a player that waits to be scrolled to will not load in a frame
        // nobody is looking at, so nudge it
        if (!url && doc && frame.contentWindow) frame.contentWindow.scrollTo(0, 600);
      } catch (e) {
        clearInterval(timer); frame.remove();
        resolve({ url: null, files: [], why: 'the site would not let it be read' });
        return;
      }
      if (url || last) {
        // the handouts sit in the same page, so read them before it goes
        let files = [];
        try { files = doc ? filesIn(doc) : []; } catch (e) { files = []; }
        clearInterval(timer); frame.remove();
        // say which it was: a page that never arrived is worth trying again,
        // a page with no player on it never will be
        resolve({ url, files,
                  why: url ? '' : (loaded ? 'no player on the page'
                                          : 'the page did not finish loading') });
      }
    }, POLL);
  });

  const found = [];
  window.evdProgress = { done: 0, of: lessons.length };
  const queue = lessons.slice();
  const wait = ms => new Promise(res => setTimeout(res, ms));
  const workers = Array.from({ length: Math.min(AT_ONCE, queue.length) }, async (_x, n) => {
    await wait(n * STAGGER);     // do not boot them all in the same instant
    while (queue.length) {
      const l = queue.shift();
      // a single page already has its video; everything else is fetched
      const got = l.url ? { url: l.url, files: l.files || [] } : await readLesson(l.href);
      window.evdProgress.done++;
      console.log('[evd] %s/%s  %s %s %s%s', window.evdProgress.done, lessons.length,
                  l.number, l.title.slice(0, 40),
                  got.url ? 'ok' : 'MISSED - ' + got.why,
                  got.files.length ? ' +' + got.files.length + ' file(s)' : '');
      found.push(Object.assign({}, l, got));
    }
  });
  await Promise.all(workers);

  // Second pass. Whatever timed out gets another go with the browser to
  // itself and twice the patience, which is usually all those pages needed.
  // Only what looked like a timeout is worth another go. A post that
  // loaded and simply has no video on it - a written tutorial, a gallery -
  // will be no different the second time.
  const retry = found.filter(f => !f.url && f.href && f.why !== 'no player on the page');
  if (retry.length) {
    console.log('[evd] %d timed out - trying those again, two at a time', retry.length);
    const again = retry.slice();
    await Promise.all(Array.from({ length: Math.min(2, again.length) }, async () => {
      while (again.length) {
        const l = again.shift();
        const got = await readLesson(l.href, PATIENCE * 2);
        if (got.url) {
          l.url = got.url;
          if (!l.files || !l.files.length) l.files = got.files;
        } else {
          l.why = got.why;
        }
        console.log('[evd] retry  %s %s %s', l.number, l.title.slice(0, 40),
                    got.url ? 'ok' : 'STILL MISSED - ' + got.why);
      }
    }));
  }
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
  // Say why, not just which. A post with no video on it is nothing to chase;
  // a page that would not load is worth another run.
  const gone = found.filter(f => !f.url);
  const byReason = {};
  for (const f of gone) (byReason[f.why || 'no video found'] ||= []).push(f.number);
  const missed = Object.entries(byReason)
    .map(([why, nums]) => nums.join(', ') + ' (' + why + ')').join('; ');

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
    + (missed ? ' <b style="color:#ffb4b4">Not collected: ' + missed + '</b>'
              : '')
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
