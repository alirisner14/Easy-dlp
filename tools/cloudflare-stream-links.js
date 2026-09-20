/*
 * Collect every lesson link from a Cloudflare Stream course in one go.
 *
 * On Cloudflare Stream the video id on its own is refused with a 401, unlike
 * Bunny where it plays as it is. What authorises playback is a signed token
 * the site mints per lesson and keeps out of the page source, so the links
 * cannot be scraped - they have to be caught as each lesson starts.
 *
 * This walks the lesson list, lets each one begin, and reads the signed
 * addresses back out of the browser's own resource timing log. It ends with a
 * panel you can copy from, in the "url | file name" form that Easy Video
 * Downloader's Paste button reads.
 *
 * It expects a lesson list numbered like "3. Sketch Head 6:12", which is the
 * usual shape. If a site lays its lessons out differently, the row pattern
 * near the top of the script is the thing to adjust.
 *
 * To use it:
 *   1. open the course while signed in
 *   2. press play on the first lesson and let it start - the browser only
 *      allows playback after you have interacted with the page, and without
 *      playback there is no signed address to catch
 *   3. F12, the Console tab
 *   4. paste this whole file, press Enter
 *   5. wait for the panel (about ten seconds a lesson), Copy, then Paste
 *      into the downloader
 *
 * If lessons come back MISSED, the player was not running: press play again
 * and re-run. Clicking through the lessons yourself works too - this only
 * automates what the browser has already fetched.
 *
 * The links expire about six hours after capture, so download the same day.
 */
(async () => {
  const MANIFEST = '/manifest/video.m3u8';
  const seen = () => performance.getEntriesByType('resource')
    .filter(e => e.name.includes('cloudflarestream.com') && e.name.includes(MANIFEST))
    .map(e => e.name);
  const camel = s => (s.match(/[A-Za-z0-9]+/g) || [])
    .map(w => w[0].toUpperCase() + w.slice(1)).join('');

  // one clickable row per lesson: "3. Sketch Head 6:12"
  const findRows = () => {
    const rows = new Map();
    document.querySelectorAll('a,button,li,div[role="button"]').forEach(el => {
      const s = (el.textContent || '').replace(/\s+/g, ' ').trim();
      const m = s.match(/^(\d{1,2})\.\s*(.+?)\s*(\d{1,2}:\d{2})$/);
      if (m && s.length < 80 && !rows.has(m[1])) {
        rows.set(m[1], { el, n: m[1], title: m[2] });
      }
    });
    return rows;
  };

  // the list is drawn after the page settles, so give it a chance rather
  // than deciding there are no lessons a second too early
  let rows = findRows();
  for (let i = 0; i < 30 && !rows.size; i++) {
    await new Promise(res => setTimeout(res, 1000));
    rows = findRows();
  }
  if (!rows.size) {
    alert('No lessons found. Open the class page itself, with the lesson list '
        + 'showing, and run this again once it has loaded.');
    return;
  }
  console.log('[evd] %d lessons, this takes about %d seconds', rows.size, rows.size * 8);

  const found = [];
  for (const r of [...rows.values()]) {
    // clear the log first: a lesson already played earlier would otherwise
    // look like it produced nothing
    performance.clearResourceTimings();
    r.el.click();
    let url = null;
    for (let i = 0; i < 10 && !url; i++) {
      await new Promise(res => setTimeout(res, 1000));
      url = seen()[0] || null;
    }
    console.log('[evd] %s. %s %s', r.n, r.title, url ? 'ok' : 'MISSED');
    found.push({ n: r.n, title: r.title, url });
  }

  const lines = found.filter(f => f.url)
    .map(f => f.url + ' | ' + String(f.n).padStart(2, '0') + '_' + camel(f.title));
  const missed = found.filter(f => !f.url).map(f => f.n).join(', ');

  document.getElementById('evd-box')?.remove();
  const wrap = document.createElement('div');
  wrap.id = 'evd-box';
  wrap.style.cssText = 'position:fixed;inset:5% 8%;z-index:2147483647;background:#0e1020;'
    + 'color:#e8ecff;border:2px solid #6c7cff;border-radius:14px;padding:16px;'
    + 'font:13px system-ui;display:flex;flex-direction:column;gap:10px;'
    + 'box-shadow:0 20px 60px rgba(0,0,0,.6)';
  wrap.innerHTML = '<div style="font-size:16px;font-weight:600">'
    + lines.length + ' of ' + rows.size + ' lesson links</div>'
    + '<div style="opacity:.8">Copy, then press Paste in Easy-dlp. '
    + 'These expire in about six hours.'
    + (missed ? ' <b style="color:#ffb4b4">Missed: ' + missed + '</b> - run it again.' : '')
    + '</div>';

  const ta = document.createElement('textarea');
  ta.value = lines.join('\n');
  ta.style.cssText = 'flex:1;width:100%;background:#05060f;color:#9fe8b0;'
    + 'border:1px solid #2a2f52;border-radius:8px;padding:10px;'
    + 'font:11px ui-monospace,Consolas,monospace;white-space:pre;overflow:auto';

  const copy = document.createElement('button');
  copy.textContent = 'Copy to clipboard';
  copy.style.cssText = 'align-self:flex-start;background:#6c7cff;color:#fff;border:0;'
    + 'border-radius:8px;padding:9px 16px;font:600 13px system-ui;cursor:pointer';
  copy.onclick = () => {
    ta.focus(); ta.select(); document.execCommand('copy'); copy.textContent = 'Copied';
  };

  const close = document.createElement('button');
  close.textContent = 'Close';
  close.style.cssText = 'position:absolute;top:10px;right:12px;background:transparent;'
    + 'color:#8b93c7;border:0;font:13px system-ui;cursor:pointer';
  close.onclick = () => wrap.remove();

  wrap.append(ta, copy, close);
  document.body.appendChild(wrap);
})();
