# TRACE · AML intelligence workspace

An **independent, proposal-led dashboard concept** for the two business questions in [`Proposal/Project_Proposal.md`](../Proposal/Project_Proposal.md). It is a working visual prototype, not a production dashboard or a report of project results.

## Open the dashboard

**Double-click [`index.html`](index.html)**. No installation, account, internet access or build step is required. Keep `index.html`, `styles.css`, `data.js`, `model.js` and `app.js` together.

Alternatively, from this folder:

```sh
python3 -m http.server 5387 --bind 127.0.0.1
```

Visit **http://127.0.0.1:5387**. Stop the optional local server with **Ctrl+C**.

## Four views

| View | The decision it supports |
| --- | --- |
| **Monitoring overview** | Compare transaction volume with supported historical labelled rate/lift. Inspect payment formats and bank-pair/format segments. |
| **Connected cases** | Explore fan-in, fan-out and short-cycle structures; inspect accounts/entities and retrieve source-linked evidence. |
| **Evaluation & coverage** | Understand chronological evaluation, denominators, proposal targets and limitations. Metrics are deliberately **not evaluated**, not fabricated. |
| **Release & provenance** | See the dataset/run/analysis identity, fixture checks and intended single-release read policy. |

### Try this

1. On **Monitoring overview**, inspect ACH. Compare its share of traffic with its share of historical labels. Open its details to see denominators, descriptive intervals and separate paid/received currency totals.
2. Select **USD**, then switch **Payment currency** to **Receiving currency**. Counts, rate, support and the baseline all recompute.
3. Switch to **Bank pair + format**, then **Show all segments**. Low-support segments show counts and a warning instead of ranked lift.
4. Select **17–28 Sep** to see the sparse-tail warning. It is never blended into the default main period.
5. Open **Connected cases**. Select an account or source ordinal; try the fan-in and cycle filters.
6. Open **A wider distribution network**. Expand to the 100-node cap, then download **All 124 records** or the JSON case bundle. Hidden evidence is still included.
7. Search for a nonexistent case to test the empty state, then clear the filters.

## Files

- [`DESIGN_GUIDE.md`](DESIGN_GUIDE.md) — visual direction, screen layouts, requirement mapping and production handoff.
- [`TESTING.md`](TESTING.md) — checks actually run, results and limitations.
- `index.html` / `styles.css` / `app.js` — responsive, interactive interface.
- `data.js` — deterministic, **invented** aggregate/case fixtures; no original dataset records.
- `model.js` — pure filtering, aggregation, exact money formatting, graph bounds and CSV helpers.
- `tests/model.test.cjs` — dependency-free local contract tests.

Run the model tests with Node.js 20+:

```sh
node --test tests/model.test.cjs
```

With the optional server running, open **http://127.0.0.1:5387/tests/browser-smoke.html** for the reproducible browser checks. Final local results: **27 model tests + 41 browser checks passed**.

## Deliberate boundaries

- The original design was based on the proposal and its pipeline explanation, **not on the existing implementation or GitHub**. The root README was read for required repository orientation only. The subsequent team-publication task adds repository links/handoffs without changing that design basis.
- Every count, case, account, entity, source checksum and monetary value in this prototype is an invented design fixture. They do not reproduce the proposal’s measured data profile.
- There is no AWS/API/database integration, authentication, detector, evaluation execution or cloud publication. No cloud resources are created or billed.
- Q1 uses historical labels. Q2 fixtures do not contain labels or Q1 risk scores. Client-side separation illustrates the workflow; it is **not** a production security boundary.
- Exports are local fixture downloads. The source-ID format illustrates traceability; it does not point to real IBM records.
- The design preserves the distinction between **historical exposure**, **structural investigation leads**, and **offline performance evaluation**.

The unusual folder spelling, `Visulization`, is kept exactly as requested.
