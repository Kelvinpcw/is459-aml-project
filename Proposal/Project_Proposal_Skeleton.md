# IS459 Project Proposal Skeleton

**IBM Transactions for Anti-Money Laundering | HI-Medium**

**Status:** Question-selection draft. The two final questions, quantitative targets, architecture, and AWS services are intentionally not selected yet. No slides are included.

## 1. Business-question shortlist

Choose **two distinct questions**. Start with the decision and user need, then determine the processing requirements and appropriate services.

### Option 1 — Target monitoring resources

**Question:** Which payment formats and bank-to-bank transaction segments have disproportionately high historical laundering exposure, after accounting for transaction volume, so compliance managers can target monitoring resources?

- **Who benefits / decision:** Compliance managers decide where to strengthen controls and focus monitoring effort.
- **Available data / output:** Transaction labels, payment formats, bank identifiers, timestamps, and currencies; a dashboard of segment volumes, laundering rates, and risk relative to the overall rate, with drill-downs and minimum-volume filters.
- **Approach:** Daily or on-demand batch analysis; moderate effort; no ML required. Retrospective risk, not a prediction of future guilt.

### Option 2 — Investigate connected laundering activity

**Question:** Which connected groups of accounts and entities exhibit coordinated transfer patterns, such as fan-in, fan-out, or circular transfers, that warrant investigation beyond an individual transaction?

- **Who benefits / decision:** AML investigators identify related accounts and assemble explainable cases rather than reviewing isolated transactions.
- **Available data / output:** Sender/receiver links, event times, amounts, currencies, and account-to-entity mappings; an interactive case graph with supporting transactions and pattern explanations.
- **Approach:** Batch investigation; higher effort. Start with a few bounded pattern types. Graph analysis does not automatically require a graph database.

### Option 3 — Prioritise a limited review queue

**Question:** Given capacity to review only K transactions per day, which transactions should analysts investigate first to capture the most labelled laundering while limiting legitimate-transaction alerts?

- **Who benefits / decision:** AML operations teams allocate a fixed analyst workload to the highest-priority transactions.
- **Available data / output:** Transaction attributes and strictly past account behaviour; a ranked daily queue with reasons for each alert. Labels support training/evaluation, not scoring inputs.
- **Approach:** Batch scoring; higher effort. Agree on K first. Use explainable rules as a baseline; ML is optional.

### Option 4 — Decide how often monitoring should run

**Question:** Would more frequent monitoring materially reduce time-to-alert for suspicious activity compared with daily processing, enough to justify the additional operational complexity?

- **Who benefits / decision:** AML operations managers choose an appropriate monitoring frequency and response-time requirement.
- **Available data / output:** Chronologically replayed historical transactions and one fixed detector; a comparison of processing schedules, detection delay, captured cases, unique alerts, runtime, and cost per run.
- **Approach:** Historical replay; higher effort. This simulates monitoring schedules rather than claiming a live production stream.

**Recommended pairing: Options 1 + 2.** Management-level monitoring allocation and investigator-level connected-case discovery are distinct decisions with shared preparation work. Option 1 + 3 is a scoring-oriented alternative. Options 3 + 4 need particularly clear separation between workload prioritisation and monitoring-frequency decisions. Evaluation plans appear in Section 5.

<!-- pagebreak -->

## 2. Selected questions and requirements

Complete this worksheet after selecting two options. These requirements should determine the architecture, not the other way around.

| Proposal item | Selected question A | Selected question B |
| --- | --- | --- |
| Exact business question | [TBD] | [TBD] |
| Beneficiary and pain point | [TBD] | [TBD] |
| Decision or action enabled | [TBD] | [TBD] |
| Analysis unit: segment / transaction / account / case | [TBD] | [TBD] |
| Required fields and any additional sources | [TBD] | [TBD] |
| Observation window and use of past history | [TBD] | [TBD] |
| Required refresh frequency and maximum delay | [TBD] | [TBD] |
| Analysis method and simple baseline | [TBD] | [TBD] |
| Output and dashboard interaction | [TBD] | [TBD] |
| Success metric and numerical acceptance target | [TBD] | [TBD] |
| Scope exclusions and assumptions | [TBD] | [TBD] |

### Shared requirements to confirm

