# Understand the entire pipeline

Read this first, then use [Q_AND_A.md](Q_AND_A.md) to rehearse. You do not need an assigned task or a formal team role. The purpose is to explain what the implemented batch system does, how the pieces connect and where its limits are. This is a source walkthrough, not a fresh AWS execution report.

## The short explanation

We turn a large synthetic payment file into two useful outputs: historical exposure comparisons for managers and explainable connected-account leads for investigators. We clean the inputs once, keep labels away from detection, evaluate cases separately, and publish a consistent set of results for the dashboard. The dashboard reads the published outputs; it does not run the detection pipeline.

## The two business questions

| Question | Decision | Main output |
| --- | --- | --- |
| Q1: Which payment formats/bank-pair segments have disproportionate historical labelled exposure after accounting for volume? | Where should monitoring controls receive closer review? | Counts, rates, baseline/lift, support, currency-specific amounts and trends |
| Q2: Which connected account groups show fan-in, fan-out or short cycles worth investigating? | Which relationships and supporting payments should an investigator inspect? | Cases, directed account graphs, rule/window explanations and complete evidence |

Q1 uses existing historical labels. Q2 generates structural leads without reading those labels or pattern annotations. Neither screen declares a real person guilty. The source is synthetic IBM HI-Medium data. Formal wording is in the [proposal](Proposal/Project_Proposal.md).

## Follow one payment through the system

### 1. Keep original inputs in S3

There are three source files: transactions, account-to-entity mappings and annotations of selected laundering patterns. Original inputs are kept separately from generated results. Source identity and checksums make it possible to say exactly which input produced an output.

A transaction's stable source ID combines the **original transaction-file checksum and original one-based data-record ordinal**. It does not change because we sort/filter a copy. Two rows with identical visible values can still be two distinct payments.

S3 is storage. Uploading files does not automatically start a processing job or publish a dashboard release. Fresh clones deliberately do not include these large/private files.

Code: [input builder](Implementation/scripts/build_development_input.py), [preparation](Implementation/jobs/prepare.py). The reviewed preparation payload is preserved in [preparation-v2](Implementation/releases/preparation-v2/prepare-v2.py); editable source and frozen deployed code are distinct.

### 2. Prepare and validate the data once

Preparation checks fields and types, maps the repeated `Account` CSV headers by position to sender/receiver, and enriches endpoints with their entity information. Account numbers are identified together with their bank; account number alone is insufficient.

Unknown enrichment is explicitly represented. It must not silently drop payments or multiply them through an incorrect join. Money uses exact `decimal(38,8)`, with paid/received currencies kept separately. Source times have minute precision and no supplied timezone; the project uses dataset-local event time, with a fixed internal parsing convention.

Outputs include cleaned Parquet facts, separately stored labels, quarantine/reconciliation information and a quality report. Parquet lets later stages read selected columns/partitions efficiently. Q2 receives an allowlisted label-free input contract; labels and annotations remain outside its read boundary.

A successful stage accounts for its input and satisfies its quality contract. A file or job definition existing is not evidence that the stage succeeded.

### 3. Q1 creates additive daily summaries

Q1 joins the historical labels to prepared facts and stores counts at a declared daily bank/format/currency grain. The dashboard filters the population, sums its counts and then calculates the rate and lift. It never averages daily percentages or adds overlapping summary grains.

- `N`: payments in the selected segment/population.
- `L`: historically labelled payments in that same scope.
- Rate: `L / N`.
- Lift: segment rate divided by the rate of the **same filtered baseline**.

**Invented arithmetic example, not project results:** a segment with 20 labels in 2,000 payments has a 1% rate. If its filtered baseline is 0.2%, its lift is 5×. That makes it worth inspecting, not proven criminal activity. A rate based on two payments is much less stable; ranked dashboard comparisons require 1,000 payments of support.

Currency side, currency, dates and payment-format filters apply consistently to numerator, denominator and baseline. Amounts remain exact and currency-specific. A transferred total is not unique criminal proceeds.

