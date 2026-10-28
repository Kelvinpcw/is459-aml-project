# Run and demonstrate the complete pipeline

Current implementation/results: [STATUS.md](STATUS.md). Cost/resource state: follow the [checkpoint pointer](../PROJECT_CHECKPOINT.md) to the ignored private operator checkpoint/ledger. The tracked ledger is historical. New full-data definitions are isolated from the validated pilot. A configuration file or local test is not evidence of cloud completion.

## Authentication and budgets

Every teammate uses their own authorised profile. This machine's project profile is `IS-459-BDA`; its default profile belongs to a different account. Verify before any cloud action:

```bash
bash Implementation/scripts/check_aws_profile.sh IS-459-BDA
```

Expected account `160885259244`, Region `us-east-1`. Always select profile/region explicitly. Never copy credentials into Git, job arguments, screenshots or another person's machine. Local SDKs verify the selected session; Glue/EC2 use their reviewed execution roles.

On 28 October the user requested project completion and authorised **US$30 total for the final full-data phase once implementation/checks are ready**. No recurring schedule is enabled. Timeout-limited maximum compute estimate is US$14.19 at the checked US$0.44/DPU-hour example, plus startup/applicable overhead. A separate US$10 conservative output estimate guard checks projected 30-day S3 storage and PUTs before every snapshot export. Other requests, logs, retained storage, the short dashboard session and prior development charges are separate. These estimates/guards are not a hard billing cap or finalized invoice. Stop/inspect if observed cost approaches the authorised ceiling.

## Local checks and dashboard

Use Python3.11/Java21 and the dependencies in `requirements.txt`. Tests use synthetic fixtures and never start AWS processing. UTC here is a fixed internal parsing convention; source timestamps have no specified timezone.

```bash
TZ=UTC SPARK_LOCAL_IP=127.0.0.1 python -m unittest discover -s Implementation/tests -v
cfn-lint Implementation/deployment/full-pipeline-stack.json Implementation/deployment/dashboard-stack.json
AML_AWS_PROFILE=IS-459-BDA streamlit run Implementation/dashboard/app.py
```

The app reads `published/current.json` once per refresh, verifies its immutable release manifest hash, and pins every table, identity, snapshot, metrics and bundle read. Q1 amounts stay in the selected currency side; baseline filters match counts. The default main reporting period ends16September; the sparse tail is selected separately. Ranking support sensitivity is available only in development. Cases show at most100nodes/500edges/200evidence rows, while downloads retain complete evidence.

## Full input and release packaging

Original data and generated `Implementation/data/` are excluded from Git. The existing ingestion helper creates the complete date-selected copy without changing originals. Source IDs remain original transaction-file SHA256 plus original1-based CSV record ordinal. The first final copy uses dates1September inclusive through29September exclusive and reconciles31,898,238records/35,230labels, zero outside/quarantined ingestion rows. Do not regenerate or reupload an already verified copy just for a screenshot.

`deployment/build_bundle.py` freezes a **new** `releases/full-vN/` directory with per-file hashes and deterministic ZIPs. Existing frozen directories must never be edited. Preserve the tested source commit, package manifest and exact CloudFormation parameters in the review record. The final stack reads original frozen preparation-v2 code, unchanged Q1, and the new separately versioned Q2/evaluator/control code.

## On-demand AWS execution

For the original full attempt, the deployment driver requires a profile and a deliberate phase. `upload` only uploads immutable code, `create` creates idle definitions/roles and the on-demand workflow, and `start` starts one named full attempt. The user must have authorised that concrete scope and cost first. Do not run these steps for onboarding or repeat a completed attempt.

```bash
python Implementation/deployment/deploy.py --profile IS-459-BDA --phase upload
python Implementation/deployment/deploy.py --profile IS-459-BDA --phase create
python Implementation/deployment/deploy.py --profile IS-459-BDA --phase status
# Only once the stack is CREATE_COMPLETE and full raw inputs/code are verified:
python Implementation/deployment/deploy.py --profile IS-459-BDA --phase start
python Implementation/deployment/deploy.py --profile IS-459-BDA --phase status
```

