# Instructions for AI assistants

## Read before working

1. Read `README.md` and `Implementation/STATUS.md` for orientation/current scope.
   Read `Implementation/AWS_HANDOFF.md` and dated records in `Implementation/team-handoffs/` for shared AWS context. Check open GitHub PRs for newer, unmerged handoffs; `main` alone may lag another teammate's work.
2. Read `Proposal/Project_Proposal.md` and `Proposal/Architecture/Pipeline_Explanation.md` for requirements/target design.
3. Read relevant source, tests and `Implementation/results/` validation notes.
4. For deployment continuation, read `PROJECT_CHECKPOINT.md` plus the relevant `Implementation/aws/reviews/` record. Old approvals/browser notes are historical context, not a request to resume AWS work.

The current user's task sets the scope. Do not implement the whole backlog or provision architecture boxes merely because they appear in a document. Follow the latest dated, scoped evidence; `*-draft.json` filenames and old docstrings alone do not establish deployment state. Do not infer live AWS state from saved screenshots.

## Current implementation and historical validation limits

- The software path on `main` includes preparation, Q1, distributed Q2, evaluation, conditional publication, a pinned Streamlit dashboard and on-demand orchestration/cleanup. Implemented code and local tests do not establish full cloud completion or effectiveness. `Implementation/STATUS.md` is the implementation summary.
- Previously published pilot preparation/Q1 validation covered only 1 September 2022: 4,465,985 transactions and 1,056 positive labels.
- Previously published pilot Q2 validation covered only `[2022-09-01T00:00:00, 2022-09-01T00:01:00)`: 43,681 transactions, 15 fan-out cases and 840 evidence transactions. No pilot fan-in/cycle cases.
- The frozen pilot `q2_detect.py` uses a bounded driver graph with a 50,000-window-row guard; preserve it unchanged. The separate distributed implementation uses overlapping seven-day daily snapshots, fan aggregation and degree-eligible bounded cycle joins. Do not describe the pilot as distributed or pretend independent minute windows preserve cross-window patterns.
- The local evaluator found no positive labels/eligible annotations in that minute; recall/recovery are not measurable. Do not claim detector effectiveness from this pilot or tune against holdout answers.
- The published pilot evaluator run succeeded on 28 October 2026 for the frozen first minute; all four raw artifacts matched local predictions. Its single-run approval is consumed; do not rerun it. Later detailed operational records remain private; consult the shared handoffs and the relevant operator before drawing conclusions or continuing AWS work.
- `Visulization/` is an independent offline dashboard concept using invented fixtures, not the AWS-connected dashboard or measured project results.

## AWS safety and authorisation

- Expected project account: `160885259244`; region: `us-east-1`. Each member configures their own authorised login/profile. Do not assume a particular local profile name or silently fall back to default credentials.
- Verify the chosen profile's STS account and region before cloud actions. Use `bash Implementation/scripts/check_aws_profile.sh YOUR_PROJECT_PROFILE`, replacing the placeholder with that member's actual profile name. Pass it explicitly because the script's legacy default is `is459`.
- Use explicit `--profile` and `--region` on AWS CLI commands. For local SDK calls, use an explicitly selected/verified session rather than ambient default credentials. Glue execution uses its reviewed service role, not laptop credentials.
- Repository setup and local tests do not authorise paid processing, deployments, IAM grants, destructive actions or resuming paused jobs. Establish the requested scope first; historical approval for one specific attempt is not blanket approval for new work or another teammate's runs.
- The earlier US$1 prototype budget and later US$30 final-phase approval are historical, scoped approvals, not fresh spending authority for another agent. Obtain the current user's explicit scope and remaining budget before paid work. The brief's US$250 course budget is not an automatic increase. Estimates are not billing caps. Flag material costs; do not introduce recurring schedules or idle paid compute.
- Do not rerun completed jobs/queries, recreate roles, overwrite immutable outputs or delete resources just to reproduce a screenshot. Check existing evidence first. Avoid unrelated shared-account resources.
- Do not commit credentials, session tokens, signed URLs, `.env` files or local AWS configuration. Inspect new logs/screenshots before pushing to this public repository.

## Mandatory shared handoff and push

The user requires GitHub to carry enough current context for teammates and their AI assistants. Updating only a local checkpoint or giving a chat summary is **not a completed handoff**. Follow `Implementation/AWS_HANDOFF.md`.