Code: [Q1 aggregation](Implementation/jobs/q1_risk.py), [dashboard SQL builders](Implementation/dashboard/data.py), [trend calculations](Implementation/dashboard/trends.py).

### 4. Q2 independently searches connected activity

Q2 represents a bank/account as a node and a directed payment relationship as an edge. Distinct counterparties determine fan support; parallel source payments still remain retrievable evidence. Self-transfers are kept in stored facts but excluded from motif edges.

| Pattern | Implemented rule idea | Why it is only a lead |
| --- | --- | --- |
| Fan-in | At least five distinct non-self senders pay one hub | Legitimate businesses also collect payments |
| Fan-out | One hub pays at least five distinct non-self receivers | Legitimate businesses also distribute payments |
| Cycle | Closed directed structure across 2–4 distinct accounts | Structural closure does not prove time-ordered return of the same funds |

The full implementation uses distributed Spark fan aggregation and bounded cycle joins. Cycle search uses the declared degree-eligible graph (incoming and outgoing degree at most 64). Capacity/expansion guards can fail a run; they must not silently truncate the detector's results. Do not claim exhaustive detection of all graph patterns or long cycles.

Daily snapshots use **overlapping seven-day lookbacks**. A pattern can span minutes or days; independent one-minute windows would lose it. Each snapshot has an exclusive end/cutoff, and future payments cannot enter earlier snapshots. Early snapshots disclose unavailable pre-dataset history. The old first-minute driver pilot is a separate preserved prototype, not the full-data implementation.

Code: [distributed detector](Implementation/jobs/q2_distributed.py), [snapshot scheduling](Implementation/jobs/q2_snapshots.py). The label-reading Q1 role is not reused for Q2; allowlists and IAM separation enforce the intended boundary.

### 5. Save a case with complete evidence

A case records its stable ID, rule/version, input/run/analysis identity, window/cutoff, participants and supporting source transactions. Its header/index supports discovery; complete evidence is stored in checksum-checked chunks/shards. Display previews do not define the evidence population.

The same payment or motif can appear in overlapping snapshots. Summing case counts or evidence memberships across snapshots does not give a unique count of laundering events/payments.

The dashboard displays at most 100 graph nodes, 500 links and 200 evidence-preview rows. The complete download remains available; cases exceeding the in-app download size can be retrieved with the [export CLI](Implementation/scripts/export_case.py). Detector capacity guards and UI display limits are different controls.

Code: [bundle packing](Implementation/jobs/q2_bundle_shards.py), [bundle validation/download](Implementation/dashboard/data.py).

### 6. Evaluate after detection

A separate trusted evaluator reads immutable cases, eligible prepared facts, historical labels and pattern annotations. It does not feed answers back into Q2.

For individual-payment metrics, the alerted set is the union of distinct core evidence source IDs. Evaluate against the full declared eligible payment population, including eligible undetected payments, rather than only detected evidence. Precision asks how many alerted payments have positive labels; recall asks how many positive payments are covered. A missing/zero denominator can make a metric unavailable.

For annotated-pattern recovery, only supported, unambiguously matched and in-window attempts are eligible. Typed recovery requires the correct motif/hub/oriented cycle and at least 80% of the matched annotated source transactions in one case's core evidence. Incomplete annotations are not exhaustive truth; unannotated cases are not automatically false positives.

The historical evaluation protocol keeps development (1–8 September), holdout (9–16) and sparse tail (17–28) separate. Settings are frozen before holdout. A per-currency matched-alert-volume amount baseline provides a comparison; a development-frozen fraction baseline and type-agnostic annotation coverage are reported separately. The frozen five-percentage-point target concerns eligible attempt recovery against amount coverage, not a five-point precision gain.

Code: [distributed evaluator](Implementation/jobs/evaluate_distributed.py). Show the actual pinned evaluation report for measured results; a passing recovery target does not establish better transaction precision/recall or recovery of all laundering.

