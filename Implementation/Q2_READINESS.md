> Historical pilot readiness/review. Statements below describe that earlier scope, not the current backlog or fresh run approval. Use [STATUS.md](STATUS.md) and [VERIFY_PROGRESS.md](VERIFY_PROGRESS.md) for current continuation.

# Q2 bounded development prototype — deployed and verified

Updated27October2026. **The approved Q2 role and first cloud run are complete. All15 cloud cases and all15 Athena index rows match the frozen replay. No active project compute/query.** Read `results/Q2_VALIDATION.md` and `../PROJECT_CHECKPOINT.md` for current status; below are the reviewed contracts and historical first-run plan. Do not rerun or recreate resources.

## Concrete first run

- Account 160885259244, us-east-1; job `is459-aml-q2-dev`.
- Immutable preparation v2: `ibm-hi-medium-b1b99c68b765580f` / `dev-20220901-v2`.
- Analysis `q2-dev-20220901-m00-v1`; dataset-local window **2022-09-01 00:00:00 inclusive to 00:01:00 exclusive**, snapshot cutoff 00:01:00. The source timestamps have minute precision and an unspecified timezone. UTC is only the fixed Spark parsing convention.
- Glue 5.1, two G.1X workers, standard execution, 15-minute timeout, zero retries, concurrency one. No notebook, interactive session, VPC, crawler, schedule or optional metrics.
- The first chronological minute was chosen using label-free transaction/edge workload sizes. It is not selected for positive-label or pattern-annotation yield.

At AWS's checked US$0.44/DPU-hour pricing example, two DPUs for 15 minutes estimate **US$0.22 compute**, plus any separately billed startup/overhead, S3 and logs. Previous Glue usage estimate US$0.207778; combined nominal compute estimate after a full 15-minute run is about US$0.43. This is not an account-wide hard billing cap. Keep the user's US$1 total prototype budget and flag material changes before execution. Source: https://aws.amazon.com/glue/pricing/ (checked 26 October 2026).

## Input isolation

`make_q2_input_manifest.py` is a trusted handoff builder. It may read the passed preparation report and exports only dataset/run identity, accepted row count, label-free fact schema, decimal precision, timestamp policy and the enriched transactions URI. It strips labels, annotation paths, reference counts and the original source manifest. The dedicated JSON is `aws/manifests/q2-input-v2.json`; Q2 rejects the full preparation report or additional input keys.

Planned S3 handoff:
`s3://is459-aml-g2team7-160885259244-us-east-1/manifests/detector-inputs/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/manifest.json`.

Enriched facts already contain both endpoints' account/entity mappings and explicit unknown flags. No separate account map, raw ingestion, labels, Patterns.txt, Q1 outputs or evaluator output is read by Q2. Unknown entities remain as explicit unknowns; inconsistent mappings fail.

Proposed role **AWSGlueServiceRole-is459-aml-q2**, policy **is459-aml-q2-data-access**, trusts only `glue.amazonaws.com`. Reads only preparation-v2 transaction facts, the exact sanitized manifest and exact Q2 script. Can manage only this analysis's `gold/cases/` and `quality/q2/` output plus `temporary/q2/`, and write `/is459/aml/q2/` logs. Explicitly denies reading raw/reference/preparation-report/Q1/evaluation zones. No IAM, Catalog, Athena, EC2 or execution-control permissions. `aws/q2-permissions-policy.json`, `q2-trust-policy.json` and `q2-job-draft.json` are the exact local review artifacts.

The computer-use tool's confirmation policy requires confirmation at action time for creating materially new security-sensitive access, even when general project permission was previously given. The user approved this exact role and single test with “go ahead” on27October; the approval is consumed and deployment/verification complete. Do not re-request existing grants. Future materially new grants still require action-time confirmation.

## Rules and completeness

`jobs/q2_detect.py` and frozen `releases/q2-v1/q2_detect-v1.py` implement rule version **structural-v1**:

1. Spark checks the full immutable preparation population, actual fact columns, dataset/run identity, non-null times and decimal(38,8) amounts. It filters the declared window/cutoff before guarded collection.
2. A node is the pair **(normalized bank ID, account number)**, encoded as a JSON pair to avoid delimiter collisions. A non-self directed pair is one graph edge; all its distinct source transactions remain evidence. Identical-looking records with distinct source IDs are retained.
3. Fan-in/out requires **at least five distinct non-self counterparties** in the fixed window. One case includes the hub, all qualifying peers and all transactions on those directional edges. Peer-to-peer/context edges are not silently added to trigger evidence.
4. Cycles are simple directed structural cycles of **2–4 distinct accounts**. Rotations collapse to one case; opposite directed orientations remain distinct when supported. Exact strongly-connected-component pruning removes only regions that cannot contain a directed cycle. A cycle does **not** claim chronological return of funds, balanced amounts or laundering.
5. Every case has a stable hash of dataset/preparation/rule/window/cutoff/pattern/nodes. Retry analysis IDs change storage identity but not logical case identity. Each bundle preserves participants, entity details, trigger parameters, directed edges, times, currency/format and all supporting source IDs/transactions. Decimal values are JSON strings, not binary floating-point values.

