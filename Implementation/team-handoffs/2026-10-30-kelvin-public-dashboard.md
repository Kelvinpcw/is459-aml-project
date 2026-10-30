# Task: public browser access to the completed AML dashboard

- **Owner:** Kelvinpcw with Codex
- **Branch / PR:** `agent/codex-public-dashboard`; [PR #20](https://github.com/Kelvinpcw/is459-aml-project/pull/20)
- **Updated at:** 2026-10-30 (+08:00)
- **Status:** BLOCKED — member sign-in required before planned deployment
- **Evidence kind:** current human authorisation, local configuration/checks, failed identity preflight

## Scope and coordination

The user reported a token interruption and explicitly requested making EC2 public. The completed ingestion, processing, publication and old-output cleanup remain preserved; there is no processing retry. PR #19 is merged and no open PRs were observed. This new scope permits a short public read-only visualization session using existing published results. The existing ceiling remains unchanged; private reserve estimates and a new bounded viewing window must be recorded before launch.

The earlier instance's scheduled deadline is past. Its current state and final old-stack cleanup could not be verified because the explicit project login/refresh token expired. The normal AWS login flow is open for the operator; do not collect secrets in chat or fall back to default credentials. Verify account/region after refresh before any cloud mutation.

## Planned configuration and checks

- A separate temporary dashboard template derives from the reviewed private dashboard with the same read-only data permissions and immutable package. It creates no processing jobs, datasets or bucket.
- Only HTTP port 80 is public. Streamlit stays bound to localhost behind an official-repository nginx proxy with WebSocket support and request/connection limits. No SSH or direct Streamlit port is opened. Published synthetic results are public during this session; the source bucket, raw data, labels and AWS credentials remain private.
- The one-hour terminate guard, encrypted root disk with deletion on termination, IMDSv2 and standard CPU credits remain. This is an HTTP/IP demo endpoint, not a new authenticated HTTPS hosting service.
- Two focused local public-access/isolation/termination checks pass. Cloud validation, instance-state inspection, deployment and actual public browser verification remain pending.

## AWS state and next safe step

No AWS mutation or processing occurred in this session so far. Identity preflight failed due to expired login. After the operator signs in: verify project identity, inspect and clean the exact obsolete private dashboard stack/instance/disk, validate current publication and available budget reserve, then deploy one fresh temporary public dashboard if the old instance has ended. Never restart the pipeline or repeat S3/Catalog cleanup. Record private exact identities/deadline/evidence; publish the sanitised observed outcome and configure final scoped cleanup.

GitHub sync: branch pushed and draft PR #20 opened. Public access is not yet deployed.
