(async function () {
  'use strict';
  const results = [];
  const summary = document.querySelector('#summary');
  let frame;
  function check(name, condition) {
    results.push({ name, pass: Boolean(condition) });
    const li = document.createElement('li');
    li.className = condition ? 'pass' : 'fail';
    li.textContent = `${condition ? 'PASS' : 'FAIL'} · ${name}`;
    document.querySelector('#results').append(li);
  }
  async function load(page, width = 1440) {
    frame?.remove();
    frame = document.createElement('iframe');
    frame.title = 'Isolated local dashboard under test';
    frame.style.width = `${width}px`;
    frame.src = `../index.html?test=local#${page}`;
    const loaded = new Promise((resolve, reject) => { frame.onload = resolve; frame.onerror = reject; });
    document.body.append(frame);
    await loaded;
    if (!frame.contentDocument?.querySelector('#main')) throw new Error('Cannot inspect dashboard. Run these checks through the optional localhost HTTP server.');
    return { doc: frame.contentDocument, win: frame.contentWindow, $: selector => frame.contentDocument.querySelector(selector) };
  }
  try {
    if (location.protocol === 'file:') throw new Error('Serve this folder with the README’s localhost command, then open /tests/browser-smoke.html. File-origin isolation prevents automated iframe checks.');
    let { doc, win, $ } = await load('monitoring');
    const set = (key, value) => {
      const element = $(`[data-filter="${key}"]`);
      element.value = value;
      element.dispatchEvent(new win.Event('change', { bubbles: true }));
    };
    check('Default main-period monitoring view renders seven formats', doc.querySelectorAll('tbody tr').length === 7);
    set('currency', 'USD');
    const paid = $('.metrics').innerText;
    set('side', 'receiving');
    check('Switching currency dimension recomputes counts', paid !== $('.metrics').innerText);
    check('Currency control retains keyboard focus after rendering', doc.activeElement.dataset.filter === 'side');
    set('period', 'tail');
    check('Sparse-tail selection displays a separate-population warning', Boolean($('.period-warning')));
    $('[data-action="reset"]').click();
    $('[data-grain="pair"]').click();
    $('[data-action="toggle-segments"]').click();
    check('All 28 bank-pair/format segments are inspectable', doc.querySelectorAll('tbody tr').length === 28);
    check('Low-support rows show counts with unranked lift', [...doc.querySelectorAll('tbody tr')].some(row => row.innerText.includes('Low support') && row.innerText.includes('Not ranked')));
    $('[data-segment]').dispatchEvent(new win.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    check('Chart keyboard activation opens segment detail with interval', $('#detail-dialog').open && $('#detail-dialog').innerText.includes('95% descriptive'));
    check('Segment detail separates paid and received currency amounts', $('#detail-dialog').textContent.includes('Paid amounts') && $('#detail-dialog').textContent.includes('Received amounts'));
    $('#detail-dialog').close();

    ({ doc, win, $ } = await load('cases'));
    $('[data-type="Fan-in"]').click();
    check('Fan-in filter has one case and a receiving hub', doc.querySelectorAll('[data-case]').length === 1 && $('.network').textContent.includes('RECEIVING HUB'));
    const node = doc.querySelectorAll('[data-node]')[2];
    node.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    check('Keyboard node selection updates the account inspector', $('#node-inspector').textContent.includes(node.dataset.node.split(':')[1]));
    $('[data-source]').click();
    check('Source inspector exposes complete checksum and ordinal', $('#detail-dialog').open && $('#detail-dialog').textContent.includes('Original 1-based') && $('#detail-dialog').textContent.includes(win.TraceData.sourceChecksum));
    $('#detail-dialog').close();
    $('[data-type="Cycle"]').click();
    check('Cycle case states the chronology limitation', $('.case-body').textContent.includes('Structural closure'));
    $('[data-type="all"]').click();
    $('[data-case="DEMO-FO-004"]').click();
    check('Wide case starts at ten visible accounts with total 104', doc.querySelectorAll('[data-node]').length === 10 && $('.graph-foot').textContent.includes('10 / 104'));
    $('[data-action="toggle-graph"]').click();
    check('Expanded graph stops at the 100-node cap', doc.querySelectorAll('[data-node]').length === 100 && $('.graph-foot').textContent.includes('100 / 104'));
    $('[data-action="next-evidence"]').click();
    check('Full evidence pagination advances independently of graph cap', $('.evidence-panel .table-foot').textContent.includes('7–12'));
    let captured;
    win.URL.createObjectURL = blob => { captured = blob; return 'data:application/octet-stream,fixture'; };
    win.HTMLAnchorElement.prototype.click = function () {};
    $('[data-action="export-evidence"]').click();
    const csv = await captured.text();
    check('Evidence download contains all 124 source records', csv.trim().split('\r\n').length === 125 && csv.includes(win.TraceData.cases[3].edges.at(-1).sourceId));
    check('Evidence download retains exact eight-decimal money strings', csv.includes('1250.00000000'));
    $('[data-action="export-case"]').click();
    const bundle = JSON.parse(await captured.text());
    check('Case bundle preserves all participants and evidence plus identity', bundle.nodes.length === 104 && bundle.edges.length === 124 && bundle.fixtureOnly === true && bundle.run === 'demo-release-01');
    $('#case-search').value = 'no-such-record';
    $('#case-search').dispatchEvent(new win.Event('input', { bubbles: true }));
    check('Search has a useful empty state', $('.case-body').textContent.includes('No matching connections'));
    $('[data-action="reset-cases"]').click();
    check('Clearing case filters restores the queue', doc.querySelectorAll('[data-case]').length === 4);

    ({ doc, win, $ } = await load('evaluation'));
    check('Performance values remain unavailable, not fabricated', [...doc.querySelectorAll('.metric-value')].slice(0, 3).every(element => element.textContent === '—'));
    check('Improvement is explicitly labelled as a target', $('.metrics').textContent.includes('Proposal target · not an achieved result'));
    check('Evaluation shows all three chronological populations', doc.querySelectorAll('.timeline-stage').length === 3);
    ({ doc, win, $ } = await load('release'));
    check('Four local fixture-integrity checks pass', doc.querySelectorAll('.check-row').length === 4 && [...doc.querySelectorAll('.check-row')].every(element => element.textContent.includes('Fixture pass')));
    check('Provenance states no cloud connection', $('.provenance-grid').textContent.includes('No AWS'));

    for (const width of [390, 768, 1024, 1440]) for (const page of ['monitoring', 'cases', 'evaluation', 'release']) {
      ({ doc } = await load(page, width));
      check(`${page} at ${width}px has no whole-page horizontal overflow`, doc.documentElement.scrollWidth <= width);
    }
  } catch (error) {
    check(`Test execution: ${error.message}`, false);
  } finally {
    frame?.remove();
    const passed = results.filter(result => result.pass).length;
    summary.textContent = `${passed} / ${results.length} checks passed. These are local UI-fixture checks, not project validation or measured detection performance.`;
    summary.dataset.complete = 'true';
    summary.dataset.passed = String(passed);
    summary.dataset.total = String(results.length);
    window.TraceSmokeResults = results;
  }
})();
