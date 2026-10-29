(function (root, factory) {
  const model = factory();
  if (typeof module === 'object' && module.exports) module.exports = model;
  else root.TraceModel = model;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const periods = Object.freeze({
    main: { label: '01–16 Sep 2022', start: '2022-09-01', end: '2022-09-17', note: 'Main reporting period' },
    development: { label: '01–08 Sep 2022', start: '2022-09-01', end: '2022-09-09', note: 'Development period' },
    holdout: { label: '09–16 Sep 2022', start: '2022-09-09', end: '2022-09-17', note: 'Holdout period' },
    tail: { label: '17–28 Sep 2022', start: '2022-09-17', end: '2022-09-29', note: 'Sparse tail · not comparable with main activity' },
  });
  const sum = (rows, key) => rows.reduce((n, row) => n + row[key], 0);
  const rate = (l, n) => n ? l / n : null;
  const lift = (segmentRate, baseline) => segmentRate !== null && baseline > 0 ? segmentRate / baseline : null;
  function filterRows(rows, filters) {
    const period = periods[filters.period || 'main'];
    if (!period) throw new Error('Unknown reporting period');
    const side = filters.side === 'receiving' ? 'receivingCurrency' : 'paymentCurrency';
    return rows.filter(row => row.date >= period.start && row.date < period.end
      && (!filters.currency || filters.currency === 'all' || row[side] === filters.currency)
      && (!filters.format || filters.format === 'all' || row.format === filters.format)
      && (!filters.bank || filters.bank === 'all' || row.fromBank === filters.bank || row.toBank === filters.bank));
  }
  function wilson(l, n) {
    if (!n) return null;
    const z = 1.96, p = l / n, den = 1 + z * z / n;
    const middle = (p + z * z / (2 * n)) / den;
    const delta = z * Math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den;
    return [Math.max(0, middle - delta), Math.min(1, middle + delta)];
  }
  function moneyByCurrency(rows, side) {
    const amountKey = side === 'receiving' ? 'receivedAtomic' : 'paidAtomic';
    const currencyKey = side === 'receiving' ? 'receivingCurrency' : 'paymentCurrency';
    const result = {};
    for (const row of rows) result[row[currencyKey]] = (result[row[currencyKey]] || 0n) + BigInt(row[amountKey]);
    return result;
  }
  function aggregate(rows, filters) {
    const population = filterRows(rows, filters);
    const n = sum(population, 'n'), l = sum(population, 'l'), baseline = rate(l, n);
    const map = new Map();
    for (const row of population) {
      const key = filters.grain === 'pair' ? `${row.fromBank} → ${row.toBank} · ${row.format}` : row.format;
      if (!map.has(key)) map.set(key, { key, format: row.format, fromBank: row.fromBank, toBank: row.toBank, rows: [], n: 0, l: 0 });
      const segment = map.get(key);
      segment.n += row.n;
      segment.l += row.l;
      segment.rows.push(row);
    }
    const segments = [...map.values()].map(segment => ({ ...segment,
      rate: rate(segment.l, segment.n), lift: lift(rate(segment.l, segment.n), baseline),
      supported: segment.n >= Number(filters.support || 1000), interval: wilson(segment.l, segment.n),
      trafficShare: n ? segment.n / n : 0, labelShare: l ? segment.l / l : 0,
    })).sort((a, b) => Number(b.supported) - Number(a.supported)
      || (!a.supported || filters.sort === 'volume' ? b.n - a.n : (b.lift || 0) - (a.lift || 0)) || a.key.localeCompare(b.key));
    return { population, n, l, baseline, segments, paid: moneyByCurrency(population, 'payment'), received: moneyByCurrency(population, 'receiving') };
  }
  function formatMoney(atomic) {
    const value = BigInt(atomic), negative = value < 0n, abs = negative ? -value : value;
    const units = abs / 100000000n;
    const fraction = (abs % 100000000n).toString().padStart(8, '0');
    const significant = fraction.slice(2).replace(/0+$/, '');
    return `${negative ? '-' : ''}${units.toLocaleString('en-US')}.${fraction.slice(0, 2)}${significant}`;
  }
  function boundedGraph(caseData, maxNodes = 100, maxEdges = 500) {
    const nodes = caseData.nodes.slice(0, Math.max(0, maxNodes));
    const keys = new Set(nodes.map(node => node.key));
    const links = new Map();
    for (const edge of caseData.edges) {
      if (!keys.has(edge.sender) || !keys.has(edge.receiver)) continue;
      const key = `${edge.sender}|${edge.receiver}`;
      if (!links.has(key)) links.set(key, { sender: edge.sender, receiver: edge.receiver, sourceIds: [] });
      links.get(key).sourceIds.push(edge.sourceId);
    }
    const edges = [...links.values()].slice(0, Math.max(0, maxEdges));
    return { nodes, edges, hiddenNodes: caseData.nodes.length - nodes.length,
      visibleTransactions: edges.reduce((n, edge) => n + edge.sourceIds.length, 0),
      capped: caseData.nodes.length > nodes.length || caseData.edges.length > edges.reduce((n, edge) => n + edge.sourceIds.length, 0) };
  }
  function filterCases(cases, { type = 'all', date = 'all', query = '' } = {}) {
    const needle = query.trim().toLowerCase();
    return cases.filter(item => (type === 'all' || item.type === type) && (date === 'all' || item.snapshotDate === date)
      && (!needle || [item.id, item.title, item.type, ...item.nodes.flatMap(node => [node.account, node.bank, node.entityId || 'unknown'])].join(' ').toLowerCase().includes(needle)));
  }
  const csvCell = value => {
    let text = String(value ?? '');
    if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
    return `"${text.replace(/"/g, '""')}"`;
  };
  function toCsv(columns, rows) {
    return [columns.map(csvCell).join(','), ...rows.map(row => columns.map(key => csvCell(row[key])).join(','))].join('\r\n') + '\r\n';
  }
  function evidenceCsv(caseData) {
    const columns = ['dataset', 'run', 'analysis', 'caseId', 'ruleId', 'windowStart', 'cutoffExclusive', 'sourceId', 'sourceChecksum', 'sourceRecordOrdinal',
      'timestamp', 'sender', 'receiver', 'rawFromBank', 'rawToBank', 'senderAccount', 'receiverAccount',
      'amountPaid', 'paymentCurrency', 'amountReceived', 'receivingCurrency', 'format', 'role'];
    return toCsv(columns, caseData.edges.map(edge => ({ ...edge, dataset: caseData.dataset, run: caseData.run, analysis: caseData.analysis,
      caseId: caseData.id, ruleId: caseData.ruleId, windowStart: caseData.windowStart, cutoffExclusive: caseData.cutoffExclusive })));
  }
  return Object.freeze({ periods, sum, rate, lift, filterRows, aggregate, wilson, moneyByCurrency, formatMoney, boundedGraph, filterCases, toCsv, evidenceCsv });
});
