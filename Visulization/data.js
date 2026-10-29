/* Entirely invented UI fixtures. These are not IBM records or measured results. */
(function (root, factory) {
  const data = factory();
  if (typeof module === 'object' && module.exports) module.exports = data;
  else root.TraceData = data;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const identity = Object.freeze({
    dataset: 'illustrative-hi-medium-v1',
    run: 'demo-release-01',
    analysis: 'proposal-ui-v1',
    source: 'INVENTED UI FIXTURES — NOT PROJECT RESULTS',
    timePolicy: 'Dataset-local time; timezone unspecified; exclusive window end',
  });
  const formats = [
    { name: 'ACH', base: 18200, rate: 0.0078, color: '#256653' },
    { name: 'Wire', base: 43000, rate: 0.00034, color: '#98aaa3' },
    { name: 'Cheque', base: 12500, rate: 0.00125, color: '#7d91af' },
    { name: 'Credit Card', base: 51600, rate: 0.00012, color: '#bbc5bd' },
    { name: 'Cash', base: 28000, rate: 0.00055, color: '#b69771' },
    { name: 'Reinvestment', base: 36300, rate: 0.00008, color: '#c9cdbd' },
    { name: 'Bitcoin', base: 2700, rate: 0.0034, color: '#d18955' },
  ];
  const pairs = [
    { from: '020', to: '070', factor: 1, exposure: 1.7 },
    { from: '070', to: '008381', factor: 0.72, exposure: 1 },
    { from: '011', to: '020', factor: 0.49, exposure: 0.85 },
    { from: '008381', to: '011', factor: 0.31, exposure: 0.5 },
  ];
  const currencies = ['USD', 'EUR', 'GBP'];
  const shares = [0.55, 0.30, 0.15];
  const q1 = [];
  for (let day = 1; day <= 28; day++) {
    formats.forEach((format, fi) => pairs.forEach((pair, pi) => currencies.forEach((currency, ci) => {
      const tail = day >= 17;
      const wave = 0.93 + ((day * 7 + fi * 3 + pi) % 17) / 70;
      const small = fi === 6 && pi === 3 ? 0.012 : 1;
      const n = Math.max(1, Math.round(format.base * pair.factor * shares[ci] * wave * small * (tail ? 0.00045 : 1)));
      const l = Math.min(n, Math.round(n * (tail ? 0.34 + fi * 0.035 : format.rate * pair.exposure * (0.9 + ci * 0.13))));
      const averageCents = BigInt(24500 + fi * 35400 + pi * 7100 + ci * 2300 + day * 13);
      const paid = (BigInt(n) * averageCents * 1000000n).toString();
      const received = (BigInt(paid) * BigInt(ci === 1 ? 91 : 99) / 100n).toString();
      q1.push({
        ...identity, date: `2022-09-${String(day).padStart(2, '0')}`,
        fromBank: pair.from, toBank: pair.to, format: format.name,
        paymentCurrency: currency,
        receivingCurrency: (day + fi + pi) % 5 === 0 ? currencies[(ci + 1) % 3] : currency,
        n, l, paidAtomic: paid, receivedAtomic: received,
      });
    })));
  }

  // Q2 uses separate, label-free fixtures. No Q1 scores or evaluation references.
  const sourceChecksum = 'd3a0c3e5f11629b8a6e04d9275c1fa63b2d8e6109c47a3f50e12b8a694dc0721';
  const account = (i, entity) => ({
    key: `${20 + (i % 4)}:DEMO${String(i).padStart(6, '0')}`,
    rawBank: `0${20 + (i % 4)}`, bank: String(20 + (i % 4)),
    account: `DEMO${String(i).padStart(6, '0')}`,
    entityId: entity === null ? null : `DEMO-E${entity || i}`,
    entityName: entity === null ? 'Unknown entity' : `Illustrative entity ${entity || i}`,
  });
  function makeCase({ id, type, size, transactions, title, startIndex, day, description }) {
    const nodes = Array.from({ length: size }, (_, i) => account(startIndex + i, i === 2 ? startIndex + 1 : i === 4 ? null : startIndex + i));
    const edges = [];
    for (let i = 0; i < transactions; i++) {
      const other = 1 + i % (size - 1);
      const from = type === 'Fan-in' ? nodes[other] : type === 'Cycle' ? nodes[i % size] : nodes[0];
      const to = type === 'Fan-in' ? nodes[0] : type === 'Cycle' ? nodes[(i + 1) % size] : nodes[other];
      const ordinal = startIndex * 100 + i + 1;
      edges.push({
        sourceId: `${sourceChecksum}:${ordinal}`, sourceChecksum, sourceRecordOrdinal: ordinal,
        sender: from.key, receiver: to.key,
        rawFromBank: from.rawBank, rawToBank: to.rawBank,
        senderAccount: from.account, receiverAccount: to.account,
        timestamp: `2022-09-${String(day - 2 + Math.floor(i / Math.max(1, Math.ceil(transactions / 3)))).padStart(2, '0')}T${String(9 + i % 9).padStart(2, '0')}:${String(i * 7 % 60).padStart(2, '0')}:00`,
        amountPaid: `${1250 + i * 173}.00000000`, paymentCurrency: i % 4 === 3 ? 'EUR' : 'USD',
        amountReceived: `${1245 + i * 173}.00000000`, receivingCurrency: i % 4 === 3 ? 'EUR' : 'USD',
        format: i % 3 === 0 ? 'Wire' : 'ACH', role: 'core',
      });
    }
    return {
      ...identity, id, title, type, description, nodes, edges,
      ruleId: type === 'Cycle' ? 'demo-cycle-2-to-4-v1' : `demo-${type.toLowerCase()}-5-v1`,
      windowStart: `2022-09-${String(day - 6).padStart(2, '0')}T00:00:00`,
      cutoffExclusive: `2022-09-${String(day + 1).padStart(2, '0')}T00:00:00`,
      lookbackDays: 7, snapshotDate: `2022-09-${String(day).padStart(2, '0')}`,
      history: 'Insufficient history for a behavioural-change comparison',
      chronology: type === 'Cycle' ? 'Not assessed. Structural closure does not establish chronological return of funds.' : null,
    };
  }
  const cases = [
    makeCase({ id: 'DEMO-FO-001', type: 'Fan-out', size: 7, transactions: 18, startIndex: 100, day: 16,
      title: 'One hub. Six destinations.', description: 'Six distinct non-self receiving accounts are linked to one sending hub within the snapshot window.' }),
    makeCase({ id: 'DEMO-FI-002', type: 'Fan-in', size: 6, transactions: 12, startIndex: 200, day: 15,
      title: 'A shared collection point.', description: 'Five distinct non-self sending accounts pay into one receiving hub within the snapshot window.' }),
    makeCase({ id: 'DEMO-CY-003', type: 'Cycle', size: 3, transactions: 6, startIndex: 300, day: 14,
      title: 'Three accounts. A closed loop.', description: 'Three distinct accounts form a closed directed structure. Transaction ordering requires a separate assessment.' }),
    makeCase({ id: 'DEMO-FO-004', type: 'Fan-out', size: 104, transactions: 124, startIndex: 400, day: 16,
      title: 'A wider distribution network.', description: '103 non-self counterparties meet the fan-out rule. This fixture demonstrates a bounded graph with complete downloadable evidence.' }),
  ];
  return Object.freeze({ identity, formats, pairs, currencies, q1, cases, sourceChecksum });
});
