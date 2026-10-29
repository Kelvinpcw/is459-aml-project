# Presentation Q&A — explain it without bluffing

Use after [PIPELINE_WALKTHROUGH.md](PIPELINE_WALKTHROUGH.md). These answers describe the implementation and its limits, not a new cloud validation or invented measured result. For exact results, use the pinned dashboard/evaluation and the operator's current approved evidence.

## 1. What problem are you solving?

We help managers identify payment segments with disproportionate historical labelled exposure and help investigators inspect connected account patterns with their evidence. Volume alone can hide concentrated exposure; individual payments alone can hide a wider structure.

## 2. Why two business questions? Aren't they the same?

They support different decisions. Q1 compares formats/bank pairs using known historical labels. Q2 builds label-free structural cases across accounts. Historical exposure is not passed into Q2 as a detector score or seed. Offline evaluation is a third, separate activity.

## 3. Is this machine learning? Why not train a model?

The core system uses descriptive aggregation and explicit graph rules. The chosen questions need transparent segment comparisons and explainable relationships, not necessarily a trained predictor. ML could be evaluated as a future extension; it is not claimed as implemented.

## 4. What goes in and what comes out?

Inputs are the synthetic transaction file, account/entity mapping and selected-pattern annotations. Preparation produces validated facts and separate labels. Q1 produces daily additive summaries; Q2 produces cases/index/evidence; the evaluator produces scoped performance/coverage reports. A validated manifest ties a successful release together for the dashboard.

## 5. If labels already exist, why detect anything?

Q1 intentionally describes known historical labels. Q2 simulates discovering structures without access to those answers, then the independent evaluator uses labels/annotations to assess it. Letting Q2 read the answers would invalidate that separation. The data is synthetic; these are not real-bank criminal verdicts.

## 6. How do you stop label leakage?

Preparation stores labels separately, Q2 accepts an allowlisted label-free input, and its service-role boundary excludes labels, annotations, Q1 label-derived scores and evaluation artifacts. Detection settings are frozen before holdout evaluation. Local tests also exercise prohibited-column/input rejection. Browser navigation alone is not a security boundary.

## 7. Why not rank segments by number of laundering payments?

A large segment can have more labelled payments simply because it has more total traffic. Show both counts and `L/N`, then compare the segment rate with the same filtered baseline (lift). Keep minimum support and uncertainty visible. This supports control review; it is not an optimisation of staff allocation or proof of unsafe banks.

## 8. What is lift? How is the baseline selected?

Q1 lift is segment rate divided by the rate of the same filtered population. Dates, currency side/currency and payment-format scope must match. Sum additive N/L first, then calculate rates; never average daily rates. Zero/absent baseline means lift is not measurable, not infinity.

The evaluator also reports transaction lift against its declared population; name which screen/metric you mean. Don't confuse a lift ratio with a percentage-point improvement.

## 9. Why the 1,000-payment threshold? What about small segments?

It is the declared dashboard ranking-support threshold, intended to avoid strong interpretation from tiny samples. Small segments remain inspectable as counts with low-support warnings. It is not a detector probability threshold or proof that all supported estimates are reliable. We do not lower it against holdout answers to manufacture attractive priorities.

## 10. What does an upward laundering trend mean?

It means more labelled payments in that selected historical scope. Check the total traffic and rate alongside it: counts can rise while the rate falls. Compare consistent filters and inspect low-volume/coverage warnings. A daily reporting view should not assume every increase is worsening underlying risk.

The rolling reporting interface is calendar-independent. Historical development/holdout/sparse-tail evaluation splits remain separate and frozen. Low volume by itself does not establish partial ingestion.

## 11. How do you handle money and different currencies?

Use exact eight-decimal values and keep paid/received currencies separate. Fix the selected currency side before summing its amounts, and apply the same population filter to counts/rates. We don't add USD and EUR into an unsupported total. Transferred value can revisit accounts and is not unique criminal proceeds.

## 12. What exactly are fan-in, fan-out and cycles?

Fan-in is at least five different non-self senders to one hub; fan-out reverses that direction. A cycle is a closed directed structure over 2–4 distinct accounts. Distinct counterparties establish structure; multiple actual payments on a relationship remain evidence. Self-transfers remain stored but aren't motif edges.

These patterns occur legitimately too. A structural cycle does not demonstrate that the same funds travelled around it in chronological order. Investigators must assess context; the interface should say “lead”, not “confirmed laundering”.

## 13. Why use seven-day snapshots? Can a pattern cross a day boundary?

Each daily snapshot examines an overlapping seven-day lookback with an exclusive cutoff. That preserves within-lookback patterns spanning minutes/days. Independent minute windows would miss cross-window structure. No future event can enter an earlier snapshot; missing pre-dataset history is disclosed. A pattern longer than the supported lookback/shape can be outside coverage.

## 14. Is the graph algorithm scalable or exhaustive?

The full implementation uses distributed Spark aggregation and bounded joins, rather than collecting the whole transaction graph on one driver. Fans retain complete core evidence. Cycle search is limited to 2–4 accounts in the declared degree-eligible graph (in/out degree at most 64), with explicit expansion guards. A guard failure stops the attempt rather than silently clipping results.

This is bounded supported coverage, not arbitrary-length exhaustive graph search. The frozen first-minute driver pilot is a separate historical implementation; do not present it as the distributed full-data method.

