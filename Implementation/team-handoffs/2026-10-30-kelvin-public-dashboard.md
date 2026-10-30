# Task: public browser access to the completed AML dashboard

- **Owner:** Kelvinpcw with Codex
- **Branch / PR:** `agent/codex-public-dashboard`; [PR #20](https://github.com/Kelvinpcw/is459-aml-project/pull/20)
- **Updated at:** 2026-10-30 (+08:00)
- **Status:** COMPLETED — public instance intentionally left running for manual shutdown
- **Evidence kind:** current human authorisation, local configuration/checks, failed identity preflight

## Scope and coordination

The user reported a token interruption and explicitly requested making EC2 public. The completed ingestion, processing, publication and old-output cleanup remain preserved; there is no processing retry. PR #19 is merged and no open PRs were observed. This new scope permits a short public read-only visualization session using existing published results. The user subsequently raised the project planning ceiling to US$200 and explicitly requested leaving the dashboard running for manual shutdown, superseding the one-hour guard for this new public instance only. This grants dashboard hosting, not another processing run. Private cost/reserve assumptions are recorded.

The earlier instance's scheduled deadline is past. Initial verification was blocked by an expired project login. After member sign-in, the explicit profile/account/region were verified: the old instance and root disk are absent; its idle stack has subsequently been deleted and verified absent. The operator completed the normal AWS login flow and the explicit project account/region passed verification. No credentials were collected in chat and no default-profile fallback was used.

## Planned configuration and checks

- A separate temporary dashboard template derives from the reviewed private dashboard with the same read-only data permissions and immutable package. It creates no processing jobs, datasets or bucket.
- Only HTTP port 80 is public. Streamlit stays bound to localhost behind an official-repository nginx proxy with WebSocket support and request/connection limits. No SSH or direct Streamlit port is opened. Published synthetic results are public during this session; the source bucket, raw data, labels and AWS credentials remain private.
- The automatic shutdown is removed at the user's explicit request. OS-initiated shutdown stops the instance; root disk deletion on explicit termination, encryption, IMDSv2 and standard CPU credits remain. This is an HTTP/IP demo endpoint, not a new authenticated HTTPS hosting service.
- Two focused local public-access/isolation/termination checks pass. Cloud validation, deployment, instance-state inspection and actual public browser verification subsequently passed.

## Initial preflight and deployment plan (historical)

At initial preflight no AWS mutation or processing had occurred. Identity preflight initially failed due to expired login, then passed after member refresh. After the operator signs in: verify project identity, inspect and clean the exact obsolete private dashboard stack/instance/disk, validate current publication and available budget reserve, then deploy one fresh temporary public dashboard if the old instance has ended. Never restart the pipeline or repeat S3/Catalog cleanup. Record private exact identities/deadline/evidence; publish the sanitised observed outcome and configure final scoped cleanup.

GitHub sync: branch pushed and draft PR #20 opened. Public access is now verified and intentionally left running. The old automatic-cleanup heartbeat was deleted to honour manual shutdown; no replacement shutdown schedule will be added.

## Deployment observations

The public stack reached CREATE_COMPLETE. Actual instance attributes confirm manual
OS shutdown stops the instance and actual ingress is HTTP80 only. No automatic
cleanup heartbeat remains. Service/proxy/no-timer health and public browser data
verification are underway; no public UI success is claimed yet. The old private
instance and root disk are absent, and its obsolete stack is verified absent.
No processing, data publication, S3 deletion or Catalog mutation was performed.

## Verified outcome

The public stack is CREATE_COMPLETE and its EC2 instance is running. Actual HTTP-only
ingress, manual-stop instance behaviour and absence of a scheduled shutdown were
verified. nginx and Streamlit are active, proxy configuration passes nginx syntax
validation, and the public health endpoint passes. Browser testing over the public
endpoint loaded the current release's Monitoring charts/counts, connected case
queue/graph/evidence section, and Evaluation metrics/baselines.

An idle WebSocket closure was diagnosed from existing service/browser logs. The
nginx read/send timeouts were extended to a day and gracefully reloaded, then
navigation was verified again. The tracked bootstrap includes the corrected
settings for future deployments; the already-launched bootstrap remains the initial
version and the exact runtime override is recorded privately. No instance stop/start
or CloudFormation UserData update was used for this fix.

All sixteen focused public/private deployment, approval/isolation and cleanup checks
pass, alongside documentation links/diff checks. No processing source, detector
settings or immutable release changed. No new Glue run, S3 output deletion,
Catalog change or publication change occurred. The project bucket's public-access
block remains fully enabled; only the synthetic published web interface is public.

The old private instance/root disk are absent and its leftover stack is verified
absent. The new public instance is intentionally left RUNNING at the user's explicit
request, under the updated US$200 planning ceiling. There is no shutdown timer or
automatic cleanup heartbeat. The user owns manual stopping/termination; root-disk
storage survives Stop and is deleted on Terminate. Normal hosting, IPv4, disk,
Athena/S3/request/transfer charges continue as applicable; estimates are not billing
caps and this is not an account-wide cost audit. Detailed resource identities,
measurements, exact price calculations and raw evidence remain private.

Next safe step: use the public dashboard and manually stop the exact instance when
finished, following END_TO_END_GUIDE.md. Do not reinstall a timer, redeploy the
instance, rerun processing or merge PRs automatically. Source and this outcome are
pushed in PR #20; public hosting remains active by design.