**Scope is deliberately bounded.** Maximum 50,000 window transactions, 20,000 distinct non-self edges, 250,000 cycle-neighbor expansions, 500 cases, 1,000 participants per case, 2,000 evidence transactions per case, 100,000 total evidence rows including overlap, and 2 MB per JSON bundle. Every exceeded limit fails the analysis; no top-K clipping, silent truncation or partial PASSED output. This driver graph core is suitable for this reviewed small development window only. It is not a scalable full-day/full-dataset implementation. Wider scope needs reviewed windowing/distributed processing and fresh capacity estimates.

## Output contract

Base: `gold/cases/dataset_version=ibm-hi-medium-b1b99c68b765580f/run_id=dev-20220901-v2/analysis_id=q2-dev-20220901-m00-v1/`.

- `bundles/<case_id>.json`: schema described above, with exact supporting transaction evidence and a structural-lead interpretation.
- `case_index/window_date=2022-09-01/`: Parquet, explicit types. String fields `dataset_version,run_id,analysis_id,case_id,pattern_type,bundle_uri`; integer counts `participant_count,unique_edge_count,evidence_transaction_count`; timestamps `window_start,window_end,snapshot_cutoff,first_event_time,last_event_time`; date partition `window_date`.
- `quality/q2/<same namespace>/report.json`: PASSED only after all bundles and index writes succeed; records config, statistics, complete-window status and schema. Failed attempts remain FAILED/partial and cannot reuse the namespace. Conditional S3 writes and Spark error-if-exists protect against accidental replacement. Never publish a partial attempt.

Empty case sets have an explicit index schema and PASSED zero-case report; consumers must use that schema/manifest instead of inferring columns from files. The shared release gate and dashboard are still unimplemented, so these outputs are not a published product release.

## Verified locally

All **30 tests passed**: previous 18 plus 12 Q2 tests. They cover distinct-degree semantics, duplicate evidence preservation, composite identity, 2/3/4 cycles, reverse orientation, an independent exhaustive cycle oracle on 15 small random graphs, snapshot/end boundaries, input leakage rejection, stable IDs, unknown entities, all processing guards, exact decimals, and Spark case-index Parquet including zero cases. Runtime: PySpark 3.5.6, Python 3.11, Java 21; not the cloud Glue runtime.

The checksum-verified real-input replay scanned the selected 4,465,985 transactions and 2,087,786 account rows in a trusted local preparation harness. Only an explicit label-free projection reaches the production detector core. Results: **43,681 scoped transactions; 31,702 self transactions excluded from graph edges; 11,979 non-self transactions; 11,760 distinct non-self edges; 15 fan-out cases; no fan-in/cycles; 840 unique supporting transactions, all independently reconciled; no unknown mappings or truncation**. All 53,557 observed endpoints include self-only accounts. Largest bundle 218,819 bytes; total 602,619 bytes. This does not measure detection precision/recall or prove laundering.

Evidence: `aws/reviews/q2-local-replay-m00-v1.json`, `q2-workload-profile.json`; complete local bundles in `data/q2-local-m00-v1/`. See `results/Q2_LOCAL_VALIDATION.md`.

## Historical deployment recipe — completed; do not rerun

1. Re-read the authorization record, verify exact hashes and correct signed-in AWS account. Never use the differently authenticated local AWS CLI.
2. Use the already-created verified Q2 policy; create the reviewed Glue-only role, attach exactly that policy and verify both. Upload the exact manifest and frozen script to their planned paths.
3. Save the reviewed job definition with the Q2 role, code, log/temp paths and all window arguments; verify persisted values before clicking Run once. Do not clone unchanged Q1 label/report parameters into Q2.
4. Observe to terminal state. Stop on failure; no automatic retry. Read the Q2 quality JSON and reconcile cloud case inventory/counts and exact bundle hashes against the local replay before registering/querying the case index. Any discrepancy needs investigation, not a changed expected result.
5. Register the explicit case-index schema and partition in the existing limited Athena workgroup only after PASSED. `sql/q2_catalog_draft.sql` and `q2_validate_cases.sql` are local drafts, not executed.
6. Keep all project compute/query runs terminal at handoff. Update cost ledger, results and checkpoint. Then implement separate evaluation, shared release/published manifest, dashboard and orchestration; these remain outstanding.
