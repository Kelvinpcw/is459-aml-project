# TRACE — dashboard design proposal

## 1. Design intent

**A calm investigation workspace, not a wall of alarms.**

The proposal asks two different people to make two different decisions. The interface should make that separation immediately understandable:

1. **Compliance management:** Where does historical labelled exposure justify a closer review of monitoring controls?
2. **Investigation:** Which connected account structures deserve examination, and what transactions explain them?

Neither screen should say “criminal”, “confirmed laundering”, “unsafe bank” or “real-time threat”. The source is synthetic and the analytical claims are narrower than those labels.

### Visual direction

| Element | Choice | Why |
| --- | --- | --- |
| Product identity | **TRACE** | Emphasises following explainable evidence rather than predicting guilt. |
| Canvas | Warm off-white `#F5F6F2` | A quieter surface for dense analytical work. |
| Primary ink | Charcoal `#202C29` | Strong hierarchy without an all-black security-console aesthetic. |
| Core accent | Forest `#123D32`, green `#256653` | Stable navigation, selected objects and investigation focus. |
| Highlight | Pale lime `#DCF1B3` | Draws attention to the explanatory takeaway, not an arbitrary danger score. |
| Warnings | Amber with text | Low support and sparse-tail context are cautions, not verdicts. |
| Pattern distinction | Named badges; muted green/amber/violet | Pattern categories are not severity rankings. Never rely on colour alone. |
| Typography | Locally available Avenir Next / system sans; monospaced identifiers | No remote font requests; numbers and evidence keys stay easy to scan. |
| Components | Thin borders, restrained radii, generous spacing | A credible operational tool rather than a decorative marketing page. |
| Motion | Short page entrance; reduced-motion support | Orientation without distracting chart animation. |

The dark insight card is intentionally the only large, high-contrast surface on the management page. It explains the main takeaway in a sentence, while the adjacent plot and table let the user challenge it.

## 2. Information architecture

```text
Persistent sidebar                Main workspace
─────────────────────             ──────────────────────────────────────
TRACE                             Breadcrumb       Dataset / demo release
                                  Persistent illustrative-data notice
01 Monitoring overview
02 Connected cases                Page title + analytical purpose
03 Evaluation & coverage          Page-specific controls
04 Release & provenance           Summaries → visual explanation → evidence
                                  Time policy / caveats
```

**Persistent identity:** The release link is visible on every screen. In a production version, the active dataset version, run and analytical scope must remain available without inspecting a developer console. Every download includes identity metadata.

**No automatic Q1 → Q2 risk transfer:** Navigation to Connected cases starts an independent label-free workspace. A high historical bank-pair rate must not silently become a detector score, filter or participant seed. The prototype does not claim browser-side code provides IAM isolation.

## 3. Screen 01 — Monitoring overview

### Purpose

Let a manager explain three sufficiently supported monitoring priorities using both rate and volume, rather than reviewing the busiest segments alone.

### Layout

```text
Monitoring overview                                  Export summary
See where historical exposure outweighs transaction volume.

[Period] [Currency dimension] [Currency] [Format] [Bank involved] [Reset]

[Transactions N] [Historical labels L] [Labelled rate L/N] [Supported priorities]

┌─────────────────────────────────────┐  ┌───────────────────────────┐
│ Volume versus labelled-rate plot    │  │ A monitoring lead,        │
│                                     │  │ explained                 │
│ y = selected-period labelled rate   │  │                           │
│ x = transaction count               │  │ 7.3× baseline (demo)      │
│ area approximately labelled count   │  │ Traffic share vs label    │
│ dashed selected baseline            │  │ share + inspect action    │
└─────────────────────────────────────┘  └───────────────────────────┘

[Formats | Bank pair + format] [Minimum support] [Rank by lift / volume]
Segment     N       L       Rate       Lift       Traffic share       Support
...

Selected segment dialog → denominator, baseline, interval, paid/received amounts
```

### Control semantics

- **Default period:** 1–16 September 2022. Development 1–8, holdout 9–16 and sparse tail 17–28 are explicit alternatives. No blended full-file headline.
- **Default currency dimension:** Payment Currency. Receiving Currency is an explicit alternative. All currencies is the initial count/rate population; it does **not** produce a summed monetary value.
- **Currency changes apply everywhere:** N, L, support, baseline and relative lift are all computed from the same filtered population. The proposal’s combined two-sided currency filter is optional future work, not implemented here.
- **Bank involved:** Includes either sending or receiving bank, clearly named. The bank-pair/format grain preserves direction. Production could add separate sender/receiver controls if user testing requires them.
- **Support:** Starts at N ≥ 1,000, with 100/500 sensitivity options. The threshold changes eligibility for ranked interpretation, not the baseline population.
- **Grain:** Formats and bank-pair/format segments are alternative views of the same underlying counts. Never add their totals together.
- **Ranking:** Supported segments first, then lift or volume. Low-support records remain inspectable as counts with warnings, ordered by count rather than purported risk. Use Show all to reach the full table.
- **Relative-lift comparison:** Segment rate divided by the selected-population rate. A zero or absent baseline yields unavailable lift, never infinity.
- **Dates:** Sum N and L across the selection, then compute L/N. Do not average daily percentages.

