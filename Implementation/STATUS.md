# Implementation status

**How to use this file:** this is an implementation/evidence timeline, not a live AWS inventory or task queue. Start with the [team guide](../TEAM_START_HERE.md), use [progress verification](VERIFY_PROGRESS.md), and read relevant [handoffs](team-handoffs/README.md) plus open PRs before continuing. Older dated sections describe their stated scope; later relevant changes can supersede them. Missing private evidence does not block local source work.

`main` contains the complete software path: shared preparation, Q1 summaries, distributed Q2 fan/cycle detection, a separate evaluator, conditional publication, a read-only dashboard, and on-demand AWS deployment/cleanup tooling. Architecture/configuration files and local tests alone do not establish a successful full cloud run.

Batch refreshes have no fixed completion-time requirement. Observed runtime and cost remain operational measurements, not pass/fail completion criteria. Configured job timeouts and dashboard shutdown guards remain safety controls; interactive UI response targets are separate.

The earlier full-v2 recovery passed **68 synthetic tests in 47.870 seconds**, including complete sharded evidence round-trips, deterministic retries, path/hash guards and publication failure retention. Both recovery templates pass cfn-lint. For full-v2, detection/aggregation/snapshot AST comparisons and byte-identical evaluator files establish that its recovery changes storage/execution only; frozen holdout settings were preserved.

The latest evaluator verification fix passed **87 synthetic tests in 53.120 seconds**, including exact frozen small-fixture result equivalence and physical-plan checks. Fan reconstruction now uses two directional equi-joins rather than an OR predicate that produces a Cartesian plan. Metric/calibration formulas, baseline settings, chronological splits and detector code are unchanged. The evaluator now also refreshes every join's right-side expression IDs to avoid Glue checkpoint-reference conflicts, with wide schema/type/rank and exact metric equivalence checks. Frozen full-v5 contains these corrections. Deployment authority and actual outcomes are recorded only in the private operational checkpoint; do not infer permission for another run from these source files. Completed outputs are reused, never regenerated merely for validation. The evidence-export CLI searches published snapshot partitions using locator columns, and shutdown tooling covers every known recovery execution. Both latest templates pass cfn-lint; the dashboard still has its one-hour terminate guard and unchanged grants.

The earlier **source-only publication** policy kept detailed AWS records local. Effective **29 October 2026**, the user additionally requires a **sanitised, committed and pushed handoff after every AWS session**, including read-only checks and failures; follow [AWS_HANDOFF.md](AWS_HANDOFF.md) and [team-handoffs/](team-handoffs/). Raw reports, detailed cost records and the operational checkpoint still stay local. On the operator machine read `Implementation/data/aws-operations-20261028/PROJECT_CHECKPOINT.md`, its ledger and ignored `Implementation/aws/reviews/full-monitor-latest.json`. A fresh clone lacks those files. Earlier private runs have not been retroactively verified/published by this policy change. Previously committed pilot evidence remains historical; never infer live state or authority to start processing from it.

| Component | Implemented contract |
| --- | --- |
| Preparation | Deterministic original-file/record source IDs, positional repeated headers, bank/account enrichment, exact decimals and separated labels |
| Q1 | Additive daily counts at both currency dimensions; filtered common baseline, supported rates/lift and currency-specific amounts |
| Distributed Q2 | Fan-in/out and balanced two-hop 2–4-cycle joins over overlapping seven-day daily snapshots; explicit degree/capacity guards and complete evidence |
| Evaluator | Eligible population, unique exact annotation matching, development-frozen baseline/target, chronological holdout and separate sparse tail |
| Publication | PASSED reports, physical Parquet populations, hashes, immutable manifest and compare-and-swap current pointer; failures retain prior release |
| Dashboard | Pinned release, Q1 filters/charts, bounded case graphs with full downloads, honest evaluation and scope warnings |
| Operation | Isolated service roles, on-demand Step Functions, bounded jobs/queries, targeted recovery and private temporary EC2/SSM with cleanup |

Frozen releases are immutable. Full-v2 uses schema3 ZIP shards, reducing writes without changing cases/source evidence. The older first-minute driver detector retains its 50,000-row guard and is separate from distributed detection. Full-scale effectiveness, observed runtime, UI targets and cloud completion must be assessed from actual operator records. No team interviews, human contributions or narrated recordings are fabricated.