Workflow: preparation → sanitised detector manifest → parallelQ1/Q2 → explicit Catalog tables/partitions → separate development evaluation → immutable calibration → holdout and sparse-tail evaluation → release gate and conditional publication. There are no automatic job retries. Each job has concurrency1 and a timeout. A failed stage/partial export never publishes; the previous successful release remains available. The current pointer uses compare-and-swap against its pre-run ETag so a concurrent publication is not silently replaced.

New jobs are `is459-aml-full-{prepare,risk,detect,evaluate,control}`; workflow is `is459-aml-full-pipeline`. The `CodeVersion`, `RunId` and `ReleaseId` parameters identify the attempt. Before any recovery, inspect the actual failure and retained completed outputs; use a new version/namespace for changed code and do not rerun completed stages without a reason. Never overwrite the old pilot or shared Q1 GitHub connection.

## Detection and evaluation contracts

The new detector uses Spark fan aggregation and pruned2–4cycle joins. Every daily snapshot reads a complete overlapping7day lookback, preserving patterns across minutes/days. Source history before1September is unavailable and early snapshots explicitly flag incomplete history. Cycles are exhaustive only in the declared degree-eligible induced graph; degree exclusions and expansion guards are reported. A guard failure fails the attempt rather than clipping cases. Fan evidence retains all non-self counterparties/parallel source records.

The failed full-v1 export used schema2 (one case header plus evidence chunks). The tested full-v2 recovery uses **schema3**: complete headers and evidence chunks packed into bounded immutable ZIP shards, with a case-index member locator and per-member SHA256/row counts. This reduces storage requests without changing motifs, thresholds, IDs or evidence. The app/CLI resolve only members under the pinned case/release. A case can span multiple shards; no transaction is clipped. The frozen pilot's original bundles and failed full-v1 files remain unchanged.

For the diagnosed first full failure, `deployment/recover.py` separates immutable upload, idle stack update, status and once-only recovery start. `verify_recovery.py` checks exact cloud definitions, original role grants, reusable preparation and empty new attempt prefixes. Recovery starts at parallel Q1/Q2, then Catalog/evaluation/publication, using nested `attempt=recovery1/` outputs. Do not rerun its start or preparation. Read the checkpoint/request markers before any action. The unchanged-role comparison is a requirement of these recovery definitions.

The evaluator validates full fact/label joins and frozen case identities, pair topology and complete evidence before scoring. It selects only snapshots available within each reporting period. Development1–8September, holdout9–16 and sparse17–28 are non-overlapping scoring populations; older context can support a case but cannot enter a later period's transaction denominator. Future snapshots cannot create earlier alerts. References require exact unique source matching; ambiguous/repeated/missing matches are excluded and audited. Typed recovery requires the correct motif/hub/oriented cycle and at least80% of reference source transactions in one case.

A baseline alert fraction per currency is frozen from development alert volume before holdout scoring. A separate matched-volume amount diagnostic uses exactly the detector’s per-currency alert count, so core comparisons also control for alert volume. The predeclared recovery margin target is5percentage points against that matched-volume comparison. Holdout/tail never tune it or detection settings. The predeclared improvement target and whether it was met are reported; unsuccessful/no-denominator results are not hidden. Annotation absence does not prove a case false.

## Evaluator-only continuation after shutdown

`deployment/evaluation-resume1-stack.json` is a prepared definition, not evidence of deployment. It starts at evaluation, then publishes; it never reruns preparation/Q1/Q2/Catalog. The evaluator adds `--attempt-id` to write a fresh nested namespace, and control accepts only the exact report under the same analysis/evaluation. Scoring/calibration functions and holdout target are unchanged. All original IAM resource blocks are retained.

