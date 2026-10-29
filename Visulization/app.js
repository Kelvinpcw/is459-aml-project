(function () {
  'use strict';
  const D = window.TraceData, M = window.TraceModel;
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const number = value => value.toLocaleString('en-US');
  const compact = value => value >= 1000000 ? `${(value / 1000000).toFixed(2)}M` : value >= 10000 ? `${(value / 1000).toFixed(1)}K` : number(value);
  const pct = (value, digits = 2) => value === null ? 'Not available' : `${(value * 100).toFixed(digits)}%`;
  const times = value => value === null ? 'N/A' : `${value.toFixed(2)}×`;
  const color = format => D.formats.find(item => item.name === format)?.color || '#73946b';
  const iconPaths = {
    overview: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    network: '<circle cx="12" cy="5" r="2.5"/><circle cx="5" cy="18" r="2.5"/><circle cx="19" cy="18" r="2.5"/><path d="m11 7-5 9m7-9 5 9M8 18h8"/>',
    shield: '<path d="M12 3 4 6v6c0 4.5 8 9 8 9s8-4.5 8-9V6z"/><path d="m8 12 3 3 5-6"/>',
    layers: '<path d="m3 7 9-4 9 4-9 4zM3 12l9 4 9-4M3 17l9 4 9-4"/>',
    chevron: '<path d="m9 5 7 7-7 7"/>',
    download: '<path d="M12 3v12m-4-4 4 4 4-4M4 15v5h16v-5"/>',
    arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    chart: '<path d="M4 3v17h17M8 15v-4m5 4V7m5 8V4"/>',
    activity: '<path d="M2 12h5l3-8 4 16 3-8h5"/>',
    target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
    reset: '<path d="M4 10a8 8 0 1 1 1 8M4 4v6h6"/>',
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    check: '<path d="m5 12 4 4L20 5"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 4v3"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
    close: '<path d="m6 6 12 12M18 6 6 18"/>',
    file: '<path d="M14 3H5v18h14V8zM14 3v5h5M8 12h8m-8 4h8"/>',
    warning: '<path d="m12 3 10 18H2zM12 9v5m0 3h.01"/>',
  };
  const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${iconPaths[name] || iconPaths.info}</svg>`;
  document.querySelectorAll('[data-icon]').forEach(element => { element.innerHTML = icon(element.dataset.icon); });
  const initialFilters = { period: 'main', side: 'payment', currency: 'all', format: 'all', bank: 'all', grain: 'format', support: 1000, sort: 'lift' };
  const state = { page: 'monitoring', filters: { ...initialFilters }, showAllSegments: false, caseType: 'all', caseDate: 'all', query: '', selectedCase: D.cases[0].id, selectedNode: null, evidencePage: 0, graphExpanded: false };
  let toastTimer;
  function toast(message) {
    $('#toast').textContent = message;
    $('#toast').classList.add('visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $('#toast').classList.remove('visible'), 3500);
  }
  function download(name, text, type) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = name; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast(`Downloaded ${name} · illustrative data only`);
  }
  function option(value, label, selected) { return `<option value="${esc(value)}"${String(value) === String(selected) ? ' selected' : ''}>${esc(label)}</option>`; }
  function selectFilter(key, label, options) {
    return `<label class="filter"><span>${label}</span><select data-filter="${key}" aria-label="${label}">${options.map(([value, text]) => option(value, text, state.filters[key])).join('')}</select></label>`;
  }
  function heading(eyebrow, title, description, actions = '') {
    return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="heading-description">${description}</p></div>${actions ? `<div class="heading-actions">${actions}</div>` : ''}</div>`;
  }
  function metric(title, value, foot, name, featured = false, extra = '') {
    return `<article class="metric${featured ? ' featured' : ''}"><div class="metric-title">${title}${icon(name)}</div><div class="metric-value">${value}</div><div class="metric-foot">${foot}</div>${extra}</article>`;
  }
  function sparkline(population) {
    const days = [...new Set(population.map(row => row.date))].sort();
    const values = days.map(day => M.sum(population.filter(row => row.date === day), 'n'));
    const min = Math.min(...values), max = Math.max(...values);
    const points = values.map((value, index) => `${index * 68 / Math.max(1, values.length - 1)},${22 - (value - min) / (max - min || 1) * 18}`).join(' ');
    return `<svg class="sparkline" viewBox="0 0 70 25" aria-hidden="true"><polyline points="${points}" fill="none" stroke="#91aa77" stroke-width="1.5"/></svg>`;
  }
  function scatter(result) {
    if (!result.segments.length) return '<div class="empty-state"><p>No segments match this filter combination.</p></div>';
    const segments = result.segments;
    const W = 660, H = 275, left = 53, right = 30, top = 20, bottom = 45;
    const maxN = Math.max(...segments.map(item => item.n)) * 1.15;
    const maxRate = Math.max(result.baseline * 2, ...segments.map(item => item.rate)) * 1.22 || .01;
    const maxLabels = Math.max(1, ...segments.map(item => item.l));
    const x = n => left + n / maxN * (W - left - right);
    const y = r => H - bottom - r / maxRate * (H - top - bottom);
    let marks = '';
    for (let tick = 0; tick <= 4; tick++) {
      const value = maxRate / 4 * tick, ty = y(value);
      marks += `<line class="grid" x1="${left}" x2="${W - right}" y1="${ty}" y2="${ty}"/><text class="axis-label" x="${left - 9}" y="${ty + 3}" text-anchor="end">${pct(value, value >= .1 ? 0 : 2)}</text>`;
      const tx = x(maxN / 4 * tick);
      marks += `<text class="axis-label" x="${tx}" y="${H - bottom + 20}" text-anchor="middle">${compact(Math.round(maxN / 4 * tick))}</text>`;
    }
    marks += `<line x1="${left}" x2="${W - right}" y1="${y(result.baseline)}" y2="${y(result.baseline)}" stroke="#9aa884" stroke-dasharray="5 5"/><text x="${W - right}" y="${y(result.baseline) - 7}" text-anchor="end" fill="#859275" font-size="9">Selected baseline ${pct(result.baseline)}</text>`;
    segments.forEach((item, index) => {
      const radius = 5 + Math.sqrt(item.l / maxLabels) * 15;
      const label = state.filters.grain === 'pair' ? `${item.fromBank} → ${item.toBank}` : item.key;
      const showLabel = state.filters.grain !== 'pair' || index < 5;
      const labelY = y(item.rate) + (item.rate < maxRate * .14 ? -13 - index % 3 * 12 : -radius - 9);
      marks += `<g class="bubble" role="button" tabindex="0" data-segment="${esc(item.key)}" aria-label="Inspect ${esc(item.key)}, ${number(item.n)} transactions, ${pct(item.rate)} labelled rate, ${times(item.lift)} lift"><title>${esc(item.key)} · N=${number(item.n)} · L=${number(item.l)} · ${pct(item.rate)} · ${times(item.lift)} lift${item.supported ? '' : ' · LOW SUPPORT'}</title><circle cx="${x(item.n)}" cy="${y(item.rate)}" r="${radius}" fill="${color(item.format)}" fill-opacity="${item.supported ? '.72' : '.25'}" stroke="${color(item.format)}" stroke-width="1.2"${item.supported ? '' : ' stroke-dasharray="3 3"'}/>${showLabel ? `<text class="point-label" x="${Math.max(left + 10, x(item.n))}" y="${Math.max(top + 7, labelY)}" text-anchor="middle">${esc(label)}</text>` : ''}</g>`;
    });
    return `<svg class="scatter" viewBox="0 0 ${W} ${H}" role="group" aria-label="Interactive volume versus historical labelled-rate plot. The same values are available in the segment table."><text class="axis-label" x="${left}" y="10">Labelled rate</text>${marks}<text class="axis-label" x="${W / 2}" y="${H - 2}" text-anchor="middle">Transaction volume →</text></svg>`;
  }
  function priorityCard(result) {
    const priority = result.segments.find(segment => segment.supported && segment.lift > 1);
    if (!priority) return `<aside class="priority-card"><div class="eyebrow">READING THE SIGNAL</div><h2>No supported priority in this selection.</h2><div class="priority-rule"></div><p>Try widening the reporting scope. A zero baseline cannot produce a meaningful risk lift.</p><span class="priority-disclaimer">No ranking is better than an unsupported ranking.</span></aside>`;
    return `<aside class="priority-card"><div class="eyebrow">A MONITORING LEAD, EXPLAINED</div><h2>${esc(priority.format)} deserves<br>a closer look.</h2><div class="priority-lift"><strong>${priority.lift.toFixed(1)}<small>×</small></strong><span>the selected<br>baseline rate</span></div><p><strong>${pct(priority.trafficShare, 1)}</strong> of transactions account for<br><strong>${pct(priority.labelShare, 1)}</strong> of historical labelled activity${state.filters.grain === 'pair' ? ` in bank pair ${esc(priority.fromBank)} → ${esc(priority.toBank)}` : ''}.</p><div class="priority-rule"></div><p>Review the controls, not just the volume.</p><div class="priority-disclaimer">Historical association, not a claim of criminal intent.</div><button class="btn" data-segment="${esc(priority.key)}">Inspect this segment ${icon('arrow')}</button></aside>`;
  }
  function segmentTable(result) {
    const displayed = state.showAllSegments ? result.segments : result.segments.slice(0, 10);
    const low = result.segments.filter(item => !item.supported).length;
    return `<section class="panel table-panel" aria-label="Monitoring priority segments"><div class="section-head"><div><h2>Where to focus your attention</h2><p>Supported exposure first. Always keep the denominator in view.</p></div><div class="table-controls"><div class="segmented" aria-label="Summary grain"><button data-grain="format" class="${state.filters.grain === 'format' ? 'active' : ''}" aria-pressed="${state.filters.grain === 'format'}">Payment formats</button><button data-grain="pair" class="${state.filters.grain === 'pair' ? 'active' : ''}" aria-pressed="${state.filters.grain === 'pair'}">Bank pair + format</button></div><select class="small-select" data-filter="support" aria-label="Minimum segment support">${[100, 500, 1000].map(n => option(n, `Support ≥ ${number(n)}`, state.filters.support)).join('')}</select><select class="small-select" data-filter="sort" aria-label="Rank segments by">${option('lift', 'Rank by lift', state.filters.sort)}${option('volume', 'Rank by volume', state.filters.sort)}</select></div></div><div class="table-scroll"><table><thead><tr><th scope="col">${state.filters.grain === 'pair' ? 'Bank pair · format' : 'Payment format'}</th><th scope="col">Transactions · N</th><th scope="col">Labelled · L</th><th scope="col">Rate · L/N</th><th scope="col">Risk lift</th><th scope="col">Traffic share</th><th scope="col">Support</th></tr></thead><tbody>${displayed.map(item => `<tr><td><button class="segment-button" data-segment="${esc(item.key)}"><span class="format-dot" style="background:${color(item.format)}"></span>${esc(item.key)}</button></td><td>${number(item.n)}</td><td>${number(item.l)}</td><td>${pct(item.rate)}</td><td>${item.supported ? `<span class="lift-label${item.lift > 1 ? '' : ' neutral'}">${times(item.lift)}</span>` : '<span class="badge badge-warm">Not ranked</span>'}</td><td><span class="share-cell">${pct(item.trafficShare, 1)}<span class="share-track"><span style="width:${item.trafficShare * 100}%"></span></span></span></td><td><span class="badge${item.supported ? '' : ' badge-warm'}">${item.supported ? 'Sufficient N' : 'Low support'}</span></td></tr>`).join('') || '<tr><td colspan="7" style="text-align:center;padding:30px">No segments match the current filters. Reset filters to start again.</td></tr>'}</tbody></table></div><div class="table-foot"><span>Showing <strong>${displayed.length}</strong> of ${result.segments.length} segments${low ? ` · ${low} low-support segment${low > 1 ? 's' : ''} shown as counts, not ranked risk` : ''}</span><button class="btn-text" data-action="export-q1">Export all filtered segments ↗</button></div></section>`;
  }
  function monitoring() {
    const result = M.aggregate(D.q1, state.filters);
    const priorities = result.segments.filter(segment => segment.supported && segment.lift >= 2).length;
    return `${heading('01 / COMPLIANCE MANAGEMENT', 'Monitoring overview', 'See where historical exposure outweighs transaction volume.', `<button class="btn" data-action="export-q1">${icon('download')} Export summary</button>`)}
      <section class="filters" aria-label="Historical exposure filters">${selectFilter('period', 'Reporting period', Object.entries(M.periods).map(([value, period]) => [value, period.label]))}${selectFilter('side', 'Currency dimension', [['payment', 'Payment currency'], ['receiving', 'Receiving currency']])}${selectFilter('currency', 'Currency', [['all', 'All currencies'], ...D.currencies.map(currency => [currency, currency])])}${selectFilter('format', 'Payment format', [['all', 'All formats'], ...D.formats.map(format => [format.name, format.name])])}${selectFilter('bank', 'Bank involved', [['all', 'All banks'], ...['020', '070', '008381', '011'].map(bank => [bank, `Bank ${bank}`])])}<button class="filter-reset" data-action="reset" aria-label="Reset monitoring filters" title="Reset filters">${icon('reset')}</button></section>
      ${state.filters.period === 'tail' ? `<div class="callout period-warning">${icon('warning')}<div><strong>Sparse tail — separate population.</strong> 17–28 September is not comparable with the main period. Do not present this selection as headline detector performance. Values below are invented fixtures.</div></div>` : ''}
      <section class="metrics" aria-label="Selected population summary">${metric('Transactions in scope', compact(result.n), `${number(result.n)} total · selected population`, 'chart', false, sparkline(result.population))}${metric('Historically labelled', compact(result.l), 'Known labels · not new detections', 'activity')}${metric('Labelled rate', pct(result.baseline), '<strong>Σ labelled / Σ transactions</strong> · not daily averages', 'target')}${metric('Supported priorities', `${priorities}<small> segments</small>`, `Lift ≥ 2× · N ≥ ${number(Number(state.filters.support))}`, 'shield', true)}</section>
      <section class="chart-row"><div class="panel chart-panel"><div class="section-head"><div><h2>Volume isn’t the whole story.</h2><p>Compare scale with historical labelled exposure.</p></div><div class="chart-top-note"><span class="tiny-circle"></span> Area = labelled count</div></div>${scatter(result)}<div class="chart-caption"><span><span class="dash-swatch"></span> Selected-population baseline</span><span>Bubble area ≈ labelled count · select to inspect</span></div></div>${priorityCard(result)}</section>
      ${result.segments.length > 10 ? `<div style="display:flex;justify-content:flex-end;margin-bottom:10px"><button class="btn-text" data-action="toggle-segments">${state.showAllSegments ? 'Show top 10 only' : `Show all ${result.segments.length} segments, including low support`} ${icon('chevron')}</button></div>` : ''}${segmentTable(result)}<div class="method-note">${icon('info')}<span>Historical labels measure association, not causation. Counts, support and baseline share the same date, bank, format and currency filters. Amounts stay separate by currency. Illustrative fixtures only.</span></div>`;
  }
  function selectedCase() { return D.cases.find(item => item.id === state.selectedCase); }
  function nodeInspector(item) {
    const node = item.nodes.find(node => node.key === state.selectedNode) || item.nodes[0];
    const incoming = item.edges.filter(edge => edge.receiver === node.key).length;
    const outgoing = item.edges.filter(edge => edge.sender === node.key).length;
    return `<div class="eyebrow">SELECTED ACCOUNT</div><h3 class="mono">${esc(node.account)}</h3><dl><div><dt>Bank / normalised key</dt><dd>${esc(node.rawBank)} / ${esc(node.key)}</dd></div><div><dt>Entity mapping</dt><dd>${esc(node.entityId || 'Unknown entity')}<br>${node.entityId ? esc(node.entityName) : 'Retained, not dropped'}</dd></div><div><dt>Core transactions</dt><dd>${incoming} incoming · ${outgoing} outgoing</dd></div></dl><div class="inspector-note">Ownership is a static synthetic mapping, not a dated ownership history. Accounts remain separate even when entities match.</div>`;
  }
  function network(item) {
    const limit = state.graphExpanded ? 100 : 10;
    const graph = M.boundedGraph(item, limit, 500);
    const positions = new Map();
    const W = 530, H = 400, cx = item.type === 'Cycle' ? 265 : 200, cy = 190;
    if (item.type === 'Cycle') graph.nodes.forEach((node, i) => {
      const angle = -Math.PI / 2 + i / graph.nodes.length * Math.PI * 2;
      positions.set(node.key, [265 + Math.cos(angle) * 120, 180 + Math.sin(angle) * 113]);
    });
    else graph.nodes.forEach((node, i) => {
      if (!i) positions.set(node.key, [cx, cy]);
      else {
        const angle = -Math.PI * .83 + (i - 1) / Math.max(1, graph.nodes.length - 1) * Math.PI * 2;
        const radius = state.graphExpanded && graph.nodes.length > 20 ? 115 + i % 3 * 17 : 130;
        positions.set(node.key, [cx + Math.cos(angle) * radius * 1.13, cy + Math.sin(angle) * radius]);
      }
    });
    const short = node => node.account.replace('DEMO', '…');
    let markup = '';
    const entities = new Map();
    graph.nodes.forEach(node => { if (node.entityId) { if (!entities.has(node.entityId)) entities.set(node.entityId, []); entities.get(node.entityId).push(node); } });
    entities.forEach(nodes => {
      if (nodes.length < 2) return;
      const coords = nodes.map(node => positions.get(node.key));
      const x1 = Math.min(...coords.map(p => p[0])) - 28, x2 = Math.max(...coords.map(p => p[0])) + 28;
      const y1 = Math.min(...coords.map(p => p[1])) - 28, y2 = Math.max(...coords.map(p => p[1])) + 28;
      markup += `<rect x="${x1}" y="${y1}" width="${x2 - x1}" height="${y2 - y1}" rx="28" fill="#d7bd8a0b" stroke="#c7b188" stroke-dasharray="4 4"/><text x="${x1 + 12}" y="${y1 - 6}" font-size="8" fill="#a18c6b">Same entity</text>`;
    });
    graph.edges.forEach(edge => {
      const [x1, y1] = positions.get(edge.sender), [x2, y2] = positions.get(edge.receiver);
      const distance = Math.hypot(x2 - x1, y2 - y1), pad = state.graphExpanded ? 8 : 21;
      const sx = x1 + (x2 - x1) / distance * pad, sy = y1 + (y2 - y1) / distance * pad;
      const ex = x2 - (x2 - x1) / distance * (pad + 5), ey = y2 - (y2 - y1) / distance * (pad + 5);
      markup += `<line x1="${sx}" y1="${sy}" x2="${ex}" y2="${ey}" stroke="#8da581" stroke-width="${state.graphExpanded ? 1 : 1.5}" marker-end="url(#edge-arrow)"/>${graph.nodes.length <= 12 ? `<text class="edge-count" x="${(x1 + x2) / 2}" y="${(y1 + y2) / 2 - 7}" text-anchor="middle">${edge.sourceIds.length} tx</text>` : ''}`;
    });
    graph.nodes.forEach((node, i) => {
      const [x, y] = positions.get(node.key);
      const selected = state.selectedNode ? node.key === state.selectedNode : !i;
      const radius = graph.nodes.length > 20 ? 4 : !i && item.type !== 'Cycle' ? 22 : 15;
      const hub = !i && item.type !== 'Cycle';
      const hubLabel = item.type === 'Fan-in' ? 'RECEIVING HUB' : 'SENDING HUB';
      const glyph = hub
        ? `<path d="M${x - 7} ${y - 5}h14m-7 0v12m-4-6h8" stroke="#dceabe" stroke-width="1.8" fill="none"/>`
        : `<circle cx="${x}" cy="${y}" r="4" fill="#a6ba94"/>`;
      markup += `<g class="node${selected ? ' selected' : ''}" role="button" tabindex="0" data-node="${esc(node.key)}"
        aria-label="${short(node)} ${hub ? hubLabel : `BANK ${node.rawBank}`} — Inspect bank ${esc(node.rawBank)}, account ${esc(node.account)}, ${esc(node.entityId || 'unknown entity')}">
        <title>Bank ${esc(node.rawBank)} · ${esc(node.account)} · ${esc(node.entityName)}</title>
        <circle class="selection-ring" cx="${x}" cy="${y}" r="${radius + 6}" fill="#dfeacf" stroke="#c6d4b8"/>
        <circle cx="${x}" cy="${y}" r="${radius}" fill="${hub ? '#335d42' : '#f0f4e9'}" stroke="${hub ? '#335d42' : '#9caf8d'}" stroke-width="1.4"/>
        ${graph.nodes.length <= 12 ? `${glyph}<text x="${x}" y="${y + radius + 18}" text-anchor="middle">${short(node)}</text>
        <text x="${x}" y="${y + radius + 30}" text-anchor="middle" style="font-size:8px">${hub ? hubLabel : `BANK ${node.rawBank}`}</text>` : ''}</g>`;
    });
    return { graph, svg: `<svg class="network" viewBox="0 0 ${W} ${H}" role="group" aria-label="Directed ${esc(item.type)} account graph. Arrow direction follows payment direction. Select an account to inspect it."><defs><marker id="edge-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="m0 0 6 3-6 3" fill="#8da581"/></marker></defs>${markup}</svg>` };
  }
  function evidence(item) {
    const perPage = 6, pages = Math.ceil(item.edges.length / perPage);
    state.evidencePage = Math.min(state.evidencePage, pages - 1);
    const rows = item.edges.slice(state.evidencePage * perPage, (state.evidencePage + 1) * perPage);
    return `<section class="panel evidence-panel"><div class="section-head"><div><h2>Follow the source records</h2><p>Every core transaction remains retrievable, including parallel transfers.</p></div><button class="btn btn-small" data-action="export-evidence">${icon('download')} All ${item.edges.length} records</button></div><div class="table-scroll"><table><thead><tr><th scope="col">Source ordinal ↗</th><th scope="col">Dataset-local time</th><th scope="col">From → to account</th><th scope="col">Paid</th><th scope="col">Received</th><th scope="col">Format</th></tr></thead><tbody>${rows.map(edge => `<tr><td><button class="btn-text mono" data-source="${esc(edge.sourceId)}" aria-label="Inspect source record ${edge.sourceRecordOrdinal}">#${edge.sourceRecordOrdinal}</button></td><td>${edge.timestamp.slice(5, 16).replace('T', ' ')}</td><td class="mono">${esc(edge.senderAccount.slice(-6))} → ${esc(edge.receiverAccount.slice(-6))}</td><td>${M.formatMoney(BigInt(edge.amountPaid.replace('.', '')))} ${edge.paymentCurrency}</td><td>${M.formatMoney(BigInt(edge.amountReceived.replace('.', '')))} ${edge.receivingCurrency}</td><td>${edge.format}</td></tr>`).join('')}</tbody></table></div><div class="table-foot"><span>Showing ${state.evidencePage * perPage + 1}–${Math.min((state.evidencePage + 1) * perPage, item.edges.length)} of <strong>${item.edges.length} core transactions</strong></span><div class="pagination"><button data-action="prev-evidence" aria-label="Previous evidence page"${state.evidencePage === 0 ? ' disabled' : ''}>←</button><span>${state.evidencePage + 1} / ${pages}</span><button data-action="next-evidence" aria-label="Next evidence page"${state.evidencePage === pages - 1 ? ' disabled' : ''}>→</button></div></div></section>`;
  }
  function caseDetails(item) {
    const { graph, svg } = network(item);
    return `<div class="case-heading"><div><small class="mono">${item.id} <span aria-hidden="true">/</span> ${item.ruleId}</small><h2>${esc(item.title)}</h2></div><button class="btn btn-small" data-action="export-case">${icon('download')} Case bundle</button></div><div class="case-meta"><span><strong>Snapshot</strong> ${item.snapshotDate}</span><span><strong>Lookback</strong> 7 days</span><span><strong>Window</strong> [${item.windowStart.slice(5, 10)}, ${item.cutoffExclusive.slice(5, 10)})</span><span class="badge badge-neutral">Label-free discovery</span></div><section class="graph-panel" aria-label="Case graph"><div class="graph-toolbar"><h3>Connected accounts</h3><div class="legend"><span><i class="legend-dot"></i> Account</span><span><i class="legend-ring"></i> Shared entity</span><span>→ Core transfer</span></div></div><div class="graph-body"><div class="network-wrap">${svg}<div class="network-note">Select a node · links aggregate parallel transactions</div></div><aside class="node-inspector" id="node-inspector" aria-live="polite">${nodeInspector(item)}</aside></div><div class="graph-foot"><span>${graph.nodes.length} / ${item.nodes.length} accounts · ${graph.edges.length} directed links · ${graph.visibleTransactions} / ${item.edges.length} core transactions in view</span>${item.nodes.length > 10 ? `<button class="btn-text" data-action="toggle-graph">${state.graphExpanded ? 'Compact view' : 'Expand to 100-node cap'} ↗</button>` : '<span>Full case in view</span>'}</div></section>
      ${graph.capped ? `<div class="method-note">${icon('info')}<span>Bounded display, not bounded evidence. ${graph.hiddenNodes} accounts and ${item.edges.length - graph.visibleTransactions} core records are outside this view. The CSV and case bundle always include the complete case.</span></div>` : ''}
      <div class="rule-card">${icon('network')}<div><h3>Why this case was generated</h3><p>${esc(item.description)} ${item.type === 'Cycle' ? 'Rule: 2–4 distinct accounts.' : `Rule: at least 5 distinct counterparties; observed ${item.nodes.length - 1}.`} Only transactions within [${item.windowStart.replace('T', ' ')}, ${item.cutoffExclusive.replace('T', ' ')}) are eligible.</p></div></div>${evidence(item)}<div class="method-note">${icon('warning')}<span>A structural lead is not proof of laundering. ${item.chronology ? `${esc(item.chronology)} ` : ''}${esc(item.history)}. Self-transfers are excluded from motifs, not from stored source data.</span></div>`;
  }
  function cases() {
    const filtered = M.filterCases(D.cases, { type: state.caseType, date: state.caseDate, query: state.query });
    if (!filtered.some(item => item.id === state.selectedCase)) { state.selectedCase = filtered[0]?.id || null; state.selectedNode = null; state.evidencePage = 0; state.graphExpanded = false; }
    const item = selectedCase();
    return `${heading('02 / CONNECTED-ACCOUNT INVESTIGATION', 'Follow the connections.', 'Explainable structures. Traceable evidence. A starting point, not a verdict.', '<span class="badge">LABEL-FREE CASE FIXTURES</span>')}<div class="cases-filters"><label class="search-box">${icon('search')}<input id="case-search" type="search" placeholder="Find a case, account or entity…" aria-label="Search cases, accounts or entities" value="${esc(state.query)}" autocomplete="off"></label><div class="segmented" aria-label="Pattern type">${['all', 'Fan-in', 'Fan-out', 'Cycle'].map(type => `<button data-type="${type}" class="${state.caseType === type ? 'active' : ''}" aria-pressed="${state.caseType === type}">${type === 'all' ? 'All patterns' : type}</button>`).join('')}</div><label>Snapshot<select class="small-select" id="case-date" aria-label="Case snapshot date">${option('all', 'All demo snapshots', state.caseDate)}${['2022-09-14', '2022-09-15', '2022-09-16'].map(date => option(date, date, state.caseDate)).join('')}</select></label></div><div class="case-layout"><div class="case-list"><div class="case-list-heading"><span>INVESTIGATION LEADS</span><span>${filtered.length.toString().padStart(2, '0')}</span></div>${filtered.map(caseData => `<button class="case-card${caseData.id === state.selectedCase ? ' selected' : ''}" data-case="${caseData.id}" aria-pressed="${caseData.id === state.selectedCase}"><span class="case-card-top"><span class="badge${caseData.type === 'Cycle' ? ' badge-purple' : caseData.type === 'Fan-in' ? ' badge-warm' : ''}">${caseData.type}</span><span class="mono">${caseData.id}</span></span><strong>${esc(caseData.title)}</strong><span class="case-card-info"><span>${caseData.nodes.length} accounts · ${caseData.edges.length} tx</span><span>${caseData.snapshotDate.slice(8)} Sep</span></span></button>`).join('')}<p class="case-list-note">No severity score or “laundering” verdict. Cases are ordered for exploration, not by label-derived risk.</p></div><div class="case-body">${item ? caseDetails(item) : `<section class="panel empty-state">${icon('search')}<h2>No matching connections</h2><p>Try a different pattern, snapshot, case ID, account or entity.</p><button class="btn" data-action="reset-cases">Clear case filters</button></section>`}</div></div>`;
  }
  function evaluation() {
    return `${heading('03 / OFFLINE EVALUATION', 'Evidence before confidence.', 'A separate assessment of detector performance — never an input to discovery.', '<span class="badge badge-warm">NOT EVALUATED IN THIS CONCEPT</span>')}
      <section class="metrics">${metric('Transaction precision', '—', 'Requires eligible labelled reference population', 'target')}${metric('Transaction recall', '—', 'Not measurable from these UI fixtures', 'activity')}${metric('Typed attempt recovery', '—', 'Incomplete annotations ≠ exhaustive truth', 'network')}${metric('Recovery improvement', '+5<small> pp</small>', 'Proposal target · not an achieved result', 'shield', true)}</section>
      <div class="section-grid"><section class="panel panel-padding"><div class="section-head"><div><h2>Keep time on your side.</h2><p>Freeze settings before holdout. Never pull future edges into an earlier snapshot.</p></div>${icon('clock')}</div><div class="timeline"><div class="timeline-stage"><div class="eyebrow">01 / DEVELOPMENT</div><strong>01–08 Sep</strong><p>Calibrate support and thresholds. Freeze configuration before evaluation.</p></div><div class="timeline-stage"><div class="eyebrow">02 / HOLDOUT</div><strong>09–16 Sep</strong><p>Evaluate unchanged settings on the complete declared eligible population.</p></div><div class="timeline-stage"><div class="eyebrow">03 / SPARSE TAIL</div><strong>17–28 Sep</strong><p>Report separately. A different traffic mix is not a headline benchmark.</p></div></div><p class="text-small">These dates describe the proposal’s protocol, not an evaluation executed by this prototype.</p></section><aside class="big-note"><div class="eyebrow">THE IMPORTANT DISTINCTION</div><h2>Find the structure.<br>Then check the answers.</h2><p>Q2 discovers cases without labels, pattern annotations or Q1 risk scores. Only the separate evaluator may join reference answers afterwards.</p><p>An unannotated case is not automatically a false positive.</p></aside></div>
      <section class="panel table-panel evaluation-table"><div class="section-head"><div><h2>The scorecard we would publish</h2><p>Unavailable values stay unavailable. No invented performance percentages.</p></div></div><div class="table-scroll"><table><thead><tr><th scope="col">Measure</th><th scope="col">Definition / eligible denominator</th><th scope="col">Current state</th></tr></thead><tbody><tr><td>Core transaction precision</td><td>Labelled-positive core alerted transactions / all eligible core alerted transactions, deduplicated by source ID.</td><td><span class="badge badge-neutral">Not evaluated</span></td></tr><tr><td>Core transaction recall</td><td>Labelled-positive core alerted transactions / all labelled positives in the declared eligible population, including missed cases.</td><td><span class="badge badge-neutral">Not evaluated</span></td></tr><tr><td>Typed attempt recovery</td><td>Eligible attempts recovered with the correct type and hub/cycle, and ≥80% of matched annotated edges inside one case’s core evidence.</td><td><span class="badge badge-neutral">Not evaluated</span></td></tr><tr><td>Type-agnostic coverage</td><td>≥80% annotated-edge coverage without requiring the amount baseline to emit a pattern name; report separately from typed recovery.</td><td><span class="badge badge-neutral">Not evaluated</span></td></tr><tr><td>Matched-volume amount comparison</td><td>Per-currency amount diagnostic at matched alert volume. Proposal target: +5 percentage points in typed recovery; development-frozen fraction baseline reported separately.</td><td><span class="badge badge-warm">Target, not result</span></td></tr><tr><td>Coverage & exclusions</td><td>Unambiguous source matches; supported types, sizes and windows. Eligible misses from pruning remain in the denominator. Boundary-spanning, long-cycle and unsupported types are separate.</td><td><span class="badge badge-neutral">No report loaded</span></td></tr></tbody></table></div></section><div class="method-note">${icon('info')}<span>Do not use overall accuracy as the headline metric for a rare-label problem. A successful pipeline run is not proof of detector effectiveness. No project execution or evaluation records were read for this design.</span></div>`;
  }
  function release() {
    const sourceIds = D.cases.flatMap(item => item.edges.map(edge => edge.sourceId));
    const result = M.aggregate(D.q1, state.filters);
    const checks = [
      ['Q1 segment counts reconcile to the selected population', M.sum(result.segments, 'n') === result.n && M.sum(result.segments, 'l') === result.l],
      ['Unique source IDs retained across case fixtures', new Set(sourceIds).size === sourceIds.length],
      ['Every case edge resolves to both account participants', D.cases.every(item => item.edges.every(edge => item.nodes.some(node => node.key === edge.sender) && item.nodes.some(node => node.key === edge.receiver)))],
      ['All case evidence is inside its exclusive-end window', D.cases.every(item => item.edges.every(edge => edge.timestamp >= item.windowStart && edge.timestamp < item.cutoffExclusive))],
    ];
    return `${heading('04 / RELEASE & PROVENANCE', 'One release. One source of truth.', 'Make analytical scope visible — and never mix outputs from different runs.', `<button class="btn" data-action="export-manifest">${icon('download')} Demo manifest</button>`)}
      <div class="section-grid"><section class="panel panel-padding"><div class="section-head"><div><h2>This is a design fixture, not a live release.</h2><p>Identity stays visible across charts, cases and downloads.</p></div><span class="badge badge-neutral">LOCAL ONLY</span></div><div class="provenance-grid">${[
        ['Dataset version', D.identity.dataset], ['Run ID', D.identity.run], ['Analysis ID', D.identity.analysis], ['Source provenance', 'Invented UI fixtures; no original records loaded'], ['Time policy', 'Dataset-local; unspecified timezone'], ['Window convention', '[start, end) — exclusive end'], ['Rule example', '5 counterparties · bounded 2–4 cycles · 7 days'], ['Connection state', 'No AWS, database, account or credential access'],
      ].map(([label, value]) => `<div class="provenance-field"><span>${label}</span><strong>${esc(value)}</strong></div>`).join('')}</div></section><aside class="big-note"><div class="eyebrow">SAFE PUBLICATION / TARGET BEHAVIOUR</div><h2>A failed run should never erase a good view.</h2><p>Production should publish only after preparation, Q1, Q2 and offline evaluation have complete, valid reports.</p><p>Pin every summary query, case bundle and evidence download to one published dataset/run. Keep the previous successful release when a new run fails.</p><p>This prototype does not implement a cloud publisher or prove any deployment state.</p></aside></div>
      <div class="section-grid"><section class="panel panel-padding"><h2>Small checks. Clear boundaries.</h2><p class="text-small" style="margin-top:7px">Computed from invented local fixtures only. These are not project data-quality results.</p><div class="status-list">${checks.map(([label, passed]) => `<div class="check-row">${icon(passed ? 'check' : 'warning')}<span>${label}</span><span class="badge${passed ? '' : ' badge-warm'}">${passed ? 'Fixture pass' : 'Fixture fail'}</span></div>`).join('')}</div><div class="method-note">${icon('info')}<span>These checks exercise the concept’s contracts. Production reports must also reconcile accepted/quarantined rows, join coverage, pruning, runtime and cost.</span></div></section><section class="panel panel-padding"><h2>The intended read path</h2><div class="release-path"><div class="release-step">${icon('file')}Published manifest</div><span class="release-arrow">→</span><div class="release-step">${icon('chart')}Pinned summaries</div><span class="release-arrow">+</span><div class="release-step">${icon('network')}Pinned evidence</div></div><p class="text-small">Athena serves summaries and the case index. Bounded case graphs and full source-linked evidence are retrieved from the matching S3 release. All production integration is outside this design’s scope.</p></section></div>`;
  }
  function showSegment(key) {
    const result = M.aggregate(D.q1, state.filters), segment = result.segments.find(item => item.key === key);
    if (!segment) return;
    const interval = segment.interval;
    const currencyText = state.filters.currency === 'all' ? 'All currencies' : `${state.filters.currency} · ${state.filters.side} side`;
    const paid = M.moneyByCurrency(segment.rows, 'payment'), received = M.moneyByCurrency(segment.rows, 'receiving');
    const moneyList = values => Object.entries(values).map(([currency, atomic]) => `<div class="money-row"><span>${currency}</span><span class="mono">${M.formatMoney(atomic)}</span></div>`).join('');
    showDialog(`<div class="dialog-heading"><div><div class="eyebrow">HISTORICAL SEGMENT / ILLUSTRATIVE</div><h2 id="detail-title">${esc(segment.key)}</h2></div><button class="dialog-close" data-action="close-dialog" aria-label="Close segment details">${icon('close')}</button></div><div class="dialog-body"><span class="badge${segment.supported ? '' : ' badge-warm'}">${segment.supported ? `Sufficient support · N ≥ ${number(Number(state.filters.support))}` : 'Low support · counts shown, risk not ranked'}</span><div class="detail-metrics"><div><span>Transactions · N</span><strong>${number(segment.n)}</strong></div><div><span>Labelled · L</span><strong>${number(segment.l)}</strong></div><div><span>Rate · L / N</span><strong>${pct(segment.rate)}</strong></div></div><div class="detail-row"><span>Selected period / population</span><strong>${M.periods[state.filters.period].label}<br>${currencyText}<br>${esc(state.filters.bank === 'all' ? 'All banks' : `Bank ${state.filters.bank}`)} · ${esc(state.filters.format === 'all' ? 'All formats' : state.filters.format)}</strong></div><div class="detail-row"><span>Baseline rate · same filters</span><strong>${pct(result.baseline)} · ${number(result.l)} / ${number(result.n)}</strong></div><div class="detail-row"><span>Relative lift / baseline</span><strong>${segment.supported ? times(segment.lift) : 'Not ranked — low support'}</strong></div><div class="detail-row"><span>95% descriptive proportion interval</span><strong>${interval ? `${pct(interval[0], 3)} – ${pct(interval[1], 3)}` : 'Unavailable'}</strong></div><p class="text-small" style="font-size:9px">Wilson interval is descriptive. Related transactions limit independence assumptions; it is not a causal confidence claim.</p><div class="money-columns"><div><h3>Paid amounts · by payment currency</h3>${moneyList(paid)}</div><div><h3>Received amounts · by receiving currency</h3>${moneyList(received)}</div></div><div class="callout">${icon('info')}<span>No cross-currency sum or assumed FX conversion. Transferred value is not unique criminal proceeds; funds can be counted again as they move.</span></div><div class="method-note">${icon('layers')}<span>${D.identity.dataset} / ${D.identity.run} / ${D.identity.analysis}. Aggregate fixture, not source-level IBM evidence.</span></div></div>`);
  }
  function showSource(sourceId) {
    const item = selectedCase(), edge = item.edges.find(edge => edge.sourceId === sourceId);
    if (!edge) return;
    const fields = [['Stable source ID', edge.sourceId], ['Original checksum (invented)', edge.sourceChecksum], ['Original 1-based data-record ordinal', edge.sourceRecordOrdinal], ['Sender · raw bank / account', `${edge.rawFromBank} / ${edge.senderAccount}`], ['Receiver · raw bank / account', `${edge.rawToBank} / ${edge.receiverAccount}`], ['Dataset-local event time', edge.timestamp], ['Paid / received', `${edge.amountPaid} ${edge.paymentCurrency} / ${edge.amountReceived} ${edge.receivingCurrency}`], ['Case / evidence role', `${item.id} / core`], ['Release / analysis', `${item.run} / ${item.analysis}`]];
    showDialog(`<div class="dialog-heading"><div><div class="eyebrow">SOURCE RECORD / INVENTED FIXTURE</div><h2 id="detail-title">Transaction #${edge.sourceRecordOrdinal}</h2></div><button class="dialog-close" data-action="close-dialog" aria-label="Close source details">${icon('close')}</button></div><div class="dialog-body">${fields.map(([label, value]) => `<div class="detail-row"><span>${label}</span><strong class="mono" style="overflow-wrap:anywhere;max-width:65%">${esc(value)}</strong></div>`).join('')}<p class="text-small">Source identity uses checksum + original ordinal, not field-value deduplication. These IDs identify invented fixtures only.</p></div>`);
  }
  function showDialog(html) { const dialog = $('#detail-dialog'); dialog.innerHTML = html; dialog.showModal(); }
  function exportQ1() {
    const result = M.aggregate(D.q1, state.filters);
    const columns = ['dataset', 'run', 'analysis', 'fixtureOnly', 'periodStart', 'periodEndExclusive', 'currencySide', 'currency', 'formatFilter', 'bankFilter', 'supportThreshold', 'grain', 'segment', 'n', 'l', 'rate', 'baseline', 'lift', 'supported'];
    const rows = result.segments.map(item => ({ dataset: D.identity.dataset, run: D.identity.run, analysis: D.identity.analysis,
      fixtureOnly: true, periodStart: M.periods[state.filters.period].start, periodEndExclusive: M.periods[state.filters.period].end,
      currencySide: state.filters.side, currency: state.filters.currency, formatFilter: state.filters.format, bankFilter: state.filters.bank,
      supportThreshold: state.filters.support, grain: state.filters.grain, segment: item.key, n: item.n, l: item.l, rate: item.rate,
      baseline: result.baseline, lift: item.supported ? item.lift : null, supported: item.supported }));
    download('TRACE-illustrative-monitoring.csv', M.toCsv(columns, rows), 'text/csv;charset=utf-8');
  }
  const pages = { monitoring, cases, evaluation, release };
  const pageTitles = { monitoring: 'Monitoring overview', cases: 'Connected cases', evaluation: 'Evaluation & coverage', release: 'Release & provenance' };
  function render({ animate = false, focus = false } = {}) {
    $('#main').innerHTML = pages[state.page]();
    $('#main').classList.toggle('page-enter', animate);
    $('#breadcrumb').textContent = pageTitles[state.page];
    document.title = `${pageTitles[state.page]} — TRACE`;
    document.querySelectorAll('.nav-link').forEach(link => {
      const active = link.dataset.page === state.page;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
    });
    if (focus) $('#main').focus({ preventScroll: true });
  }
  function route() {
    const page = location.hash.slice(1) || 'monitoring';
    if (!pages[page]) return;
    state.page = page;
    render({ animate: true, focus: Boolean(location.hash) });
    window.scrollTo({ top: 0, behavior: 'instant' });
  }
  document.addEventListener('change', event => {
    const key = event.target.dataset.filter;
    if (key) {
      const focusKey = key;
      state.filters[key] = key === 'support' ? Number(event.target.value) : event.target.value;
      render();
      document.querySelector(`[data-filter="${focusKey}"]`)?.focus({ preventScroll: true });
    }
    if (event.target.id === 'case-date') { state.caseDate = event.target.value; render(); $('#case-date').focus({ preventScroll: true }); }
  });
  document.addEventListener('input', event => {
    if (event.target.id !== 'case-search') return;
    const position = event.target.selectionStart;
    state.query = event.target.value;
    render();
    $('#case-search').focus({ preventScroll: true });
    $('#case-search').setSelectionRange(position, position);
  });
  document.addEventListener('click', event => {
    const target = event.target.closest('[data-action], [data-segment], [data-grain], [data-type], [data-case], [data-node], [data-source]');
    if (!target) return;
    if (target.dataset.segment) return showSegment(target.dataset.segment);
    if (target.dataset.source) return showSource(target.dataset.source);
    if (target.dataset.grain) { state.filters.grain = target.dataset.grain; render(); document.querySelector(`[data-grain="${state.filters.grain}"]`).focus({ preventScroll: true }); return; }
    if (target.dataset.type) { state.caseType = target.dataset.type; render(); document.querySelector(`[data-type="${state.caseType}"]`).focus({ preventScroll: true }); return; }
    if (target.dataset.case) { state.selectedCase = target.dataset.case; state.selectedNode = null; state.evidencePage = 0; state.graphExpanded = false; render(); document.querySelector(`[data-case="${state.selectedCase}"]`).focus({ preventScroll: true }); return; }
    if (target.dataset.node) {
      state.selectedNode = target.dataset.node;
      document.querySelectorAll('[data-node]').forEach(node => node.classList.toggle('selected', node.dataset.node === state.selectedNode));
      $('#node-inspector').innerHTML = nodeInspector(selectedCase());
      return;
    }
    switch (target.dataset.action) {
      case 'reset': state.filters = { ...initialFilters }; render(); toast('Monitoring filters reset'); break;
      case 'toggle-segments': state.showAllSegments = !state.showAllSegments; render(); document.querySelector('[data-action="toggle-segments"]').focus({ preventScroll: true }); break;
      case 'reset-cases': state.caseType = 'all'; state.caseDate = 'all'; state.query = ''; render(); $('#case-search').focus({ preventScroll: true }); break;
      case 'export-q1': exportQ1(); break;
      case 'close-dialog': $('#detail-dialog').close(); break;
      case 'export-evidence': download(`${selectedCase().id}-illustrative-evidence.csv`, M.evidenceCsv(selectedCase()), 'text/csv;charset=utf-8'); break;
      case 'export-case': download(`${selectedCase().id}-illustrative-case.json`, JSON.stringify({ fixtureOnly: true, ...selectedCase(), displayPolicy: { initialNodes: 10, maximumNodes: 100, maximumLinks: 500, completeEvidenceIncluded: true } }, null, 2), 'application/json'); break;
      case 'export-manifest': download('TRACE-illustrative-manifest.json', JSON.stringify({ ...D.identity, fixtureOnly: true, publishedToCloud: false, evaluation: 'NOT EVALUATED', q1Rows: D.q1.length, caseIds: D.cases.map(item => item.id), generatedBy: 'Local proposal-led design concept' }, null, 2), 'application/json'); break;
      case 'prev-evidence': state.evidencePage = Math.max(0, state.evidencePage - 1); render(); break;
      case 'next-evidence': state.evidencePage += 1; render(); break;
      case 'toggle-graph': state.graphExpanded = !state.graphExpanded; render(); document.querySelector('[data-action="toggle-graph"]').focus({ preventScroll: true }); break;
    }
  });
  document.addEventListener('keydown', event => {
    if ((event.key === 'Enter' || event.key === ' ') && event.target.matches('g[role="button"]')) {
      event.preventDefault(); event.target.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    }
  });
  $('#detail-dialog').addEventListener('click', event => { if (event.target === $('#detail-dialog')) $('#detail-dialog').close(); });
  window.addEventListener('hashchange', route);
  route();
})();
