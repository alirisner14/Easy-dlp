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
 * Pages are fetched two or three at a time with a pause between, because
 * asking for a hundred back to back gets the run throttled part way through:
 * the start and the end come back fine and the middle comes back empty.
 * Anything that still does not answer is tried again at the end, slower, and
 * whatever is left after that is listed in the panel with a button to try
 * those few again - which beats fetching all hundred a second time.
 *
 * The panel says why each one was left out. "did not finish loading" is worth
 * another try; "no player on the page" is a written post with no video on it,
 * and will say the same next time.
 *
 * While it runs, a small bar sits bottom-right with a running count, Pause
 * and Stop. Stop keeps everything found so far and opens the links panel at
 * once - for a run started on the wrong page, or one plainly missing
 * everything - and the panel then offers to carry on from where it stopped.
 * The same controls work from the console: evdPause(), evdResume(),
 * evdStop().
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
  // Stamped on the bar and in the console, so an old copy saved in DevTools
  // is easy to tell from the current one.
  const EVD_SCRIPT = 'VimeoCollectionScript 1.4.1';
  console.log('[evd] ' + EVD_SCRIPT);
  // Some sites lay a full-screen layer over the page that no z-index beats.
  // The browser's top layer does, so the bar and panel go there when they can.
  const lift = el => {
    try { el.popover = 'manual'; el.showPopover(); } catch (e) { /* older browser */ }
  };
  // Running it twice at once would double the load on the site and tangle
  // the two runs' results together.
  if (window.evdControl && window.evdControl.running) {
    alert('Already collecting on this page. Press Stop on the bar in the corner '
        + '(or type evdStop() in the console) first.');
    return;
  }
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
  // The page being read, as a bare path, so links back to it can be told
  // apart from links to other lessons.
  const bare = h => h.split('#')[0].split('?')[0].replace(/\/+$/, '');
  const here = bare(location.pathname);
  // Run on a single tutorial post that has its video, the wanted video is
  // that one - not every post its sidebar and comments happen to link to.
  // (A course *lesson* page is different: its sidebar is the course, and
  // collecting that is the point.)
  const onPost = POST.test(here) && !LESSON.test(here)
                 && !!document.querySelector(PLAYER_FRAME);
  for (const a of (onPost ? [] : document.querySelectorAll('a[href]'))) {
    const raw = a.getAttribute('href') || '';
    // Compared and fetched without the #fragment or ?query. A post's comment
    // timestamps ("Jan 8, 2023") are links back to that same post with a
    // #comment on the end; taken one by one they made a run fetch the same
    // video seventeen times under seventeen dates.
    const href = bare(raw.startsWith('http') ? new URL(raw).pathname : raw);
    const isLesson = LESSON.test(href);
    const isPost = POST.test(href) && !LESSON.test(href);
    if ((!isLesson && !isPost) || seen.has(href) || href === here) continue;
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
  // A pause between one page and the next. A library fetched back to back
  // gets throttled part way through - the run comes back with the start and
  // the end intact and the middle empty, a success every fifth or sixth - and
  // the cure for that is to ask less often, not to wait longer for an answer
  // that was never coming.
  const BREATH = 400;
  const wait = ms => new Promise(res => setTimeout(res, ms));

  // -- stop and pause -------------------------------------------------------
  // A run over a big library takes many minutes, and started on the wrong
  // page - or once it is plainly missing everything - waiting for it to try
  // every link is the worst way to find out. So a small bar sits in the
  // corner while it works: Pause, Stop, and a running count. Stop keeps what
  // has been found so far and opens the links panel at once. The same three
  // are console commands too, for when the bar is out of reach:
  //   evdPause()   evdResume()   evdStop()
  const control = { running: true, paused: false, stopped: false };
  window.evdControl = control;

  const bar = document.createElement('div');
  bar.id = 'evd-bar';
  bar.style.cssText = 'position:fixed;inset:auto;right:16px;bottom:16px;margin:0;z-index:2147483647;'
    + 'background:#0e1020;color:#e8ecff;border:2px solid #6c7cff;border-radius:12px;'
    + 'padding:10px 12px;font:13px system-ui;display:flex;gap:10px;align-items:center;'
    + 'box-shadow:0 10px 30px rgba(0,0,0,.5)';
  const barText = document.createElement('span');
  barText.style.cssText = 'min-width:190px';
  const barBtn = (text, bg) => {
    const b = document.createElement('button');
    b.textContent = text;
    b.style.cssText = 'border:0;border-radius:8px;padding:7px 12px;cursor:pointer;'
      + 'font:600 12px system-ui;color:#fff;background:' + bg;
    return b;
  };
  const pauseBtn = barBtn('Pause', '#3a4170');
  const stopBtn = barBtn('Stop', '#b3424a');
  bar.append(barText, pauseBtn, stopBtn);

  const tally = { done: 0, of: 0, ok: 0, missed: 0, what: 'Collecting' };
  const showProgress = () => {
    const state = control.stopped ? 'Stopping…'
      : control.paused ? 'Paused at ' + tally.done + ' of ' + tally.of
      : tally.what + ' ' + tally.done + ' of ' + tally.of;
    barText.textContent = state + (tally.done ? '  ·  ' + tally.ok + ' found, '
                                   + tally.missed + ' missed' : '');
    pauseBtn.textContent = control.paused ? 'Resume' : 'Pause';
    pauseBtn.disabled = stopBtn.disabled = control.stopped;
  };
  window.evdPause = () => { if (!control.stopped) control.paused = true; showProgress(); return 'paused'; };
  window.evdResume = () => { control.paused = false; showProgress(); return 'resumed'; };
  window.evdStop = () => {
    control.stopped = true; control.paused = false; showProgress();
    return 'stopping - the links found so far will open in a moment';
  };
  pauseBtn.onclick = () => (control.paused ? window.evdResume() : window.evdPause());
  stopBtn.onclick = () => window.evdStop();

  const startBar = (what, of) => {
    Object.assign(tally, { done: 0, of, ok: 0, missed: 0, what });
    control.running = true; control.paused = false; control.stopped = false;
    document.body.appendChild(bar);
    bar.title = EVD_SCRIPT;
    lift(bar);
    showProgress();
  };
  const endBar = () => { bar.remove(); control.running = false; };

  // Before each lesson: hold while paused, and say whether to go on at all.
  const gate = async () => {
    while (control.paused && !control.stopped) await wait(250);
    return !control.stopped;
  };

  const readLesson = (href, patience) => new Promise(resolve => {
    const frame = document.createElement('iframe');
    // big enough for a player to decide it is visible, no bigger: every
    // pixel of it is laid out for real
    frame.style.cssText = 'position:fixed;left:-9999px;top:0;width:900px;height:600px;border:0';
    frame.src = href;
    document.body.appendChild(frame);
    const deadline = Date.now() + (patience || PATIENCE);
    const timer = setInterval(() => {
      // Stop means now, not once every page already loading has timed out
      if (control.stopped) {
        clearInterval(timer); frame.remove();
        resolve({ url: null, files: [], why: 'not reached' });
        return;
      }
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

  // One pass over a list of lessons, `atOnce` at a time, filling in whatever
  // it can. Used for the first sweep and for every retry after it, so a
  // second attempt behaves exactly like the first, only more patiently.
  const sweep = async (list, atOnce, patience, tag) => {
    const queue = list.slice();
    let done = 0;
    await Promise.all(Array.from({ length: Math.min(atOnce, queue.length) },
      async (_unused, n) => {
        await wait(n * STAGGER);       // do not boot them all in one instant
        while (queue.length) {
          if (!await gate()) break;
          const l = queue.shift();
          const got = l.url ? { url: l.url, files: l.files || [] }
                            : await readLesson(l.href, patience);
          if (got.why === 'not reached') { l.why = 'not reached'; break; }
          done++;
          if (got.url) {
            l.url = got.url;
            if (!l.files || !l.files.length) l.files = got.files;
            l.why = '';
          } else {
            l.why = got.why;
          }
          tally.done++;
          tally[got.url ? 'ok' : 'missed']++;
          showProgress();
          console.log('[evd] %s %s/%s  %s %s %s%s', tag, done, list.length, l.number,
                      l.title.slice(0, 40), got.url ? 'ok' : 'MISSED - ' + got.why,
                      (got.files || []).length ? ' +' + got.files.length + ' file(s)' : '');
          // A beat between pages. A library of a hundred fetched back to back
          // gets throttled part way through - the middle of the run comes back
          // empty while the start and the end are fine - and the cure is to
          // ask less often, not to wait longer for an answer that is not coming.
          if (queue.length && !control.stopped) await wait(BREATH);
        }
      }));
    // whatever a stop left untouched is marked, so the panel can offer to
    // carry on from there instead of starting the whole run again
    if (control.stopped) {
      for (const l of list) if (!l.url && !l.why) l.why = 'not reached';
    }
  };

  // a page that loaded and has no player on it will be no different next time
  const stragglers = () => lessons.filter(
    l => !l.url && l.href && l.why !== 'no player on the page' && l.why !== 'not reached');
  const unreached = () => lessons.filter(l => !l.url && l.href && l.why === 'not reached');

  startBar('Collecting', lessons.length);
  await sweep(lessons, AT_ONCE, PATIENCE, 'pass 1');
  if (stragglers().length && !control.stopped) {
    console.log('[evd] %d did not answer - going round again, slower',
                stragglers().length);
    startBar('Second try', stragglers().length);
    await sweep(stragglers(), 2, PATIENCE * 2, 'pass 2');
  }
  if (control.stopped) console.log('[evd] stopped - showing what was found so far');
  endBar();

  // -- the panel -----------------------------------------------------------
  // Built as a function so a retry can redraw it rather than starting over:
  // fetching a hundred pages again to recover the few that were throttled is
  // most of an hour for no reason.
  const panel = document.createElement('div');
  panel.id = 'evd-box';
  panel.style.cssText = 'position:fixed;inset:5% 8% 76px 8%;margin:0;width:auto;height:auto;z-index:2147483646;background:#0e1020;'
    + 'color:#e8ecff;border:2px solid #6c7cff;border-radius:14px;padding:16px;'
    + 'font:13px system-ui;display:flex;flex-direction:column;gap:10px;'
    + 'box-shadow:0 20px 60px rgba(0,0,0,.6)';

  const heading = document.createElement('div');
  const box = document.createElement('textarea');
  box.style.cssText = 'flex:1;width:100%;background:#05060f;color:#9fe8b0;'
    + 'border:1px solid #2a2f52;border-radius:8px;padding:10px;'
    + 'font:11px ui-monospace,Consolas,monospace;white-space:pre;overflow:auto';

  const row = document.createElement('div');
  row.style.cssText = 'display:flex;gap:8px;align-items:center';
  const button = (text, primary) => {
    const b = document.createElement('button');
    b.textContent = text;
    b.style.cssText = 'border:0;border-radius:8px;padding:9px 16px;cursor:pointer;'
      + 'font:600 13px system-ui;'
      + (primary ? 'background:#6c7cff;color:#fff' : 'background:#232848;color:#cdd4ff');
    return b;
  };
  const copy = button('Copy to clipboard', true);
  const again = button('', false);
  const carry = button('', false);
  copy.onclick = () => {
    box.focus(); box.select(); document.execCommand('copy');
    copy.textContent = 'Copied';
  };

  const close = button('Close', false);
  close.style.cssText += ';position:absolute;top:10px;right:12px;background:transparent;'
    + 'color:#8b93c7;padding:4px;font-weight:400';
  close.onclick = () => {
    if (control.running) window.evdStop();     // closing means stop, too
    panel.remove();
  };

  const render = () => {
    const ordered = lessons.slice().sort(
      (a, b) => a.number.localeCompare(b.number, undefined, { numeric: true }));
    // Anything the course page itself offers, read after the lessons so that
    // whatever they already claimed is not counted twice. A course-wide
    // workbook lives here rather than on any one lesson.
    const lines = [];
    let fileCount = 0;
    for (const r of filesIn(document)) {
      lines.push(r.url + ' | 00_' + r.name + '.' + r.ext);
      fileCount++;
    }
    // Two "lessons" that resolve to one video are one lesson reached twice.
    // The first keeps it; the rest are reported, not queued as duplicates -
    // which download as nothing and leave the queue looking finished.
    const firstFor = {};
    const repeats = [];
    for (const f of ordered) {
      const stem = f.number + '_' + camel(f.title);
      if (f.url && firstFor[f.url]) { repeats.push(f.number); continue; }
      if (f.url) firstFor[f.url] = f.number;
      if (f.url) lines.push(f.url + ' | ' + stem);
      for (const r of (f.files || [])) {
        // a handout keeps its lesson's number, so it sorts beside the video
        lines.push(r.url + ' | ' + stem + '_' + r.name + '.' + r.ext);
        fileCount++;
      }
    }
    box.value = lines.join(String.fromCharCode(10));
    copy.textContent = 'Copy to clipboard';

    // Say why, not only which: a post with no video on it is nothing to
    // chase, a page that would not load is worth another go.
    const gone = ordered.filter(f => !f.url);
    const byReason = {};
    for (const f of gone) {
      const why = f.why || 'no video found';
      (byReason[why] = byReason[why] || []).push(f.number);
    }
    // a long list of numbers says nothing a count does not
    const missed = Object.keys(byReason).map(why => {
      const nums = byReason[why];
      return nums.length > 12 ? nums.length + ' ' + why : nums.join(', ') + ' (' + why + ')';
    }).join('; ');

    heading.innerHTML = '<div style="font-size:16px;font-weight:600">'
      + (lines.length - fileCount) + ' of ' + lessons.length + ' lesson links'
      + (fileCount ? ' and ' + fileCount + ' resource' + (fileCount === 1 ? '' : 's') : '')
      + '</div>'
      + '<div style="opacity:.8">Copy, then press Paste in Easy-dlp.'
      + (missed ? ' <b style="color:#ffb4b4">Not collected: ' + missed + '</b>' : '')
      + (repeats.length ? ' <b style="color:#ffd27a">Left out ' + repeats.length
         + ' that were the same video as an earlier one (' + repeats.join(', ')
         + ').</b>' : '')
      + '</div>';

    const left = stragglers().length;
    again.style.display = left ? '' : 'none';
    again.disabled = false;
    again.textContent = 'Try the ' + left + ' missing again';

    // after a Stop: pick up where it left off, rather than starting over
    const rest = unreached().length;
    carry.style.display = rest ? '' : 'none';
    carry.disabled = false;
    carry.textContent = 'Carry on with the ' + rest + ' not reached';
  };

  again.onclick = async () => {
    const list = stragglers();
    again.disabled = carry.disabled = true;
    startBar('Retrying', list.length);
    for (let i = 0; i < list.length; i++) {
      if (!await gate()) break;
      // one at a time, with the browser to itself and every patience going -
      // this is the pass that gets back what a rate limit took
      await sweep([list[i]], 1, PATIENCE * 3, 'again');
      if (i < list.length - 1) await wait(BREATH);
    }
    endBar();
    render();
  };
  window.evdRetryMissed = () => again.onclick();

  carry.onclick = async () => {
    const list = unreached();
    for (const l of list) l.why = '';
    again.disabled = carry.disabled = true;
    startBar('Collecting', list.length);
    await sweep(list, AT_ONCE, PATIENCE, 'carry on');
    endBar();
    render();
  };

  document.getElementById('evd-box')?.remove();
  row.append(copy, again, carry);
  panel.append(heading, box, row, close);
  document.body.appendChild(panel);
  lift(panel);
  render();
})();