`deployment/resume_evaluation.py` separates upload/update/verify/start/status. A start requires a recorded exact-scope approval, verified deployment and one-time request marker. Obtain the current scoped approval after a pause; old attempt approvals are consumed. Never restart the failed/aborted original executions. The source-only public repository deliberately lacks private authorization/run markers.

For final validation, `dashboard-validation-stack.json` adds a one-time60minute shutdown and terminate behavior to the existing private dashboard. Root disk deletes on termination. Delete its stack sooner after validation and verify instance/disk/IPv4 removal; do not rely on the timer as proof of cleanup. The stop phase now aborts all known workflow markers before stopping active full jobs. Verify terminal states afterward.

A follow-up keyed verification correction is prepared as `evaluation-keyed1-stack.json` / frozen full-v4. It replaces the fan reconstruction OR join with separate incoming/outgoing equi-joins; equivalent result and no-Cartesian plan tests are required. Use `resume_evaluation.py --attempt evaluation-keyed1` only for its explicitly approved new attempt. The driver uses separate approval/request/start records and preserves all old attempts. Original detector/scoring formulas/holdout settings are unchanged. The current operator checkpoint, not this runbook, determines the next authorised stage.

## Private dashboard and demo

Create the separate temporary dashboard stack only when ready to demonstrate. It uses an existing default VPC/subnet, one`t3.small`, an encrypted8GB root disk with delete-on-termination, IMDSv2 and no inbound security-group rules. Access is through SSM port forwarding, not a public web port. Its role reads published analysis and metrics only, never raw facts/labels, and writes only its restricted Athena result prefix. The dashboard workgroup has a512MB/query scan cutoff and app queries cancel after30seconds.

```bash
python Implementation/deployment/deploy.py --profile IS-459-BDA --phase dashboard \
  --dashboard-template dashboard-recovery1-stack.json
python Implementation/deployment/deploy.py --profile IS-459-BDA --phase dashboard-status
aws ssm start-session --target INSTANCE_ID --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8501"],"localPortNumber":["8502"]}' \
  --profile IS-459-BDA --region us-east-1
```

For the reviewed bounded validation use `--dashboard-template dashboard-validation-stack.json` instead of the recovery-only template. Open `http://127.0.0.1:8502`. Replace `INSTANCE_ID` with the observed stack output. Verify service health and active SSM registration first; never assume a newly launched instance is ready.

Demo checks: explain supported Q1 comparisons with the common baseline and low-support warning; change currency side/date/format without mixing populations; inspect a selected Q2 snapshot/rule/participants/entities and full source evidence; display honest evaluation denominators and cycle/history limitations; refresh one published release. Record measured initial/cached timings and unmet acceptance targets rather than claiming proposed targets were achieved.

For a case larger than the50MB in-app ZIP download limit, download its evidence manifest and use the complete export CLI; no evidence is truncated:

```bash
AML_ATHENA_WORKGROUP=is459-aml-dashboard python Implementation/scripts/export_case.py --profile IS-459-BDA \
  --release-id RELEASE_ID --case-id COMPLETE_CASE_ID \
  --snapshot-end EXACT_PUBLISHED_CUTOFF --output Implementation/data/case-export-new
```

`--snapshot-end` is an optional exact cutoff from the pinned published schedule. With it, the CLI queries only that snapshot; without it, the CLI searches declared partitions one at a time. Queries select only the case locator fields. Evidence is still downloaded and checksum-checked in full.

## End-of-run cleanup

Observe the workflow and every known job/query to terminal. Use the driver's`stop` phase if authorised compute is still running; verify cancellation completes. Delete only the temporary dashboard stack, then verify instance termination and deletion of its attached root volume/public IPv4 allocation:

```bash
python Implementation/deployment/deploy.py --profile IS-459-BDA --phase remove-dashboard
```

Retain S3 data/code/results, published release, Catalog/workgroup metadata and idle job/workflow definitions for reproducibility. Do not delete unrelated shared-account resources. Update the checkpoint/ledger with actual IDs, observed counts/metrics, runtime, estimated charges, cleanup and remaining limitations.
