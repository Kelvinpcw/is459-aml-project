# Targeted recovery review — 28 October 2026

The authorised whole-project task and US$30 total ceiling remain active. Original execution `full-20261028-v1` failed after the detector's export metadata join raised Spark `INTERNAL_ERROR` / conflicting `case_id` references. The parallel Q1 job was cancelled by orchestration. Preparation and sanitised manifest succeeded and will be reused. All original full jobs are terminal; prior publication remains the pilot.

## Changes

New immutable code release `Implementation/releases/full-v2/` fixes export join expression IDs and packs full case/evidence members into bounded ZIP shards (schema3). It retains all source transactions, including parallel payments, beyond the existing graph preview. Per-member SHA256 and row counts are checked by dashboard/download CLI. Deterministic executor retries accept only byte-identical shards. Display caps are unchanged. This reduces per-case S3 PUT overhead without changing detection.

AST comparisons prove `DistributedConfig`, `detect`, `schedule`, `run_snapshots` and Q1 `aggregate_daily` are identical to frozen full-v1. Both evaluator files are byte-identical. No holdout labels/annotations were used for this correction; no threshold or acceptance-target tuning occurred. 68 local tests pass in47.870s, including the formerly failing export join after Parquet write, full sharded round-trip, duplicate executor retry, hashes and path isolation. Both recovery templates pass cfn-lint.

New source payload SHA `03318a47e61487243680591a3a1b2f44b57307b2823803d815237eb637d2fb42`. Each payload/hash/location is in `releases/full-v2/manifest.json`. New scripts use `scripts/full-v1/recovery1/`, an immutable subrelease inside the already approved role prefix. The new dashboard package is `published/software/full-v2/dashboard.zip`, readable under its already approved `published/*` grant. No original frozen file or cloud object is overwritten.

## Deployment scope

Update only the idle full stack's four downstream job script/config references and add `is459-aml-full-recovery1`, using the existing workflow role. All six original IAM resource blocks are exactly unchanged. The dashboard recovery template changes its bootstrap package location only; its role/trust/policies are exactly unchanged from the user's explicit approval. No new IAM grants or recurring schedules.

Recovery starts at parallel Q1/Q2 and then Catalog → evaluation → publication. It does not run preparation or regenerate the manifest. Q1 and Q2 use fresh nested `attempt=recovery1/` output/quality prefixes beneath their original approved analyses; old partial outputs/reports remain immutable. Evaluator output and full release have not been created, so their original fresh identities remain. Quality failures retain the previous published release; publication uses the captured pilot pointer ETag.

## Costs and operation

Original full compute estimate US$1.052334 plus prior development US$0.280623. Remaining timeout maxima: Q1 US$1.65, Q2 US$8.80, evaluator US$1.65, two controls US$0.293334. Add US$10 projected output guard and US$1 overhead reserve: conservative total **about US$24.73**, below the US$30 ceiling. Estimates are not billing caps. The monitor includes both attempt histories and cancels active owned compute when its guarded total reaches US$28. Retain no expensive idle services; temporary EC2 is still unlaunched.

Prepared exact templates: `deployment/recovery1-stack.json`, `dashboard-recovery1-stack.json`. Driver `recover.py` separates upload, idle update and once-only start, checks original deployed template / unchanged IAM / terminal prior jobs, and writes request markers before starting. Check actual stack/code verification before the start phase.
