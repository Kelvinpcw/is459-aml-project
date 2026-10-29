# Verify what is done before continuing

For an explanation of how the system works, use the [walkthrough](../PIPELINE_WALKTHROUGH.md) and [Q&A](../Q_AND_A.md) first. You do not need an assigned task to learn or inspect the source.

Use this to answer “What is implemented?”, “What ran?” and “What can I safely pick up?”. Checking status is separate from rerunning processing. Reading an old approval is not fresh authority for AWS work.

## 1. Read shared evidence first — no AWS needed

From the repository root, inspect your branch and fetch GitHub. Preserve uncommitted work.

```bash
git status --short --branch
git fetch origin
git log -5 --oneline origin/main
gh pr list --state open
gh pr view PR_NUMBER --comments
```

Read [STATUS.md](STATUS.md), relevant [team handoffs](team-handoffs/README.md), PR files/tests and [the requirements](../Proposal/Project_Proposal.md). For an unmerged PR, inspect its branch/files on GitHub; don't merge someone else's work merely to read it. An example relevant record at this guide's preparation is [pipeline-verification PR #11](https://github.com/Kelvinpcw/is459-aml-project/pull/11); read its current state rather than assuming it is merged or a live inventory.

Use the latest **relevant scoped** evidence, not simply the newest file in the repository. A dashboard styling update does not supersede a processing handoff. If evidence is private/unavailable, say so and ask its operator for a public-safe summary; continue independent local work.

## 2. Keep these states distinct

| Evidence | What you may conclude | What it does not establish |
| --- | --- | --- |
| Source/config exists | Implementation is present at that commit | It was deployed or completed in AWS |
| Synthetic local tests passed | The tested scenarios passed locally | Real-data success or detector effectiveness |
| Merged PR | Shared source/context is on `main` | A teammate pulled it or a cloud service changed |
| Dated operator cloud observation | The stated scope/status was observed then | It is still current or another run is approved |
| Published manifest + matching quality/evidence | One coherent release can be consumed | All account resources are stopped or billing is final |

Identify the component, source commit, input/run/snapshot identity, checked scope/time and evidence owner. Never combine unrelated pilot/full-data attempts into a success claim. The software includes the full batch path; scheduled/incremental daily ingestion and formal user-acceptance measurements remain separate work.

## 3. If fresh AWS verification is explicitly requested

1. Agree the read-only scope and relevant resource owner. Read [AWS_HANDOFF.md](AWS_HANDOFF.md), recent handoffs and open PRs. Use the member's own approved login; [onboarding](../TEAM_START_HERE.md#4-aws-login--only-for-an-approved-activity) covers sign-in. Missing permissions are a blocker, not a reason to create grants.
2. Verify the actual profile's account and region with `bash Implementation/scripts/check_aws_profile.sh YOUR_PROJECT_PROFILE`. Use explicit profile/region on all subsequent commands. This guide's preparation made no AWS calls.
3. Inspect existing state only. With the owner's appropriate access, read the existing publication pointer, verify its manifest hash and identity using the logic in [release.py](pipeline/release.py), inspect referenced quality reports and relevant terminal job/workflow metadata. Use observed resource locators from the operator; don't guess job names from old draft files. Do not read Q2-prohibited inputs through its role.
4. Verify only the requested scope: required stage reports, consistent dataset/run/analysis/window identities, immutable output locations and retained stage-success evidence. For cleanup, inspect the owned jobs/queries/temporary dashboard resources directly. Definitions and S3 objects can remain while compute is stopped; a stopped EC2 instance can still leave billable storage/IPs.
5. Summarise the result in chat and keep a private supporting note if useful. State unknowns, unavailable access, failed checks and next owner. Distinguish “no active resources in this inspected scope” from an account-wide claim. **A purely read-only check needs no handoff or PR** unless the user asks for a shared record.

**Do not** start Athena queries, Glue jobs, crawlers, interactive sessions or Step Functions just to prove existing work. Don't recreate roles, deploy a dashboard, overwrite outputs or delete resources. A read-only status request does not authorise those actions. The connected dashboard's data queries need their own agreed viewing scope; they are not an offline check.

Do not fabricate missing private evidence or ask another agent's old chat to act as fresh approval. A failed/missing publication means investigate the existing failure first; it is not an automatic processing retry.

## 4. Report a useful handoff

Give the teammate:

- what is implemented and where, with the commit/PR;
- what was checked, when and in which scope, with local versus cloud evidence labelled;
- which checks could not be performed and why;
- whether any compute was started/stopped, what cleanup was actually observed and what remains unverified;
- the next suggested step and who to contact if known, without inventing assignments.

Keep detailed AWS records, raw results, measurements/costs and credentials private. Push a [sanitised handoff](team-handoffs/README.md) so the next agent can find it. If GitHub sync fails, explicitly report **NOT SYNCED TO GITHUB**.
