const test = require('node:test');
const assert = require('node:assert/strict');
const D = require('../data.js');
const M = require('../model.js');
const defaults = { period: 'main', side: 'payment', currency: 'all', format: 'all', bank: 'all', grain: 'format', support: 1000, sort: 'lift' };
const row = overrides => ({ date: '2022-09-01', format: 'ACH', fromBank: '020', toBank: '070', paymentCurrency: 'USD', receivingCurrency: 'EUR', n: 1000, l: 10, paidAtomic: '100000001', receivedAtomic: '99000001', ...overrides });

test('fixtures are unmistakably illustrative and have no production identity', () => {
  assert.match(D.identity.source, /NOT PROJECT RESULTS/);
  assert.match(D.identity.run, /^demo-/);
  assert.match(D.identity.dataset, /^illustrative-/);
});

test('main period excludes September 17 and retains September 16', () => {
  const rows = M.filterRows([row({ date: '2022-08-31' }), row({ date: '2022-09-01' }), row({ date: '2022-09-16' }), row({ date: '2022-09-17' })], defaults);
  assert.deepEqual(rows.map(row => row.date), ['2022-09-01', '2022-09-16']);
});

test('development, holdout and sparse tail have disjoint boundaries', () => {
  const sets = ['development', 'holdout', 'tail'].map(period => new Set(M.filterRows(D.q1, { ...defaults, period }).map(row => row.date)));
  for (let a = 0; a < sets.length; a++) for (let b = a + 1; b < sets.length; b++) assert.equal([...sets[a]].filter(day => sets[b].has(day)).length, 0);
  assert.deepEqual(sets.map(set => set.size), [8, 8, 12]);
});

test('rates use summed counts, never unweighted daily rates', () => {
  const result = M.aggregate([row({ n: 1000, l: 100 }), row({ date: '2022-09-02', n: 9000, l: 0 })], defaults);
  assert.equal(result.baseline, 0.01);
  assert.equal(result.segments[0].rate, 0.01);
  assert.notEqual(result.baseline, 0.05);
});

test('payment currency filters N, L, baseline and support together', () => {
  const rows = [row({ n: 100, l: 10 }), row({ n: 5000, l: 50, paymentCurrency: 'EUR', receivingCurrency: 'USD' })];
  const result = M.aggregate(rows, { ...defaults, currency: 'USD' });
  assert.equal(result.n, 100); assert.equal(result.l, 10); assert.equal(result.baseline, 0.1);
  assert.equal(result.segments[0].supported, false);
});

test('receiving currency filters the opposite dimension, including denominators', () => {
  const rows = [row({ n: 100, l: 10 }), row({ n: 5000, l: 50, paymentCurrency: 'EUR', receivingCurrency: 'USD' })];
  const result = M.aggregate(rows, { ...defaults, currency: 'USD', side: 'receiving' });
  assert.equal(result.n, 5000); assert.equal(result.l, 50); assert.equal(result.baseline, 0.01);
  assert.equal(result.segments[0].supported, true);
});

test('bank and format restrictions apply before the baseline', () => {
  const rows = [row({ n: 1000, l: 100 }), row({ n: 9000, l: 0, format: 'Wire' }), row({ n: 10000, l: 0, fromBank: '008381', toBank: '011' })];
  const result = M.aggregate(rows, { ...defaults, format: 'ACH', bank: '070' });
  assert.equal(result.n, 1000); assert.equal(result.baseline, 0.1);
});

test('each grain reconciles to one population without overlapping sums', () => {
  for (const grain of ['format', 'pair']) {
    const result = M.aggregate(D.q1, { ...defaults, grain });
    assert.equal(M.sum(result.segments, 'n'), result.n);
    assert.equal(M.sum(result.segments, 'l'), result.l);
    assert.equal(result.baseline, result.l / result.n);
    assert.ok(result.segments.every(segment => segment.n >= segment.l));
  }
});

test('supported segments precede low support; low support ordered by count, not risk', () => {
  const result = M.aggregate([row({ format: 'A', n: 1500, l: 1 }), row({ format: 'B', n: 50, l: 45 }), row({ format: 'C', n: 100, l: 1 })], defaults);
  assert.deepEqual(result.segments.map(segment => segment.key), ['A', 'C', 'B']);
  assert.deepEqual(result.segments.map(segment => segment.supported), [true, false, false]);
});

test('support is evaluated after summing selected dates', () => {
  const result = M.aggregate([row({ n: 600 }), row({ date: '2022-09-02', n: 600 })], defaults);
  assert.equal(result.segments[0].supported, true);
});

test('zero baseline produces no infinite or misleading lift', () => {
  const result = M.aggregate([row({ l: 0 })], defaults);
  assert.equal(result.baseline, 0); assert.equal(result.segments[0].lift, null);
  assert.equal(M.lift(0, 0), null);
});

test('an empty population has no rate or lift', () => {
  const result = M.aggregate([], defaults);
  assert.equal(result.n, 0); assert.equal(result.l, 0); assert.equal(result.baseline, null);
  assert.deepEqual(result.segments, []);
});

test('unknown periods fail explicitly', () => assert.throws(() => M.filterRows(D.q1, { period: 'unknown' }), /Unknown reporting period/));

test('exact paid and received totals stay separate by their respective currencies', () => {
  const rows = [row({ paidAtomic: '900719925474099312345678', receivedAtomic: '123456789' }), row({ paidAtomic: '3', receivedAtomic: '1' }), row({ paymentCurrency: 'GBP', receivingCurrency: 'USD', paidAtomic: '4', receivedAtomic: '5' })];
  assert.deepEqual(M.moneyByCurrency(rows, 'payment'), { USD: 900719925474099312345681n, GBP: 4n });
  assert.deepEqual(M.moneyByCurrency(rows, 'receiving'), { EUR: 123456790n, USD: 5n });
});