### 7. Publish one coherent release

The release gate validates required stage quality reports, identities, declared populations and complete outputs. The publisher writes an immutable release manifest and conditionally updates the current pointer. This prevents silently mixing outputs from unrelated attempts or replacing another publisher's update.

If processing/publication fails, the previous successful release remains available. “Stage finished” and “new release published” are different events. Hash/identity checks establish which artifacts belong together; they are not claims of detector effectiveness.

Code: [control/Catalog/publication entry point](Implementation/jobs/control.py), [release validation and conditional publication](Implementation/pipeline/release.py).

### 8. Display published results

The connected TRACE dashboard loads/verifies the selected published manifest and pins reads to it. Athena queries Q1 summaries and the Q2 case index; S3 supplies the selected case's bundles and separate evaluation report. Glue Catalog describes table schemas/partitions so Athena can query the Parquet outputs.

- **Monitoring overview:** supported comparisons and an explanation of exposure versus volume; daily counts/rates/traffic below.
- **Connected cases:** bounded case queue and directed graph, participant/entity details, rule/window and complete downloads.
- **Evaluation & coverage:** actual eligible denominators, classification versus pattern recovery, baselines and limitations.
- **Release & provenance:** the dataset/run/release and coverage behind the view.

Rolling dates end at the latest **published data date**, not today's laptop date. A label count rising is not necessarily a risk-rate rise: payment volume may have increased too. Low volume is a warning about stability, not proof of incomplete ingestion. Reporting windows do not replace frozen evaluation splits.

Code: [app](Implementation/dashboard/app.py), [presentation](Implementation/dashboard/presentation.py), [data reads](Implementation/dashboard/data.py). Run instructions: [SETUP.md](Implementation/SETUP.md).

## What each AWS service contributes

| Component | Job in this project | What it does not imply |
| --- | --- | --- |
| S3 | Inputs, Parquet outputs, reports, case evidence and release manifests | Files arriving automatically start daily processing |
| Glue / Spark | Preparation, aggregation, detection, evaluation and control jobs | A saved job definition is running compute |
| Glue Catalog | Queryable schemas and partitions | A separate copy of every transaction |
| Step Functions | Coordinates on-demand stages, parallel branches and failures | A recurring daily schedule |
| Athena | Bounded reads of published summaries/indexes | Detection runs inside the dashboard |
| Streamlit / Plotly / PyVis | Connected analytical interface and graph display | Every displayed lead is confirmed laundering |
| IAM | Separate service/read boundaries, especially label-free Q2 | A Git branch isolates cloud resources |
| Optional EC2 + SSM | Temporary private dashboard hosting/access | Required for local viewing; the laptop launcher avoids this deployment |

## What “completed” means here

The batch software path is implemented and the operator has published outputs that can be viewed. Confirm the exact completed scope from [status](Implementation/STATUS.md), [relevant handoffs](Implementation/team-handoffs/README.md), open PRs and the pinned release. This document made no new AWS checks.

This is not a production banking deployment, an ML fraud classifier or an automatically scheduled incremental daily feed. Formal user testing and latency/operational claims need their own evidence. Updating source on GitHub doesn't deploy jobs, recompute data or restart another teammate's server.

## Rehearse with the dashboard

1. Name the two decisions and the synthetic source.
2. Pick a supported Q1 segment; explain N, L, rate, baseline, lift and currency/time scope.
3. Compare a count trend with its rate and traffic; explain why they can disagree.
4. Open one Q2 case; explain the arrows, entity mapping, rule, cutoff and full evidence path.
5. Open evaluation; distinguish precision, recall and eligible pattern recovery. State when a baseline is better.
6. Show provenance and explain how partial failures retain the previous release.

Ask your agent to explain each step in plain language, quiz you and point to the source. Ask it to say “unknown/not verified” for measurements it cannot access, rather than fill gaps with plausible numbers.