## 15. Does the 100-node graph cap lose evidence?

The UI preview is capped, not the complete case. The case manifest retains complete evidence references, which are checksum-checked and downloadable. The in-app archive has a size bound; the export CLI handles larger cases. Distinguish UI display caps from detector capacity guards, and don't mistake overlapping snapshot memberships for distinct payments.

## 16. How do you know which source payment an edge came from?

A stable source ID uses the original transaction-file checksum plus its original one-based data-record ordinal. Cases retain those IDs and their run/rule/window. Identical-looking records are not deduplicated just because their values match. Accounts use bank plus account number; raw identifiers and unknown mappings are retained.

## 17. How do you measure effectiveness?

Report individual-payment precision/recall on the full declared eligible population, using the distinct union of alerted source payments. Also report eligible annotated-attempt recovery and coverage/exclusions. Precision is positive labels among alerted payments; recall is covered positives among all eligible positives. Undefined denominators are reported as unavailable. Overall accuracy is not an informative headline for rare positive labels.

## 18. What counts as a recovered annotated attempt?

An eligible supported annotation must match source records unambiguously and fit the time/shape contract. Typed recovery needs the correct motif and hub/oriented cycle plus at least 80% of its matched annotated transactions in one case's core evidence. Hidden preview edges still count if stored as core evidence. Unsupported/ambiguous/out-of-scope attempts are reported separately; missed eligible attempts stay in the denominator.

## 19. Why aren't annotations complete ground truth?

They describe selected laundering attempts, not every possible legitimate/illegitimate case. A case without an annotation is not automatically false. Use historical payment labels for transaction metrics and declared eligible annotations for pattern recovery, with their different denominators clearly named.

## 20. What is the baseline and did you beat it?

Compare with high-amount payments selected within each currency at matched alert volume. A separate development-frozen fraction baseline is retained. The amount diagnostic doesn't need to emit a pattern name; type-agnostic 80% annotation coverage is reported as well as typed case recovery.

**Read the actual pinned evaluation before answering “did we beat it?”.** Transaction precision/recall and pattern recovery are different measures. If amount performs better on transaction classification, say so. The predeclared +5 percentage-point target concerns eligible typed recovery versus matched-volume amount coverage, not a blanket claim that the detector is better or finds all laundering.

## 21. How do you avoid evaluating on your training answers?

The historical protocol uses 1–8 September for development, freezes settings, evaluates 9–16 September as holdout and reports 17–28 September separately because the sample's traffic differs. Eligible scoring populations and snapshot cutoffs are explicit. Earlier context may support a later case, but future events/snapshots can't create earlier alerts. We don't retune on holdout outcomes.

## 22. What happens if a job fails halfway?

Partial/new outputs don't replace the previous successful release. Required quality, completeness and identity checks must pass before publication. Immutable outputs and a conditional pointer update support traceability/recovery without blindly rerunning completed stages. A stopped job is not the same thing as a published successful release.

## 23. How does the dashboard avoid mixing versions?

It verifies one published manifest and pins summary queries, case evidence and evaluation reads to that release. Refresh switches only after the new release validates; failure retains the old selection. A code commit, frozen software package and published data release are related but different identities. Merging GitHub code alone updates none of the cloud data.

## 24. Why S3, Glue, Athena and Step Functions?

S3 retains inputs/results/evidence. Glue/Spark performs the large batch processing. Catalog schemas/partitions make Parquet queryable. Athena reads compact published summaries/indexes on demand. Step Functions coordinates dependencies, parallel branches and failures. Streamlit/Plotly/PyVis display the results. The project doesn't require streaming infrastructure or a separate graph database to answer these bounded batch questions.

## 25. Does it run automatically when new data arrives each day?

No recurring/incremental ingestion is implemented by this project. It is an on-demand batch path. The reporting UI can move its rolling range when a newer complete release is published, but that doesn't schedule processing or make it incremental. Scheduling, late-data policy, idempotent incremental updates and ongoing cost operations would need deliberate additional work.

## 26. Is the whole project complete? What should we demonstrate?

The batch software path is implemented and existing published outputs are available to the operator. Show the actual release's source/scope, quality/evaluation evidence and dashboard. Confirm completion/state through [VERIFY_PROGRESS.md](Implementation/VERIFY_PROGRESS.md), relevant handoffs and open PRs; don't claim a new full run because source files exist.

Describe remaining limits honestly: synthetic data, bounded graph coverage, incomplete annotations, historical labels, no production deployment claim, no automatic daily feed, and formal UI/user-test measurements only where evidence exists. Exact runtime/cost/billing claims should come from the operator's approved records, not invented numbers or estimates presented as invoices.

## Rehearsal prompt for any teammate's AI agent

```text
Read PIPELINE_WALKTHROUGH.md, Q_AND_A.md and the current relevant source.
Explain the entire pipeline to me as a beginner, one stage at a time.
Then ask me ten presentation questions, wait for each answer and correct
my reasoning with the relevant code/doc reference. Emphasise business
value, labels/leakage, denominators, windows, evidence completeness,
baselines, failure recovery and remaining limitations. Do not change code,
log in, access AWS, rerun processing or invent measured results for this
learning session. If I ask for a change later, use the shared GitHub
change/handoff workflow; I don't need an assigned role or a separate
reviewer to merge my own checked PR.
```