| Requirement | Proposed starting point / evidence needed |
| --- | --- |
| Scale | Process all 31,898,238 local transactions; use subsets only for development. Measure full-run time and resource usage. |
| Processing mode | Begin with batch unless a selected question needs lower latency. Do not add streaming only for complexity. |
| Data correctness | Explicit schema, stable account keys, decimal amounts, currency-aware calculations, and a documented time policy. |
| Reliability | Repeatable runs, retries, row-count reconciliation, quarantined invalid records, and no duplicate output on rerun. |
| Usability | A user can move from a summary or alert to its supporting source transactions and understand the result. |
| Security | Least-privilege access, encryption, and no credentials embedded in source code or the document. |
| Operation | Provision compute only when needed; retain enough data, configuration, and logs to reproduce a run. |

### Short problem statement template

“[Beneficiary] currently struggles to [pain point]. Using [available data], the project will answer [question A] and [question B], enabling [decisions]. The solution will deliver [outputs] within [freshness/runtime requirement]. Success will be measured against [baseline] using [metrics and targets].”

**Additional data:** None is necessary for the four shortlisted questions. Add a source only if it closes an identified requirement gap; document its URL, licence, join method, and limitations.

<!-- pagebreak -->

## 3. Understand the available data

The local project contains the brief, supporting notes, and three HI-Medium data files. The dataset is synthetic; it does not identify real customers or establish real-world bank risk.

### 3.1 Local file profile

| File / measure | Observed information |
| --- | --- |
| HI-Medium_Trans.csv | 31,898,238 transactions; approximately 3.03 GB, decimal units. |
| Laundering label | 35,230 transactions labelled 1: 0.110445% of transactions. |
| Actual timestamp coverage | 1 Sep 2022 00:00 to 28 Sep 2022 15:58; 28 distinct dates. Use the actual file range rather than assuming the published primary activity period covers every row. |
| Formats and currencies | 7 payment formats; 15 payment currencies and 15 receiving currencies. |
| HI-Medium_accounts.csv | 2,087,786 rows; 122,333 distinct bank IDs; 668,138 distinct entity IDs. Bank ID + Account Number is unique in this file. |
| HI-Medium_Patterns.txt | 2,756 annotated attempts and 22,743 transaction-row occurrences across 8 pattern types. This is not a complete list of all laundering. |

The pattern types are STACK, CYCLE, FAN-IN, FAN-OUT, GATHER-SCATTER, SCATTER-GATHER, BIPARTITE, and RANDOM. Pattern-row occurrences should not be assumed to be distinct transactions or one-to-one matches without validation.

### 3.2 Data dictionary and usable relationships

| Fields | Meaning and use |
| --- | --- |
| Timestamp | Transaction event date/time, recorded to the minute. Supports windows and chronological evaluation; timezone is not supplied. |
| From Bank + first Account | Sending bank and sending account; identify the source node. |
| To Bank + second Account | Receiving bank and receiving account; identify the destination node. The brief calls this second account Account.1. |
| Amount Paid + Payment Currency | Amount leaving the source, expressed in its payment currency. |
| Amount Received + Receiving Currency | Amount reaching the destination, expressed in its receiving currency; do not assume it is directly comparable with Amount Paid. |
| Payment Format | Payment method: Reinvestment, Cheque, Credit Card, ACH, Wire, Cash, or Bitcoin. |
| Is Laundering | Ground-truth transaction label: 1 = laundering, 0 = legitimate. Available for retrospective analysis and model evaluation. |
| Account-file fields | Bank Name, Bank ID, Account Number, Entity ID, Entity Name. Link accounts to synthetic entities using the bank/account pair. |

### 3.3 What sample records reveal

- **Legitimate self-transfer:** At 2022/09/01 00:17, bank 020 / account 800104D70 sends to itself: USD 6,794.63, Reinvestment, label 0. Self-links are not automatically suspicious.
- **Labelled laundering:** At 2022/09/01 00:19, 070 / 100428660 sends to 008381 / 8035B3E00: USD 27,815.14, Cheque, label 1. Laundering is not confined to one payment format.
- **Entity enrichment:** Normalised bank 20 / account 800104D70 maps to Partnership #1 in the account file. Entity IDs allow activity across several accounts to be studied together.

**Evidence for Option 1:** ACH accounts for 12.13% of all transactions but 87.27% of labelled laundering; its historical laundering rate is 0.7948%, about 7.20 times the overall rate. This supports deeper segment analysis, not a claim that ACH causes laundering or that other channels are safe.

<!-- pagebreak -->

## 4. Processing and pipeline design worksheet

### 4.1 Data preparation requirements