### Why this chart?

A volume–rate scatter plot exposes the central management trade-off: a small or medium segment may sit much higher on labelled rate than the largest payment category. A plain volume bar chart cannot show that relationship on its own.

The bubble area is approximately proportional to L (a minimum visible radius is added). The baseline is not a separate comparison period: it is the filtered population’s own rate. Exact N/L/rate/lift values are always available in the table and inspection dialog. No artificial trend arrows are shown; the small sparkline represents only the fixture’s daily volume.

### Segment inspection

- Segment N, L, rate and eligibility.
- Explicit filtered denominator and baseline rate.
- 95% Wilson descriptive proportion interval with a related-transactions caveat.
- Paid totals grouped by Payment Currency.
- Received totals grouped by Receiving Currency.
- No all-currency monetary total, assumed FX equality or “criminal proceeds” total.
- Dataset/run/analysis identity and fixture label.

## 4. Screen 02 — Connected cases

### Purpose

Let an investigator explain a case and retrieve its complete supporting records without writing SQL.

```text
Follow the connections.                              Label-free case fixtures
[Search case / account / entity] [All | Fan-in | Fan-out | Cycle] [Snapshot]

Case queue                    Selected case / rule version         Bundle ↓
┌───────────────────┐         Snapshot / seven-day window / exclusive cutoff
│ Pattern + case ID │         ┌─────────────────────────┬──────────────────┐
│ Structural title  │         │ Directed account graph  │ Selected account │
│ Accounts / tx     │         │ Shared-entity grouping  │ Bank + account   │
└───────────────────┘         │ Parallel links counted  │ Entity / unknown │
...                           └─────────────────────────┴──────────────────┘
                              Why this rule triggered
                              Complete evidence table            CSV ↓
                              Source IDs / times / endpoints / paid & received
```

### Graph grammar

- **Node:** A normalised bank/account pair, never account number alone.
- **Arrow:** Payment direction. Parallel transactions share a visual link while retaining every source ID. A link count says how many core transactions it represents.
- **Hub:** A filled central node for fan patterns. Fan-in arrows point inward; fan-out arrows point outward.
- **Dashed shared-entity enclosure:** Static entity membership; accounts remain separate. Missing mappings are explicitly Unknown and never silently dropped.
- **Selected account:** A highlighted node plus a contextual inspector. This shows incoming/outgoing core counts, raw bank identifier, normalised key and entity information.
- **Core evidence:** All links in the prototype are core motif evidence. Optional surrounding-context edges are not invented or mixed into the rule denominator. A production extension should use a distinctly dashed/grey link type and separate core/context counts.
- **No red “bad account” nodes, label-derived ranking, sanctions flags, geographic risk, confidence percentage or hidden ML score.** Those are not supported by the proposal.

### Bounded display, complete case

The default fixture view is intentionally compact: up to ten nodes. A wider network can expand to the proposal’s 100-node / 500-link cap. The cap applies only to display, not the participant list or full evidence.

The interface must show **visible / total** accounts and transactions. All evidence remains available through pagination, full CSV and full JSON bundle export. The 104-account fixture demonstrates this distinction. It is not a performance benchmark.

### Rule and time explanation

- Fan-in/out: at least five distinct non-self counterparties in the configured window.
- Cycle: a closed directed structure across 2–4 distinct accounts. The fixture uses three.
- Show rule ID, snapshot date, lookback and `[window_start, cutoff_exclusive)` in dataset-local time.
- Show insufficient-history context when a change-from-baseline explanation is unavailable.
- Self-transfers remain in stored source data but are excluded from motif edges.
- A structural cycle is not necessarily a chronological transfer path or evidence that identical funds returned.
- Production cycle coverage must disclose degree-64 eligibility/pruning from the proposal’s frozen protocol, rather than imply exhaustive traversal. This UI contains no detector.

### Evidence interaction

Selecting a source ordinal opens its complete invented checksum + original one-based record ordinal, raw endpoints, timestamp, paid/received amounts and currencies, case ID, rule and release identity. The full export preserves exact eight-decimal strings and every distinct record. Spreadsheet-sensitive CSV values are neutralised.

The visual ordinal is a shortened display, not a replacement identity. No source record is deduplicated merely because its fields resemble another payment.

## 5. Screen 03 — Evaluation & coverage

**Separate from investigation.** The proposal permits labels and annotations only in the offline evaluator, after immutable cases have been generated.

The design shows:

- Transaction precision and recall with their declared eligible denominators.
- Typed attempt recovery: correct pattern and hub/cycle plus ≥80% of matched annotated edges in one case’s core evidence, including hidden graph edges.
- A separately named type-agnostic coverage measure for fair comparison with an amount-only diagnostic.
- A per-currency, matched-alert-volume amount comparison; a development-frozen fraction baseline is reported separately.
- The **+5 percentage-point improvement target** as a proposal target, never an achieved result.
- Development → frozen holdout → separately reported sparse tail.
- Coverage/exclusions: supported types/sizes/windows, ambiguous matches, long cycles, boundary-spanning attempts and pruning. Eligible missed attempts stay in the denominator.

