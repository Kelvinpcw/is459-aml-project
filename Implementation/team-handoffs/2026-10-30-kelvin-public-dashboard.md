# Task: public browser access to the completed AML dashboard

- **Owner:** Kelvinpcw with Codex
- **Branch / PR:** `agent/codex-public-dashboard`; [PR #20](https://github.com/Kelvinpcw/is459-aml-project/pull/20)
- **Updated at:** 2026-10-30 (+08:00)
- **Status:** IN_PROGRESS
- **Evidence kind:** current human authorisation, local configuration/checks, failed identity preflight

## Scope and coordination

The user reported a token interruption and explicitly requested making EC2 public. The completed ingestion, processing, publication and old-output cleanup remain preserved; there is no processing retry. PR #19 is merged and no open PRs were observed. This new scope permits a short public read-only visualization session using existing published results. The user subsequently raised the project planning ceiling to US$200 and explicitly requested leaving the dashboard running for manual shutdown, superseding the one-hour guard for this new public instance only. This grants dashboard hosting, not another processing run. Private cost/reserve assumptions are recorded.

The earlier instance's scheduled deadline is past. Initial verification was blocked by an expired project login. After member sign-in, the explicit profile/account/region were verified: the old instance and root disk are absent; its idle stack remains for scoped deletion. The normal AWS login flow is open for the operator; do not collect secrets in chat or fall back to default credentials. Verify account/region after refresh before any cloud mutation.

## Planned configuration and checks

- A separate temporary dashboard template derives from the reviewed private dashboard with the same read-only data permissions and immutable package. It creates no processing jobs, datasets or bucket.
- Only HTTP port 80 is public. Streamlit stays bound to localhost behind an official-repository nginx proxy with WebSocket support and request/connection limits. No SSH or direct Streamlit port is opened. Published synthetic results are public during this session; the source bucket, raw data, labels and AWS credentials remain private.
- The automatic shutdown is removed at the user's explicit request. OS-initiated shutdown stops the instance; root disk deletion on explicit termination, encryption, IMDSv2 and standard CPU credits remain. This is an HTTP/IP demo endpoint, not a new authenticated HTTPS hosting service.
- Two focused local public-access/isolation/termination checks pass. Cloud validation, instance-state inspection, deployment and actual public browser verification remain pending.

## AWS state and next safe step

No AWS mutation or processing occurred in this session so far. Identity preflight initially failed due to expired login, then passed after member refresh. After the operator signs in: verify project identity, inspect and clean the exact obsolete private dashboard stack/instance/disk, validate current publication and available budget reserve, then deploy one fresh temporary public dashboard if the old instance has ended. Never restart the pipeline or repeat S3/Catalog cleanup. Record private exact identities/deadline/evidence; publish the sanitised observed outcome and configure final scoped cleanup.

GitHub sync: branch pushed and draft PR #20 opened. Public access is not yet deployed. The old automatic-cleanup heartbeat was deleted to honour manual shutdown; no replacement shutdown schedule will be added.
