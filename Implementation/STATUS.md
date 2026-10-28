# Implementation status

`main` contains the complete software path: shared preparation, Q1 summaries, distributed Q2 fan/cycle detection, a separate evaluator, conditional publication, a read-only dashboard, and on-demand AWS deployment/cleanup tooling. Architecture/configuration files and local tests alone do not establish a successful full cloud run.

The earlier full-v2 recovery passed **68 synthetic tests in 47.870 seconds**, including complete sharded evidence round-trips, deterministic retries, path/hash guards and publication failure retention. Both recovery templates pass cfn-lint. For full-v2, detection/aggregation/snapshot AST comparisons and byte-identical evaluator files establish that its recovery changes storage/execution only; frozen holdout settings were preserved.

The latest evaluator verification fix passed **87 synthetic tests in 53.120 seconds**, including exact frozen small-fixture result equivalence and physical-plan checks. Fan reconstruction now uses two directional equi-joins rather than an OR predicate that produces a Cartesian plan. Metric/calibration formulas, baseline settings, chronological splits and detector code are unchanged. The evaluator now also refreshes every join's right-side expression IDs to avoid Glue checkpoint-reference conflicts, with wide schema/type/rank and exact metric equivalence checks. Frozen full-v5 contains these corrections. Deployment authority and actual outcomes are recorded only in the private operational checkpoint; do not infer permission for another run from these source files. Completed outputs are reused, never regenerated merely for validation. The evidence-export CLI searches published snapshot partitions using locator columns, and shutdown tooling covers every known recovery execution. Both latest templates pass cfn-lint; the dashboard still has its one-hour terminate guard and unchanged grants.

The user explicitly requested **source-only publication**. New AWS run records, costs, measured results and the detailed checkpoint stay local. On the operator machine read `Implementation/data/aws-operations-20261028/PROJECT_CHECKPOINT.md`, its ledger and ignored `Implementation/aws/reviews/full-monitor-latest.json`. A fresh clone lacks those files. Previously committed pilot evidence remains historical; never infer live state or authority to start processing from it.

| Component | Implemented contract |
| --- | --- |
| Preparation | Deterministic original-file/record source IDs, positional repeated headers, bank/account enrichment, exact decimals and separated labels |
| Q1 | Additive daily counts at both currency dimensions; filtered common baseline, supported rates/lift and currency-specific amounts |
| Distributed Q2 | Fan-in/out and balanced two-hop 2–4-cycle joins over overlapping seven-day daily snapshots; explicit degree/capacity guards and complete evidence |
| Evaluator | Eligible population, unique exact annotation matching, development-frozen baseline/target, chronological holdout and separate sparse tail |
| Publication | PASSED reports, physical Parquet populations, hashes, immutable manifest and compare-and-swap current pointer; failures retain prior release |
| Dashboard | Pinned release, Q1 filters/charts, bounded case graphs with full downloads, honest evaluation and scope warnings |
| Operation | Isolated service roles, on-demand Step Functions, bounded jobs/queries, targeted recovery and private temporary EC2/SSM with cleanup |

Frozen releases are immutable. Full-v2 uses schema3 ZIP shards, reducing writes without changing cases/source evidence. The older first-minute driver detector retains its 50,000-row guard and is separate from distributed detection. Full-scale effectiveness, runtime/UI targets and cloud completion must be assessed from actual operator records. No team interviews, human contributions or narrated recordings are fabricated.

Read [setup](SETUP.md), [runbook](RUNBOOK.md), [completion plan](COMPLETION_PLAN.md), [proposal](../Proposal/Project_Proposal.md) and [checkpoint pointer](../PROJECT_CHECKPOINT.md). Known pilot findings: [Q1](results/Q1_VALIDATION.md), [Q2](results/Q2_VALIDATION.md), [evaluation](results/EVALUATION_CLOUD_VALIDATION.md).

The dashboard evaluation screen displays the exact holdout payment interval, precision alongside recall, both amount-baseline comparisons, the eligible annotation denominator and frozen recovery target. These are distinct measures; attempt recovery does not establish better individual-payment precision or recall. The immutable `releases/dashboard-v1` package contains this presentation change. Eight release/dashboard checks and the updated temporary-dashboard template validation pass.