test('money formatting preserves up to eight decimal places beyond Number precision', () => {
  assert.equal(M.formatMoney('900719925474099312345678'), '9,007,199,254,740,993.12345678');
  assert.equal(M.formatMoney('1'), '0.00000001');
  assert.equal(M.formatMoney('123000000'), '1.23');
  assert.equal(M.formatMoney('-123000001'), '-1.23000001');
});

test('descriptive intervals include the observed proportion and stay bounded', () => {
  for (const [l, n] of [[0, 100], [100, 100], [10, 1000], [1, 1]]) {
    const interval = M.wilson(l, n);
    assert.ok(interval[0] >= 0 && interval[1] <= 1);
    assert.ok(interval[0] <= l / n + 1e-12 && interval[1] >= l / n - 1e-12);
  }
  assert.equal(M.wilson(0, 0), null);
});

test('case generation fixtures contain no labels, Q1 scores, or evaluation answers', () => {
  const keys = new Set();
  function visit(value) { if (!value || typeof value !== 'object') return; for (const [key, item] of Object.entries(value)) { keys.add(key); visit(item); } }
  visit(D.cases);
  for (const key of keys) assert.doesNotMatch(key, /launder|label|risk|score|annotation|precision|recall|recovery/i);
});

test('all evidence has stable checksum + 1-based ordinal identities and no self motif', () => {
  const ids = new Set();
  for (const item of D.cases) for (const edge of item.edges) {
    assert.match(edge.sourceChecksum, /^[a-f0-9]{64}$/);
    assert.ok(edge.sourceRecordOrdinal >= 1);
    assert.equal(edge.sourceId, `${edge.sourceChecksum}:${edge.sourceRecordOrdinal}`);
    assert.notEqual(edge.sender, edge.receiver);
    assert.ok(!ids.has(edge.sourceId)); ids.add(edge.sourceId);
  }
});

test('evidence preserves distinct parallel transactions rather than deduplicating fields', () => {
  const item = D.cases[0], graph = M.boundedGraph(item);
  assert.equal(graph.edges.length, 6);
  assert.equal(graph.visibleTransactions, 18);
  assert.equal(new Set(item.edges.map(edge => edge.sourceId)).size, 18);
});

test('complete evidence stays inside exclusive-end snapshots', () => {
  for (const item of D.cases) for (const edge of item.edges) {
    assert.ok(edge.timestamp >= item.windowStart && edge.timestamp < item.cutoffExclusive);
    assert.ok(item.nodes.some(node => node.key === edge.sender));
    assert.ok(item.nodes.some(node => node.key === edge.receiver));
  }
});

test('fan rules have at least five distinct non-self counterparties', () => {
  for (const item of D.cases.filter(item => item.type !== 'Cycle')) {
    const counterparts = new Set(item.edges.map(edge => item.type === 'Fan-in' ? edge.sender : edge.receiver));
    assert.ok(counterparts.size >= 5);
    assert.equal(counterparts.size, item.nodes.length - 1);
  }
});

test('unknown entity mapping is explicit and the account remains in the case', () => {
  const item = D.cases[0], unknown = item.nodes.find(node => node.entityId === null);
  assert.ok(unknown); assert.equal(unknown.entityName, 'Unknown entity');
  assert.ok(item.edges.some(edge => edge.sender === unknown.key || edge.receiver === unknown.key));
});

test('the graph cap never alters full evidence or participants', () => {
  const item = D.cases[3], before = JSON.stringify(item);
  const graph = M.boundedGraph(item, 100, 500);
  assert.equal(graph.nodes.length, 100); assert.equal(graph.hiddenNodes, 4); assert.equal(graph.capped, true);
  assert.ok(graph.visibleTransactions < item.edges.length);
  assert.equal(item.edges.length, 124); assert.equal(item.nodes.length, 104);
  assert.equal(JSON.stringify(item), before);
});

test('the link cap is independent of node cap', () => {
  const graph = M.boundedGraph(D.cases[0], 100, 2);
  assert.equal(graph.edges.length, 2); assert.equal(graph.nodes.length, 7); assert.equal(graph.capped, true);
});

test('case filtering supports type, snapshot, account, entity and empty results', () => {
  assert.equal(M.filterCases(D.cases, { type: 'Cycle' }).length, 1);
  assert.equal(M.filterCases(D.cases, { date: '2022-09-16' }).length, 2);
  assert.equal(M.filterCases(D.cases, { query: 'demo000100' })[0].id, 'DEMO-FO-001');
  assert.equal(M.filterCases(D.cases, { query: 'DEMO-E201' })[0].id, 'DEMO-FI-002');
  assert.equal(M.filterCases(D.cases, { query: 'no-such-record' }).length, 0);
});

test('CSV export includes complete evidence even when a graph is capped', () => {
  const item = D.cases[3], csv = M.evidenceCsv(item), lines = csv.trim().split('\r\n');
  assert.equal(lines.length, item.edges.length + 1);
  for (const edge of item.edges) assert.ok(csv.includes(edge.sourceId));
  for (const identity of [item.dataset, item.run, item.analysis, item.ruleId, item.windowStart, item.cutoffExclusive]) assert.ok(csv.includes(identity));
  assert.ok(csv.includes('1250.00000000'));
});

test('CSV values are quoted and escaped; spreadsheet formulas are neutralised', () => {
  const csv = M.toCsv(['value'], [{ value: 'a,"b"' }, { value: '=1+1' }, { value: '@SUM(A1)' }]);
  assert.ok(csv.includes('"a,""b"""'));
  assert.ok(csv.includes('"\'=1+1"')); assert.ok(csv.includes('"\'@SUM(A1)"'));
});