Read [setup](SETUP.md), [runbook](RUNBOOK.md), [completion plan](COMPLETION_PLAN.md), [proposal](../Proposal/Project_Proposal.md) and [checkpoint pointer](../PROJECT_CHECKPOINT.md). Known pilot findings: [Q1](results/Q1_VALIDATION.md), [Q2](results/Q2_VALIDATION.md), [evaluation](results/EVALUATION_CLOUD_VALIDATION.md).

The dashboard evaluation screen displays the exact holdout payment interval, precision alongside recall, both amount-baseline comparisons, the eligible annotation denominator and frozen recovery target. These are distinct measures; attempt recovery does not establish better individual-payment precision or recall. The immutable `releases/dashboard-v1` package contains this presentation change. Eight release/dashboard checks and the updated temporary-dashboard template validation pass.

## Team handoff and offline visual concept — 29 October 2026

- [TEAM_START_HERE.md](../TEAM_START_HERE.md) provides beginner onboarding and an AI prompt: local-first setup, explicit task assignment, GitHub authentication, optional administrator-provided AWS login and required shared handoff. Its [follow-up record](team-handoffs/2026-10-29-beginner-onboarding.md) identifies the documentation checks; no cloud setup was executed.
- `AGENTS.md`, the setup/runbook and [AWS_HANDOFF.md](AWS_HANDOFF.md) now require shared AWS session summaries, ownership coordination, explicit branch pushes and PRs. Check open PRs for handoffs not yet merged into `main`. These are instructions, not automated AWS/GitHub enforcement.
- [`Visulization/`](../Visulization/README.md) adds the independent TRACE offline visual concept: four views, invented aggregates/cases, exact-money formatting and complete local evidence downloads. It is separate from `Implementation/dashboard/`, has no backend/cloud integration and does not establish detector performance.
- The [dated handoff](team-handoffs/2026-10-29-collaboration-and-prototype.md) records the local checks for this publication. **AWS: none; no new cloud state, results, cost or cleanup has been verified.** Existing private operational records and frozen releases are unchanged.

A local visualization launcher verifies an explicit project profile, uses the bounded dashboard workgroup and binds to localhost. This avoids applying the smaller development scan limit to full-data case queries. It starts no AWS processing or EC2; normal Athena/S3 read charges may apply. See the visualization section in SETUP.md.

## Dashboard presentation refresh — 29 October 2026

The current source adds compact reporting filters, a supported-lift ranking with a consistent-population baseline, an alternate volume/rate view, readable exact-value tables, and a deterministic bounded case graph with click-to-inspect account details and fit/zoom controls. Evaluation separates transaction classification from eligible-pattern recovery and keeps the baseline comparison visible. Only the selected page loads its data; filters persist across navigation. Source query contracts, money strings, graph/evidence bounds, detector thresholds, evaluator settings and frozen releases remain unchanged.

Validation: five display/graph safety checks, one synthetic interactive navigation/filter test, and eight existing release/dashboard checks pass. The local dashboard uses the new source; the previously frozen cloud software remains historical. New browser screenshots and operational observations remain private. No processing run, IAM change or EC2 deployment is part of this refresh.

## Daily trend view — 29 October 2026

Monitoring now accepts the complete published date range. A new bounded daily query sums additive N/L counts from the common Q1 base, with the same release, date, currency-side and payment-format filters. The chart aligns daily labels, laundering rate and total traffic, shades the sparse tail and keeps rate traces separate across the boundary. First-to-last-day comparisons state the observed counts/rates and flag comparisons across different traffic populations.

Main-period and sparse-tail rankings retain separate date ranges and baselines. Mixed-range overview counts are additive; no pooled headline rate is displayed. Known filtered zero-traffic days have no measurable rate; dates outside published coverage remain gaps. Segment support and exact monetary amounts are unchanged. The detector, evaluator, chronological calibration and frozen releases are unaffected.

Validation: 18 focused tests passed, including independent synthetic SQL aggregation, both currency sides, weighted count totals, zero/gap handling, period boundaries and full-range navigation with separate ranking queries. Browser observations and query records remain private. No Glue run, EC2 deployment or IAM change was needed.

## Rolling reporting windows — 29 October 2026

