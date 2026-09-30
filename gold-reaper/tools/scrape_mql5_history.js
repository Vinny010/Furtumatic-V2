// scrape_mql5_history.js — run in Chrome DevTools console on
//   https://www.mql5.com/en/signals/2265877#!tab=history   (logged in, History tab open)
// 1) if an Export/CSV link exists it is logged and we stop (click it instead).
// 2) else clicks "More"/"Show more" until the row count stops growing,
// 3) then serialises the largest table to CSV and downloads it.
// Selectors are generic on purpose; if row count is 0, inspect the table and
// adjust ROW_SEL / CELL_SEL below.
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const vis = el => !!(el && el.offsetParent !== null);

  // --- 0) prefer an official export if the page offers one ------------------
  const exp = [...document.querySelectorAll('a,button')].find(e =>
    /export|download.*csv|csv/i.test((e.textContent||'') + ' ' + (e.getAttribute('href')||'')));
  if (exp) { console.warn('EXPORT LINK FOUND — click this instead:', exp); exp.scrollIntoView(); return; }

  // --- 1) expand: click "More" until nothing grows --------------------------
  const ROW_SEL  = 'table tr';
  const moreBtn  = () => [...document.querySelectorAll('button,a,span,div')]
      .find(e => vis(e) && /^\s*(more|show more|load more|показать ещё)\s*$/i.test(e.textContent||''));
  let stale = 0, last = -1;
  for (let i = 0; i < 400; i++) {
    const b = moreBtn();
    const n = document.querySelectorAll(ROW_SEL).length;
    if (n === last) stale++; else stale = 0;
    last = n;
    if (!b || stale >= 4) break;
    b.click(); window.scrollTo(0, document.body.scrollHeight);
    await sleep(1300);
  }

  // --- 2) serialise the biggest table ----------------------------------------
  const tables = [...document.querySelectorAll('table')];
  const t = tables.sort((a,b)=>b.rows.length-a.rows.length)[0];
  if (!t) { console.error('no <table> found — adjust selectors'); return; }
  const q = s => '"' + String(s).replace(/\s+/g,' ').trim().replace(/"/g,'""') + '"';
  const lines = [...t.rows].map(r => [...r.cells].map(c => q(c.textContent)).join(','));
  const csv = lines.join('\n');

  // --- 3) report + download ---------------------------------------------------
  const dateRe = /\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}/g;
  const dates = csv.match(dateRe) || [];
  console.log('rows (incl. header):', lines.length, '| first date:', dates[0], '| last date:', dates[dates.length-1]);
  const blob = new Blob([csv], {type:'text/csv'});
  const a = Object.assign(document.createElement('a'), {href: URL.createObjectURL(blob), download: 'gold_reaper_history.csv'});
  document.body.appendChild(a); a.click(); a.remove();
})();
