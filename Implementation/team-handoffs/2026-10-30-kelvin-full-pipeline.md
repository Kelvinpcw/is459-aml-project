# Task: fresh ingestion-to-EC2 run and removal of old generated outputs

- **Owner:** Kelvinpcw with Codex
- **Branch / PR:** `agent/codex-full-run-20261030`; PR pending
- **Updated at:** 2026-10-30 (+08:00)
- **Status:** PLANNED
- **Evidence kind:** source checks, fresh inventory and explicit current run authorisation

## Scope and coordination

The user explicitly requested one new whole pipeline run from ingestion through visualization on EC2, removal of past S3 run outputs, and detailed setup/run instructions. The existing planning ceiling remains unchanged; the current request grants this new attempt, not reuse of a revoked attempt. The operator's private plan records the estimate, reserves, exact identities and approval evidence. Estimates/timeouts are not billing caps.

Only the operator's maintained AML stack, source staging and generated output paths are included. Open PR #18 is this operator's completed definition cleanup, not another owner's work. No other open PR was observed. The new run updates the maintained five jobs rather than adding duplicates; shared Catalog database/workgroup are reused. No recurring schedule or unrelated shared-account resource changes.

## Changes and checks

- New `build_run30.py` / `run30.py` define a fresh ingestion namespace/run on the maintained stack. Deployment uses an inspected change set and rejects resource additions/removals/replacements. Exact deployment verification and one-start private markers are required.
- Reuse immutable full-v6 processing software; frozen detector/evaluator settings stay unchanged. The stopped prior attempt remains consumed and revoked.
- `upload_input.py` supports an explicit scoped new raw prefix and private observation path. Complete stable-ID input artifacts are uploaded with conditional completion and streaming/server-part checksum verification. Original source records/checksums/ordinals remain unchanged.
- Ten local deployment/plan/isolation/dashboard checks passed. Both new templates will be validated before apply; no cloud success is claimed yet.
- Old generated outputs are inventoried privately. Deletion is deferred until the new release and EC2 dashboard are verified, retaining a working previous publication on failure. Preserve original/raw source, annotations, required software and current new outputs. Do not delete a bucket that is still used.

## AWS scope and cleanup

Read-only source and output inventory completed with the explicit verified project profile/region. No run/deployment/upload/deletion has started at plan publication. New compute will be monitored against the private cost reserve; stop requests require terminal verification. The private EC2 dashboard has no inbound ports, uses SSM and a one-hour terminate guard, with root disk deletion. No processing retries or automatic recovery are authorised. S3 cleanup must use the exact pre-run object inventory with fresh pointer and object-identity checks.

## Next teammate / agent

- Publish plan and mark IN_PROGRESS; upload/verify fresh ingestion, upload/verify software, inspect/apply the maintained-stack change set, verify, start once and monitor.
- After successful publication, launch/verify EC2 visualization; delete old generated S3 outputs and stale Catalog tables only when proven superseded, then verify and publish outcome. Keep operational identities and measurements private.
- Document the actual end-to-end setup, repeatable commands, access and shutdown steps. Do not claim success until directly verified.
- GitHub sync: pending draft PR and push. No other owner should start or update these shared jobs until this session is terminal.
