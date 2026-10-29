# Start here — teammates and AI agents

Use this order: **get the code → understand the pipeline → explore results or make a change → check, push and merge → leave an update**. GitHub access and AWS access are separate; cloning gives you source, not either account's permissions.

## 1. Get the project

Ask the repository owner to invite your own GitHub account as a collaborator and accept the invitation. Install [Git](https://git-scm.com/downloads) and your preferred AI editor if needed, then:

```bash
git clone https://github.com/Kelvinpcw/is459-aml-project.git
cd is459-aml-project
```

Open the **whole folder** in the AI editor. If you already have a clone, use it; let the agent inspect uncommitted work before updating. Do not force-reset it, clone inside it, or initialise another Git repository.

Your editor may already handle GitHub login. Otherwise install the [GitHub CLI](https://cli.github.com/) and use its [interactive login](https://cli.github.com/manual/gh_auth_login):

```bash
gh auth login
gh auth status
```

Complete the login yourself in your browser/terminal. Give the agent no passwords, keys, authentication codes or tokens. Use your own Git name/email, not another teammate's identity.

## 2. Ask your AI agent to explain the project first

```text
Help me understand this IS459 project and prepare to answer presentation Q&A.

Read TEAM_START_HERE.md, AGENTS.md, README.md, PIPELINE_WALKTHROUGH.md,
Q_AND_A.md, Implementation/STATUS.md and the relevant team handoffs.
Fetch current origin/main and check open/draft PRs for newer work;
preserve other people's local edits and in-progress changes.

The batch software path is already implemented. Explain it step by step:
inputs → preparation → Q1/Q2 → evaluation → publication → dashboard.
For each stage explain its purpose, inputs/outputs, code location, AWS
service and limitations. Distinguish code/local tests from actual dated
cloud observations. Explain the two business questions and quiz me.
No assigned task or formal team role is needed just to learn/explore.
Don't turn old plans into an instruction to rebuild the pipeline.

If I request a change, inspect the relevant source and overlapping PRs,
make a focused change on a branch, run relevant checks and explain it.
Update docs/status when needed, add a short handoff, stage explicit
paths, commit, push and open/update a PR. Verify its remote head.
Contributors may merge their own PR after checks and an overlap check;
no separate reviewer is required. Merge for me when I ask you to.

Detect my OS/tools and set up only what I need. Ask before installations
or machine configuration changes. Guide login in my own terminal/browser;
never collect credentials in chat. Start locally. AWS login, bounded
viewing/status checks and processing/deployment are separate scopes.
Don't start jobs, deploy, alter IAM, overwrite/delete outputs or add
schedules without the current explicit approval. Use my own verified
profile; keep detailed AWS records/measurements/costs private.

Finish with what changed, checks actually run, pushed commit/PR/merge
state, AWS scope/cleanup and next step. If publishing fails, say
NOT SYNCED TO GITHUB and why. A local AI chat is not the team record.
```

Start with the [pipeline walkthrough](PIPELINE_WALKTHROUGH.md), then use the [Q&A guide](Q_AND_A.md) to rehearse. The agent can prepare commands and help you verify results. You complete interactive authentication and confirm task ownership/access with the relevant teammate. An agent cannot grant itself repository or AWS permissions.

## 3. Explore or run only what you need

| Task | Tools / instructions | AWS? |
| --- | --- | --- |
| Docs, design review, code review | Git + editor; [contribution workflow](CONTRIBUTING.md) | No |
| View the offline TRACE concept | Open [Visulization/index.html](Visulization/index.html) in a browser | No; invented fixtures |
| Test/change that concept | Node.js 20+; [prototype README](Visulization/README.md) | No |
| View/change the connected dashboard | Python 3.11 + dashboard dependencies; [setup](Implementation/SETUP.md#visualization-without-restarting-cloud-compute) | Existing published-result reads only, when approved |
| Work on processing jobs | Python 3.11, Java 21 and project dependencies; [local tests](Implementation/SETUP.md#2-local-pythonspark-environment) | No for synthetic local tests |
| Deploy/process/clean up cloud resources | Current scope, owner, budget and explicit approval; [AWS handoff](Implementation/AWS_HANDOFF.md) | Yes; separate from onboarding |

With Python 3 available, run the local tool check from the root; replace `docs` with `prototype`, `dashboard` or `pipeline`:

```bash
python3 Implementation/scripts/project_doctor.py --task docs
```

On Windows use `py -3` if `python3` is unavailable. This helper only checks local tool versions. It installs nothing, signs into nothing, reads no AWS profiles and makes no cloud/GitHub API calls. A passing check does not establish credentials, Python package readiness or pipeline completion.

## 4. AWS login — only for an approved activity

Ask the AWS administrator for **your own approved identity** in account **`160885259244`**, workload region **`us-east-1`**, and which login method applies. Console access does not automatically configure the CLI. Use [AWS CLI v2's official installer](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), then check `aws --version`.

Choose **one** administrator-approved route:

| Your access method | Commands / reference |
| --- | --- |
| Existing console identity, permitted for local development | `aws login --profile is459-project --region us-east-1` ([AWS instructions](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html)); requires CLI 2.32.0+ and the necessary existing sign-in permission |
| IAM Identity Center / SSO | Configure once with `aws configure sso --profile is459-project`; refresh with `aws sso login --profile is459-project` ([AWS instructions](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)) |
| Another approved setup | Ask the administrator for that method; do not improvise credentials or access grants |

`is459-project` is an example local profile name. Use your actual profile, which may differ from a teammate's. For SSO, use the supplied directory region/start URL and assigned role; the directory region can differ from the workload region. Complete browser/MFA steps yourself. On expiration, repeat the same method/profile. If sign-in permissions are missing, ask the administrator; do not create IAM roles/users or attach policies yourself.

Set the profile's workload region once if needed, then verify it before other AWS work:

```bash
aws configure set region us-east-1 --profile is459-project
aws sts get-caller-identity --profile is459-project --region us-east-1
bash Implementation/scripts/check_aws_profile.sh is459-project
```

The guard requires an explicit profile and checks its configured region/account. Never silently fall back to `default`. These are identity checks, not permission to run jobs or a cost cap. Windows users need an approved Bash environment for repository `.sh` helpers; ask the agent to adapt local paths instead of pasting Unix commands into PowerShell unchanged.

To ask an agent for a scoped status check after login:

```text
I have completed my own login. My local profile is [profile].
Verify its project account/region, then follow Implementation/VERIFY_PROGRESS.md to
inspect the existing publication and relevant job/resource metadata
read-only. Do not start jobs/queries, deploy, change IAM, overwrite or
delete anything. Record the timestamp, scope, unknowns and next step.
Keep detailed observations private and push a sanitised team handoff.
```

Read [VERIFY_PROGRESS.md](Implementation/VERIFY_PROGRESS.md) for what that check can establish. A purely read-only status check needs no handoff; follow the [AWS handoff](Implementation/AWS_HANDOFF.md) for any change, paid run, deployment or cleanup. The connected dashboard can make chargeable Athena/S3 reads; a new processing run needs separate approval.

## 5. Make your work visible

Follow [CONTRIBUTING.md](CONTRIBUTING.md): branch → change/check → handoff → explicit commit/push → PR → merge. Ask your agent: **“Show me the pushed commit and PR link.”** You can merge your own PR after checks and checking for overlapping work; a separate teammate review is optional. Teammates read open PRs for work in progress, then update their clone after merge. AWS console changes and local AI chats require an explicit written handoff; GitHub does not discover them automatically.