- Before authorised AWS mutations/paid processing, coordinate ownership and publish a sanitised `PLANNED` handoff on your branch with a draft PR. Set it to `IN_PROGRESS` when work starts. This is coordination, not a lock or permission to run. Read existing open PRs and get the relevant owner's confirmation for shared resources; an unanswered PR is not consent.
- After **every AWS work session**, including read-only observations, failed/aborted attempts, deployments, IAM changes, queries, publication and cleanup, create/update your dated record in `Implementation/team-handoffs/`. Group related read-only calls in one session record; do not commit once per API call. State what was actually observed, when, by whom, code/input/run identities, output ownership, outcome, cost basis, compute/cleanup state, blockers and the next safe step. Use `unknown`/`not verified` when appropriate.
- Update `Implementation/STATUS.md` when completion state changes and tracked source/configuration when it changes. Keep raw reports, detailed operator checkpoints, new ledger entries, credentials and sensitive data local/ignored. A short, manually sanitised team handoff is now required in Git; this does not authorise uploading private operational records.
- For local-only tasks, update the relevant docs/tests and publish the task branch/PR too; explicitly say `AWS: none` rather than implying cloud validation.
- Review the exact diff for secrets/private data, run relevant local checks, stage **explicit paths**, commit, push your feature branch, and create/update a PR. Verify the remote branch commit matches your local commit. Report the commit, PR URL, checks actually run, AWS effects/costs and remaining blockers to the user. Never merge your own PR or push directly to `main`.
- If GitHub/auth/network problems or the user's instructions prevent a push, keep the local handoff, state **NOT SYNCED TO GITHUB** with the exact blocker, and do not claim teammates can see it. Do not force-push, overwrite others' work, or leak secrets to make a push succeed.
- If publication fails before cloud changes, pause new work until coordination is restored. Never delay necessary authorised stop/cleanup actions just to update Git; make the system safe first, then record and publish the observed outcome. Do not start additional paid work while a previous session's handoff remains unpublished.

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

## Team workflow (humans and AI agents)

This repository is shared by the whole team and is public. Teammates and their AI assistants both push here; treat every branch, work tree and cloud run as potentially someone else's work.

- Work on your own branch (`feature/<task>` or `agent/<tool>-<task>`), push it and open a pull request. Do not commit to `main` directly, and do not merge your own work without a teammate's review.
- Do not run `git add .` or `git add -A`. The working tree may contain another person's uncommitted edits, local-only AWS records or sync artifacts. Stage explicit paths only.
- Before starting, `git fetch origin` and rebase or merge `origin/main` into your branch. Long-lived branches drift and produce conflicting evidence files.
- `Implementation/aws/reviews/*`, ledger entries for new runs and the detailed checkpoint are local-only by policy (not all legacy tracked files are ignored). Do not force-add private records or stage a changed legacy ledger. Publish only a sanitised summary under `Implementation/team-handoffs/`; this repository is public.
- macOS/iCloud sometimes creates byte-identical `Name 2.md` copies. They are ignored by `* 2.*`; delete them instead of committing them, and never let a `test_* 2.py` reach pytest.
- A branch does not isolate AWS. Before any cloud action, confirm nobody else is using the same job or output prefix, and use your own paths and run/analysis IDs.
- Pull requests should state what changed, which contracts were touched, the tests actually run, any AWS resources or costs affected, and whether compute was stopped.

## Code, tests and collaboration

- Make focused changes in `Implementation/jobs/`, `scripts/`, `sql/` and their tests. Preserve frozen `Implementation/releases/` and historical run/review artifacts. Create a new release/attempt when authorised rather than editing evidence to match changed code.
- Do not revert others' changes, force-push shared history, or edit the same shared cloud job without coordination. Agree schemas/manifest/case contracts with downstream owners.
- Use synthetic fixtures for local tests; see `Implementation/SETUP.md`. A fresh clone intentionally lacks original/generated datasets. Do not fabricate missing inputs or report cloud/replay tests that were not run.
- Run relevant local tests for code changes. Keep golden frozen outputs unchanged unless a versioned contract change is explicitly intended/reviewed. Documentation changes need link/config checks, not paid AWS validation.
- Update `Implementation/STATUS.md` for changed completion state, and checkpoint/resource ledger for actual cloud actions. Record exact tested/deployed code, inputs, scope, output namespace, observed result, estimated cost and whether compute ended. Label proposals, local tests, saved evidence and fresh cloud observations separately.
