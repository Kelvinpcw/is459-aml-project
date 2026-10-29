# AWS sessions: coordinate, verify, hand over

GitHub carries a **sanitised activity summary** so teammates know what happened. Detailed AWS records, measurements/costs, raw logs/screenshots, credentials and the operator checkpoint remain private. Do not copy private run reports into a public PR. Use [CONTRIBUTING.md](../CONTRIBUTING.md) for the general code/task workflow.

## Before an AWS session

1. Read [STATUS.md](STATUS.md), [VERIFY_PROGRESS.md](VERIFY_PROGRESS.md), relevant [handoffs](team-handoffs/README.md) and open/draft PRs. Different components can have different owners and observation times.
2. Establish the current user's requested scope: identity/status check, viewing published data, processing, deployment, IAM change or cleanup. These are different authorisations. Confirm the relevant resource owner before touching shared resources; a PR is not a lock and silence is not consent.
3. For mutations or paid processing, publish a PLANNED handoff on your branch with a draft PR before acting. Explain the purpose, component/consumers, unique logical output ownership and approval boundary. Keep detailed cost/access/run reviews private. Make an IN_PROGRESS update when starting. Don't start if coordination/publication is unresolved.
4. Use the member's own approved login, explicit profile and project region; verify with `check_aws_profile.sh YOUR_PROJECT_PROFILE`. Never silently use `default` or grant yourself access. Logins/identity checks do not authorise jobs, data queries, deployment or spending.

A read-only task can group its observations in one end-of-session record; it doesn't need a commit for every API call. Do not reconstruct missing evidence through a paid rerun. Reuse completed immutable results.

## At the end — including failures and read-only sessions

Create/update a dated record from the [template](team-handoffs/_TEMPLATE.md). Share:

- owner, branch/PR, time, requested scope and affected component;
- source/version and outcome category, with local versus cloud evidence distinguished;
- what changed, failed or could not be verified; no fabricated success;
- whether compute was started/stopped, what cleanup was actually observed and what remains unknown;
- next safe step, responsible owner and blockers.

Keep the full observed resource/run/query identities, input/output namespaces, report hashes, result metrics, runtime, cost estimate/billing evidence and cleanup inventory in the private operator record. Public code/release identifiers and logical resource aliases can provide context without publishing that evidence. Don't retroactively publish another operator's private records. Ask the relevant owner privately when exact locators are required.

Update [STATUS.md](STATUS.md) if implementation/completion state changed. Review the exact public diff, stage explicit files, commit/push and open/update a PR (self-merge is allowed under the contribution workflow). Verify local, remote branch and PR heads agree; report commit/link/checks and remaining blockers. A local checkpoint or chat summary alone is not a shared handoff.

## Cost and cleanup

Budgets and earlier single-run approvals are scoped historical records, not authority for another agent. Agree current scope and remaining budget before paid work; estimates/timeouts are not billing caps. Don't add recurring schedules or leave idle paid compute.

Necessary authorised stop/cleanup takes precedence over Git troubleshooting. Verify terminal/deleted state directly as appropriate; a stop request or elapsed shutdown timer is not proof. Retain approved S3 results and avoid unrelated resources. See [TEARDOWN.md](TEARDOWN.md).

If GitHub publication is blocked, preserve the private/public-safe handoff locally, say **NOT SYNCED TO GITHUB** with the exact blocker, and don't start more paid work until coordination is restored. Do not force-push shared history or disclose private evidence to get around a publication failure.

These procedures are instructions, not automatic AWS monitoring, GitHub synchronisation, a deployment pipeline or a cloud-resource lock.
