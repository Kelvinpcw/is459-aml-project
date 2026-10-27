# Instructions for AI assistants

## Read before working

1. Read `README.md` and `Implementation/STATUS.md` for orientation/current scope.
2. Read `Proposal/Project_Proposal.md` and `Proposal/Architecture/Pipeline_Explanation.md` for requirements/target design.
3. Read relevant source, tests and `Implementation/results/` validation notes.
4. For deployment continuation, read `PROJECT_CHECKPOINT.md` plus the relevant `Implementation/aws/reviews/` record. Old approvals/browser notes are historical context, not a request to resume AWS work.

The current user's task sets the scope. Do not implement the whole backlog or provision architecture boxes merely because they appear in a document. Follow the latest dated, scoped evidence; `*-draft.json` filenames and old docstrings alone do not establish deployment state. Do not infer live AWS state from saved screenshots.

## Current baseline and limitations

- Preparation and Q1 were cloud-validated only for 1 September 2022: 4,465,985 transactions and 1,056 positive labels.
- Q2 was cloud-validated only for `[2022-09-01T00:00:00, 2022-09-01T00:01:00)`: 43,681 transactions, 15 fan-out cases and 840 evidence transactions. No pilot fan-in/cycle cases.
- `q2_detect.py` uses a bounded driver graph with a 50,000-window-row guard. It is not full-day/distributed graph detection. Design a scalable implementation; do not remove limits, claim scalability, or pretend independent minute windows preserve cross-window patterns.
- The local evaluator found no positive labels/eligible annotations in that minute; recall/recovery are not measurable. Do not claim detector effectiveness from this pilot or tune against holdout answers.
- Evaluator cloud run succeeded on 28 October 2026 for the frozen first minute; all four raw artifacts matched local predictions. Its single-run approval is consumed; do not rerun it. Dashboard, orchestration, shared publication and wider-window evaluation remain incomplete.

## AWS safety and authorisation

- Expected project account: `160885259244`; region: `us-east-1`. Each member configures their own authorised login/profile. Do not assume a particular local profile name or silently fall back to default credentials.
- Verify the chosen profile's STS account and region before cloud actions. Use `bash Implementation/scripts/check_aws_profile.sh YOUR_PROJECT_PROFILE`, replacing the placeholder with that member's actual profile name. Pass it explicitly because the script's legacy default is `is459`.
- Use explicit `--profile` and `--region` on AWS CLI commands. For local SDK calls, use an explicitly selected/verified session rather than ambient default credentials. Glue execution uses its reviewed service role, not laptop credentials.
- Repository setup and local tests do not authorise paid processing, deployments, IAM grants, destructive actions or resuming paused jobs. Establish the requested scope first; historical approval for one specific attempt is not blanket approval for new work or another teammate's runs.
- The saved prototype budget is US$1 total unless explicitly revised. The brief's US$250 course budget is not an automatic increase. Estimates are not billing caps. Flag material costs; do not introduce recurring schedules or idle paid compute.
- Do not rerun completed jobs/queries, recreate roles, overwrite immutable outputs or delete resources just to reproduce a screenshot. Check existing evidence first. Avoid unrelated shared-account resources.
- Do not commit credentials, session tokens, signed URLs, `.env` files or local AWS configuration. Inspect new logs/screenshots before pushing to this public repository.

## Preserve the data contracts

- Keep deterministic source IDs: original transaction-file checksum plus original 1-based CSV data-record ordinal. Preserve distinct records even when their field values look identical.
- Raw transactions repeat the `Account` header. Map by position to sender/receiver; join accounts on normalised bank ID **and** account number. Preserve raw identifiers; unknown enrichment must not silently drop transactions or multiply rows.
- Use exact decimal money (`decimal(38,8)` in the current contract). Preserve paid/received currencies separately; no float totals or unsupported cross-currency sums.
- Source times have minute precision and an unspecified timezone. Use the documented dataset-local policy. Respect exclusive window ends and snapshot cutoffs; never introduce future events into earlier snapshots.
- Q1 may read historical labels. Q2 must not read labels, pattern annotations, Q1 label-derived scores or evaluation artifacts. Preserve IAM separation and column/input allowlists; do not reuse the Q1 role for Q2.
- Q1 retains additive N/L counts by both currency dimensions and its declared grain. Filter population/baseline consistently, sum counts across dates, then calculate rates/lift. Never average daily rates or add overlapping grains.
- Q2 cases need stable IDs, rule/window/cutoff, account/entity participants, core evidence source IDs, and complete retrievable evidence despite display caps. Self-transfers remain in stored data but are excluded from graph motif edges. Structural leads are not proof of laundering or chronological return of identical funds.
- Evaluate on the declared eligible population, not only detected transactions. Incomplete annotations are not exhaustive case-level truth. Keep development/calibration (1–8 September), holdout (9–16), and sparse tail (17–28) separate; freeze settings before holdout evaluation.
- Propagate dataset/run/analysis identities. A future dashboard must pin all reads to one published release; partial failures must not replace the previous successful release.

## Code, tests and collaboration

- Make focused changes in `Implementation/jobs/`, `scripts/`, `sql/` and their tests. Preserve frozen `Implementation/releases/` and historical run/review artifacts. Create a new release/attempt when authorised rather than editing evidence to match changed code.
- Use a feature branch and a pull request. Do not revert others' changes, force-push shared history, or edit the same shared cloud job without coordination. Agree schemas/manifest/case contracts with downstream owners.
- Use synthetic fixtures for local tests; see `Implementation/SETUP.md`. A fresh clone intentionally lacks original/generated datasets. Do not fabricate missing inputs or report cloud/replay tests that were not run.
- Run relevant local tests for code changes. Keep golden frozen outputs unchanged unless a versioned contract change is explicitly intended/reviewed. Documentation changes need link/config checks, not paid AWS validation.
- Update `Implementation/STATUS.md` for changed completion state, and checkpoint/resource ledger for actual cloud actions. Record exact tested/deployed code, inputs, scope, output namespace, observed result, estimated cost and whether compute ended. Label proposals, local tests, saved evidence and fresh cloud observations separately.