At the user's clarification, the dashboard now uses last-7-day, last-30-day and custom reporting windows anchored to the latest published date. Sample-specific main/tail controls are superseded. Overview counts, rates and segment baselines all use one consistently filtered selected window; rates are ratios of summed counts. Case exploration defaults to the latest published snapshot, with an explicit historical selector.

Daily volume below 1,000 selected payments is an informational flag and never removes records or implies incomplete ingestion. Missing release dates remain gaps. Whole-day completeness is unknown unless the release explicitly supplies optional day coverage; no date is automatically marked complete or partial from its volume. Refresh data preserves the chosen rolling preset and advances it when a newer release arrives; refresh failure retains the previous release. Query windows remain bounded to 500 calendar days.

The historical sample profile and frozen development/holdout/sparse-tail evaluation are unchanged. This is a reporting change; automatic scheduled ingestion, incremental processing and new publication metadata are not implemented or deployed by it. No new AWS processing, EC2 or IAM changes are part of this scope.

Validation for the rolling view: 21 focused checks passed, including arbitrary future dates, short-history clipping, cross-year release growth, consistent ranking/date filters, refresh failure retention and explicit completeness handling. The existing synthetic SQL, graph safety, exact-money and release checks remain included.


## Connected TRACE layout — 29 October 2026

The connected Streamlit source now adapts the offline TRACE concept's forest-green palette, persistent sidebar, monitoring insight card and case queue. Monitoring prioritises supported segment comparisons before the retained rolling daily trend. The volume/rate chart includes supported zero-label groups and a filtered-population baseline. Explanatory traffic/label shares use the full query baseline, never a capped preview total. Preview counts are explicitly named as such; low-support groups are inspectable but unranked. Exact monetary strings and descriptive intervals remain available in segment details.

Connected cases put the bounded case queue beside the graph, rule explanation and evidence counts; complete evidence export remains unchanged. Evaluation retains actual denominators and baseline comparisons. Release & provenance is a separate page with no additional data query. The offline `Visulization/` prototype and its invented fixtures remain separate; they are not used by the connected app. No detector, evaluator, SQL, frozen release, IAM or publication contract changes are included.

Local validation: 25 focused checks passed, including trends, navigation, baseline-derived explanations, graph safety, complete-source evidence, release retention and packaging the stylesheet into a temporary new release. Wide (1440px) and narrow (618px) browser layouts were checked against existing published outputs; no processing was rerun. Browser and AWS preview observations are recorded separately in the [task handoff](team-handoffs/2026-10-29-trace-connected-dashboard.md).

## Full-data release observed — 29 October 2026

A read-only AWS check in account `160885259244` / `us-east-1` (profile verified; no mutations, queries, job starts or deployments) found `full-20261028-v1` as the current publication pointer. The pointer SHA256 matches the manifest bytes, and the preparation, Q1, Q2 and evaluation quality reports all report `PASSED`. Preparation accounts for all **31,898,238** transactions and **35,230** labels; Q1 has 28 date partitions and Q2 has 28 daily snapshots. The frozen holdout evaluation reports **0.197% precision / 65.9% recall**, and typed eligible-attempt recovery is **122/122** versus 91.8% for the matched-volume amount baseline, meeting the frozen +5 pp target. No Glue run, Athena query, Step Functions execution or EC2 instance was active; the temporary dashboard stack is deleted and the dashboard workgroup is idle. Published data, Catalog tables and idle definitions are retained. This observation does not authorise rerunning processing or redeploying the dashboard. Scope, cost basis and cleanup state: [handoff](team-handoffs/2026-10-29-1130Z-kelvin-pipeline-status-verification.md).


## Fresh rerun preparation — 29 October 2026

US$90 is now a saved planning ceiling. The user clarified that only GitHub configuration was requested: **do not run the full pipeline or deploy services now**. New isolated definitions/driver and immutable full-v6 software are retained for future review; core processing files match full-v5 and the updated TRACE dashboard is included. Local suite/template/guard checks passed. An incorrectly started preparation attempt was cancelled and verified stopped, without any downstream stage or dashboard starting; cleanup is recorded in the [handoff](team-handoffs/2026-10-29-1215Z-kelvin-fresh-full-rerun.md). It is not a completed new cloud run and must not be resumed. Future paid work requires fresh scoped permission; previous successful results remain unchanged.
