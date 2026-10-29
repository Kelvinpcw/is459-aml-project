# Historical Glue ↔ GitHub connection reference

Observed 27 October 2026, Singapore; not freshly verified. Read [progress verification](../VERIFY_PROGRESS.md) before touching the shared job. Setup is paused at the user's request after successful Q1 push and pull. No processing job was run.

| Setting | Value |
| --- | --- |
| AWS account / Region | `160885259244` / `us-east-1` |
| Connected job | `is459-aml-q1-dev` |
| Repository | `Kelvinpcw/is459-aml-project` |
| Branch observed then | `codex/glue-github-connection` |
| Sync folder | `Implementation/glue/is459-aml-q1-dev` |
| Verified sync commit | `24ec9b68e380910843932472113a93aebe6d3091` |

Only Q1 is connected. At the connection checkpoint, preparation/Q2 were unchanged and the evaluator was unsaved. Its later cloud completion is recorded in [current status](../STATUS.md); it has no GitHub connection. No automatic deployment, execution or schedule is configured. The historical source integration was merged via [PR #3](https://github.com/Kelvinpcw/is459-aml-project/pull/3); that does not switch or verify the live Glue job branch.

## What the buttons do

In Glue Studio open the Q1 job, then Version Control. Verify the account, Region, repository, branch and folder before acting. Glue requires GitHub connection information again for a new console login; each person uses their own authorised access. Never share a token in Git, chat or a screenshot. The current user's fine-grained token has project-repository Contents read/write and Metadata read, with no account permissions; its observed expiry is 26 November 2026.

- **Actions → Push to repository** exports the saved job definition and script to the selected branch. It can overwrite those files on that branch. Use a task branch and review the resulting pull request.
- **Actions → Pull from repository** updates the shared Glue job from the selected branch. It can overwrite unsaved console work. Coordinate with the job owner and inspect both the script and job settings first.
- **Run** is separate and starts paid processing. This setup did not authorise a new run or resume the paused evaluator.

The initial export was pulled back unchanged. Full editor copies before and after exactly matched `../releases/q1-v1/q1_risk-v1.py`. The export contains no detected token patterns or credential fields. Retain the JSON and script together: Glue expects the JSON filename to match the job name, and the Python filename to match `command.scriptLocation`.

## Where future changes belong

Editable source remains `../jobs/q1_risk.py`. The Q1 subfolder here is the console's deployment snapshot; editing the source file alone does not update that snapshot or AWS. A component owner must prepare the reviewed script and matching JSON together for an authorised deployment. Preserve frozen releases and the historical `q1_risk-v1.py` S3 object; a future code change needs a new versioned script location and fresh analysis/output identity before pulling or running. Do not overwrite validated pilot outputs.

After team review/merge, deliberately choose the agreed branch in Glue and save it; merging this PR does not switch the job from its current integration branch automatically. Do not delete a branch while a job still depends on it.

If repository discovery says “Unable to load repositories” after entering a token, switching to Script and back to Version Control resolved the observed setup failure. This is a recorded workaround, not a diagnosis of every possible token failure.

Evidence: [connection record](../aws/reviews/github-glue-q1-connection-20261027.json). Official reference: [AWS Glue Git integration](https://docs.aws.amazon.com/glue/latest/dg/edit-job-add-source-control-integration.html).
