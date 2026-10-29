# Fresh isolated full-pipeline rerun

- **Owner:** Kelvinpcw, assisted by Codex.
- **Branch:** `feature/full-rerun-20261029`; [PR #13](https://github.com/Kelvinpcw/is459-aml-project/pull/13).
- **Updated at:** 2026-10-29T12:15:35.599745+00:00.
- **Status:** IN_PROGRESS — definitions/package validated and published; immutable upload/idle deployment next. No paid processing started.
- **Evidence kind:** local tests and private read-only preflight; detailed operational records stay private.

## Scope and coordination

The user explicitly requested a new full-pipeline rerun and required service deployment under the revised project ceiling, preserving the earlier requirement to stop expensive services after validation and retain S3. This is a new scoped attempt, not reuse of old approval/start markers. No overlapping open PR was present at preflight. The current operator owns this isolated attempt.

## Prepared changes

- New isolated job/role/workflow/temp namespace and new run/release identity; reuse the already ingested immutable full dataset and existing shared Catalog/workgroup. Previous jobs, outputs and the current successful release stay intact until conditional publication succeeds.
- Freeze a new full-v6 package. Core Q1/Q2/snapshot/evaluator/control files are byte-identical to full-v5; the package includes the updated connected TRACE dashboard and stylesheet. No detector/evaluator thresholds or chronological rules change.
- Deliberate upload/create/verify/start/status/stop phases. An exact private plan and template hash are required before cloud calls; start uses a one-time private request marker, fresh output checks and prior-pointer compare-and-swap. Budget status includes a conservative reserve and owned-run stop guard; estimates are not account billing caps.
- Five isolated Glue roles, one workflow role and a temporary dashboard role. Q2 retains label/annotation/Q1/evaluation denies. The dashboard has no inbound access, SSM-only access, a one-hour termination timer and delete-on-termination root disk. Deploy it only after successful publication; verify teardown afterward.

## Checks and observations

- Full existing synthetic suite: 115 tests passed after correcting a local Python driver/worker mismatch. The initial run failed because workers used system Python 3.13 with a 3.11 driver; no pipeline code was changed to hide this failure.
- Six focused rerun tests passed, including isolation/label denies, complete workflow/CAS, dashboard safeguards and rejection of wrong/unapproved plans before any identity/cloud call.
- Both new templates pass cfn-lint; Python compile and diff checks pass. No previous frozen package changed.
- Read-only preflight verified the explicit project account/region, existing publication/raw inputs and fresh output/resource names; no active owned compute was found in the inspected scope. Existing annotations match the frozen identity. Raw observations, counts, cost review and exact locators remain private with the operator.

## AWS boundary and next step

No cloud write, deployment or paid processing has occurred yet. The next step is uploading the new immutable package, creating the isolated idle definitions, verifying exact deployed grants/jobs/workflow, then starting the one approved full attempt. Publish an IN_PROGRESS update before starting. Retain old results; do not repeat legacy starts or alter unrelated shared resources. This record is coordination, not a reusable spending approval for another agent/member.