- **Disambiguate the schema:** The raw transaction CSV has two columns named Account. Assign sender_account and receiver_account explicitly by position; do not silently overwrite either column.
- **Make joins reliable:** Transaction bank IDs have zero padding; account-file bank IDs do not. Validate and normalise bank-ID strings consistently while retaining raw values. Join using normalised bank ID + account number. Account number alone is not unique across banks.
- **Respect event time:** The file is not chronologically sorted. Parse timestamps and order/window by event time. Document the unspecified timezone and minute-level precision. Historical replay is a simulation, not an existing real-time feed.
- **Handle money correctly:** Use decimal amounts and retain both currencies. Report monetary totals separately by currency unless a justified, cited historical FX source is added. Currency or bank-name text does not establish verified customer geography.
- **Prevent information leakage:** For detection/scoring, exclude Is Laundering and the pattern annotations from live inputs. Use only information available by the scoring time; tune on earlier data and evaluate later. Retrospective labelled risk reporting is a separate, valid use.
- **Preserve lineage:** No transaction ID is provided. Derive a reproducible source-row identifier, with file/version and row position. Do not delete identical-looking rows without evidence that they are accidental duplicates.
- **Validate beyond missing values:** The full scan found no empty fields or wrong-width transaction rows, but type validity, amount consistency, join coverage, and source/pattern matching still require tests. Do not remove self-transfers wholesale.

### 4.2 End-to-end logical pipeline

**Historical files -> raw storage -> validated and normalised data -> entity enrichment -> two question-specific analysis branches -> insight visualisation**

| Stage | Required processing / output | AWS service |
| --- | --- | --- |
| Ingest and preserve | Versioned raw transaction, account, and annotation files; ingestion manifest and source metadata. Keep evaluation annotations separate from scoring inputs. | [Select after requirements] |
| Validate and clean | Explicit schema, parsed timestamps, canonical IDs, decimal amounts, rejected-row log, and row-count reconciliation. | [TBD] |
| Store and enrich | Queryable analytical representation; sender/receiver account-to-entity joins with measured match coverage. | [TBD] |
| Analyse question A | [Method, time window, features/aggregations, baseline, output dataset, and refresh requirement.] | [TBD] |
| Analyse question B | [Method, time window, features/aggregations, baseline, output dataset, and refresh requirement.] | [TBD] |
| Visualise and act | [Dashboard/case view/alert queue], filters, explanations, and source-transaction drill-down. | [TBD] |

**Cross-cutting controls:** Orchestration, retries, run metadata, access control, logging, checkpoints where justified, and resource shutdown/cleanup.

**Architecture diagram placeholder:** Show the shared ingestion/preparation layer, both analysis branches, their outputs, and the final user-facing views. Every component must trace to a requirement. Add specific AWS services only after the team selects its questions.

<!-- pagebreak -->

## 5. Evaluate whether the design meets requirements

Separate business usefulness from pipeline correctness. Neither a sophisticated architecture nor an impressive model metric alone establishes a useful solution.

### 5.1 Question-specific evaluation options

| If selected | Baseline and evaluation approach |
| --- | --- |
| Option 1: monitoring allocation | Compare volume-only rankings with rate/lift rankings. Validate numerators and denominators, apply a minimum segment size, and show uncertainty. Test whether the dashboard supports a concrete allocation decision; numerical user-acceptance targets remain [TBD]. |
| Option 2: connected investigations | Compare with a simple single-transaction rule. Report coverage of held-out annotated attempts, transaction-label composition of alerted cases, and explanation quality. Unannotated groups are not automatically negative examples: case-level ground truth is incomplete. |
| Option 3: limited review queue | Compare with a simple amount/velocity ranking. Measure precision at K, recall at K, legitimate alerts, and uplift on chronological holdout data. Report results at several agreed review capacities. |
| Option 4: monitoring frequency | Compare daily processing with more frequent schedules using the same detector, lookback policy, and dataset. Measure median/p95 delay, captured cases, unique alert volume, runtime, and operational cost; report missed cases separately. |

For any learned or tuned detector, fit only on earlier data, validate on a subsequent period, and reserve a later test period. Features must not use future transactions. Define treatment of annotated attempts that cross split boundaries. Evaluate on the natural class distribution, not only a balanced sample.

**Important:** An always-legitimate classifier achieves approximately 99.8896% accuracy on this file. Accuracy alone is therefore unsuitable as the main AML success metric. Label 0 is dataset ground truth, not a guarantee about unseen real-world behaviour.