All performance values are **Not evaluated / —**. The concept has no reference report and must not fill the gap with plausible-looking percentages. Incomplete annotations are not complete case-level ground truth; an unannotated case is not automatically a false positive. Overall accuracy is not the headline metric for a rare-label problem.

## 6. Screen 04 — Release & provenance

This page makes trust inspectable:

- Dataset, run and analysis IDs; source provenance and time policy.
- Clear local-only connection state.
- Small, truthfully named checks computed from the synthetic fixtures.
- Intended read path: published manifest → pinned summary queries + matching case evidence.
- Safe-publication policy: a partial or failed new run does not replace the last successful release.

The current interface is **not** an orchestration console. No Start pipeline, Deploy, Re-run evaluator, Publish or cloud Delete button is provided.

## 7. Requirement-to-interface map

| Proposal requirement | Design response |
| --- | --- |
| Compare historical exposure with volume | Volume–rate plot, filtered baseline, explicit N/L table, rank-by-volume comparison. |
| Small-sample warnings | Minimum support control; low-support counts remain visible, with no ranked lift. |
| Currency-aware denominators | Explicit side selector; all filters applied before aggregation and baseline calculation. |
| Exact money / no cross-currency sum | BigInt eight-decimal atomic totals; separate paid/received lists by currency. |
| Explainable connected cases | Directed graph, shared-entity context, rule text, window/cutoff, source record inspector. |
| Complete evidence despite display cap | Visible/total counters, paginated full evidence, uncapped CSV/JSON downloads. |
| Q2 label independence | Independent workspace and label-free fixtures; evaluation isolated as its own view. Production IAM separation still required. |
| No future events | Dataset-local exclusive-end windows; fixture checks and model tests verify evidence boundaries. |
| Chronological evaluation | Development/holdout/tail cards and explicit unavailable performance metrics. |
| Single-release consistency | Persistent release entry; identity propagated in every export; intended publisher/read policy documented. |
| Interactive usability | No-query filters, keyboard-selectable chart/graph nodes, direct evidence inspection, clear empty states. |
| Private, on-demand operation | No external libraries, embedded credentials, cloud calls, telemetry or public service assumed. |

## 8. Responsive and accessible behaviour

- Wide screens: full navigation, four summary cards, chart/insight columns, case queue + graph + account inspector.
- Medium screens: compact icon navigation; the graph inspector moves below the network.
- Small screens: top navigation; two summary cards per row; chart/insight stack; case cards form a compact grid. Tables scroll inside their containers rather than causing whole-page overflow.
- Native labelled selects and search field; semantic headings/tables; named chart/graph groups; keyboard-selectable SVG objects.
- A skip link, visible focus rings, modal Escape behaviour and live account/download status.
- Categories and warnings use text as well as colour. Reduced-motion preference is respected.
- Production handoff must test text contrast, minimum readable sizes, zoom, keyboard/screen-reader behaviour and actual analyst workflows. This concept is not an accessibility certification.

## 9. Production handoff — without borrowing implementation design

This section describes **proposed adapter needs**, not an existing backend contract. Agree names with the owning teams before integration.

### Q1 adapter

Read approved summaries at dataset/run/date/sender-bank/receiver-bank/format/payment-currency/receiving-currency grain, with additive N/L and exact decimal paid/received totals. Apply filters consistently before rate/lift calculation. Never add overlapping summary grains.

### Q2 adapter

Use a case index for pattern/date search, then fetch the selected immutable case bundle. Required content: identity, stable case/rule ID, window/cutoff, account/entity participants, core evidence source IDs, raw endpoints, timestamps, distinct paid/received amounts/currencies and any display coverage metadata. Validate bundle identity against the pinned release before rendering.

### Evaluation adapter

Read a separate approved evaluation report with chronological scope, eligible counts, metric definitions and exclusions. Do not pass reference matches, labels or baseline answers into case discovery.

### Release adapter

Read the published manifest once per refresh and pin all subsequent reads. Load and validate a complete candidate release before swapping the displayed state. On a missing, incomplete, corrupt or mismatched response, retain the previous successful view and show an explicit warning; never silently mix data from different runs.

### Additional production work

Private authenticated access, least-privilege IAM, server-side query allowlists, bounded/cached reads, audit logging, error/retry handling, immutable evidence validation, latency measurements and cleanup remain separate engineering work. None is claimed as implemented by the local prototype. There are no cloud resources or recurring costs introduced here.

## 10. Basis and boundaries

Design source: [`Proposal/Project_Proposal.md`](../Proposal/Project_Proposal.md), especially §§1–4, 6–7, and [`Proposal/Architecture/Pipeline_Explanation.md`](../Proposal/Architecture/Pipeline_Explanation.md) for the target read path. The root README was read only for required repository orientation.

No files in `Implementation` and no GitHub content were opened to derive this design. No original/generated transaction data, project dashboards, project evaluation outputs or cloud records were consulted. All new artifacts are confined to `Visulization`; existing work elsewhere is left untouched.