### 5.2 Pipeline acceptance checklist

| Requirement | Test / evidence |
| --- | --- |
| Complete processing | Input rows = accepted rows + quarantined rows; joins do not multiply transaction rows. Reconcile analysis totals. |
| Correct relationships | Verify normalised bank/account keys, unique account-dimension keys, sender/receiver joins, and unmatched-account counts. |
| Repeatability | Same input and configuration produce the same analytical results; a rerun does not duplicate outputs. |
| Recovery | Demonstrate safe retry of a failed stage without unnecessarily repeating successful work. |
| Performance | Record end-to-end runtime and relevant throughput on development subsets and the complete dataset; target [TBD]. |
| Usability | Demonstrate the intended user decision, filters, explanations, and source drill-down; acceptance scenario [TBD]. |
| Operational hygiene | Capture run cost and logs, apply access controls, verify shutdown, and document final resource deletion. |

### 5.3 A purposeful X-factor

Choose one enhancement only if it demonstrably helps the selected questions: automated runs with recovery evidence; interactive linked-case exploration; a measured frequency/latency experiment; or benchmarked processing improvements. ML and additional services are optional, not automatic enhancements.

<!-- pagebreak -->

## 6. Scope, delivery plan, and guardrails

### 6.1 Proposed scope

- **In scope:** The local HI-Medium dataset, two distinct business decisions, one shared pipeline with branches or two justified pipelines, data-quality checks, useful visualisation, evaluation, reproducible source code, and setup/run evidence.
- **Pending selection:** The two questions, pattern/rule scope, review capacity, time windows, numerical targets, AWS services, and the final architecture diagram.
- **Not assumed:** Production deployment, a real live banking feed, verified customer countries, KYC/sanctions matching, proven criminal intent, long-term forecasts, or financial savings. These are not established by the available data.
- **Document only for this request:** Slides will be prepared separately if requested. This skeleton supports proposal preparation; it does not replace the course's required presentation submission.

### 6.2 Milestones and responsibilities

| Milestone | Output / owner |
| --- | --- |
| Discovery — completed for this draft | Review the brief, dictionary, samples, and local file profile. |
| Select questions | Choose two distinct options; finalise audience, decision, scope, and success criteria. Owner: [TBD]. |
| Design before proposal pitch | Architecture diagram, justified processing mode, AWS-service mapping, and evaluation plan. Owner: [TBD]. |
| Prototype | Small end-to-end run with validated joins, baseline analyses, and initial user-facing output. Owner: [TBD]. |
| Full-scale implementation | Process the complete dataset; test correctness, runtime, recovery, and question-specific results. Owner: [TBD]. |
| Final evidence and cleanup | Source code, narrated setup/run videos, individual contributions, reproducibility notes, and AWS deletion checklist. Owners: [TBD]. |

The supplied brief places the proposal pitch in Week 9 and the final presentation/artefacts in Week 13. Confirm the actual class dates with the team.

### 6.3 AWS and budget assumptions

**Team preference:** Use any appropriate AWS services, including services not taught in class. Compute will run only when needed, so cost should be a secondary design criterion rather than the starting point.

**Operational caveat:** Stopping compute does not eliminate storage, snapshots, logs, or some network-resource charges. Track residual costs, use a budget alert, and document shutdown and final teardown.

**Brief guardrails:** The supplied brief states a USD 250 budget, prohibits AWS Marketplace purchases, and asks teams to avoid expensive services such as Redshift, RDS, and QuickSight in favour of cost-effective alternatives. If the instructor has provided updated permission, record it before relying on a different interpretation. No AWS resources are provisioned by this document.

### 6.4 Sources and evidence

1. **Local project brief:** [IS459] Project_G2.pptx, especially slides 4–6, 8, and 10–11: dictionary, distinct questions, pipeline expectations, beneficiaries, and evaluation.
2. **Local supporting notes:** other.txt: business-first design, timing requirements, and dataset selection.
3. **Local data:** Ibm_dataset_medium/HI-Medium_Trans.csv, HI-Medium_accounts.csv, and HI-Medium_Patterns.txt. Counts and sample observations in this document were obtained from these files; original data was not modified.
4. **Dataset source:** https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
5. **IBM provenance and licence notes:** https://github.com/IBM/AML-Data — explains synthetic generation and the data's CDLA-Sharing-1.0 licence.

**Next decision:** Select two shortlist options. Then replace the [TBD] fields with an agreed business scope, measurable requirements, and a justified AWS pipeline.
