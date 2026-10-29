# New teammate? Start here

You do **not** need to understand AWS, Spark or this codebase before opening the project with an AI coding assistant. Start locally. Your assistant should explain the project and help with only your assigned task, not deploy the whole architecture.

**GitHub access and AWS access are separate.** Cloning this public repository gives you code, not permission to push changes or access the team's AWS account.

## 1. Get the code and open the folder

1. Install [Git](https://git-scm.com/downloads) and your preferred AI coding editor/application.
2. Ask Kelvin to invite your own GitHub account as a repository collaborator; accept the invitation. You can clone before this, but pushing requires access.
3. Open a terminal and run:

   ```bash
   git clone https://github.com/Kelvinpcw/is459-aml-project.git
   cd is459-aml-project
   ```

4. In your AI editor, use **Open Folder** and select the entire `is459-aml-project` folder. Open the assistant/chat there. Do not open just one Python file or use a chat that cannot read the project folder.

Already have a clone? Open that copy instead. Ask the agent to inspect your branch and uncommitted work before updating it. Do not overwrite work, clone inside the repository, run `git init` again, or force-pull/reset to fix an error.

If Git is not installed, use its official installer first or ask your assistant for OS-specific help. Do not paste credentials or tokens into the AI chat.

## 2. Paste this into your AI assistant

You can use this prompt unchanged. If you have an assigned task, add it below the prompt.

```text
I am new to this shared team project. Help me onboard step by step.

Read TEAM_START_HERE.md, AGENTS.md, README.md,
Implementation/STATUS.md and Implementation/AWS_HANDOFF.md,
then the newest relevant shared handoffs. Check open GitHub PRs
for newer/unmerged work. If you cannot access something, say so.

First explain, in plain language:
- what this project does;
- what software exists versus what was actually cloud-validated;
- what is happening in relevant open PRs;
- what I need on my laptop for my assigned task.

Ask for my assigned task if I have not provided one, and ask which
operating system I use if you cannot determine it. Do not choose
unassigned backlog work or implement the entire project.

Inspect existing tools before installing anything. Ask before
installing software or changing my machine's configuration.
Guide me through interactive logins in my own terminal/browser;
never ask me to paste keys, tokens or passwords into chat or Git.

Start with local setup only. Do not access AWS, launch the connected
dashboard, run paid queries, deploy, change IAM, overwrite outputs,
delete resources or resume old jobs without my explicit approval
for that specific scope/cost. If my task needs AWS, first establish
my own approved login method, coordinate resource ownership, then
verify the explicit profile's project account and region.

Use a separate task branch based on current origin/main. Preserve
others' edits. Run relevant local checks, update shared context,
commit/push only explicit task files and open/update a PR for a
teammate's review. Never push directly to main or merge your own PR.

For any authorised AWS session, follow Implementation/AWS_HANDOFF.md:
publish a sanitised handoff with observations, cost basis, compute/
cleanup state, blockers and next steps, even if the session was
read-only or failed. Keep raw evidence and credentials private.

Finish with the verified pushed commit, PR URL, checks actually run,
AWS effects/costs and blockers. If you cannot publish, clearly say
NOT SYNCED TO GITHUB and explain why. Do not invent test/cloud results.
```

The assistant can read files and prepare work, but it cannot grant you GitHub/AWS access, supply missing private evidence, accept interactive logins for you, or decide the team's task ownership. Ask the relevant teammate when those are missing.

## 3. Install only what your task needs

| Your task | Start with | AWS needed? |
| --- | --- | --- |
| Read requirements, edit docs, review code | Git and your editor | No |
| View the offline TRACE design | Open [`Visulization/index.html`](Visulization/index.html) locally in a browser | No; invented fixtures only |
| Test/change that offline design | Follow its [README](Visulization/README.md); Node.js 20+ for model tests | No |
| Work on Python/Spark jobs and tests | Follow [local setup](Implementation/SETUP.md#2-local-pythonspark-environment): Python 3.11, Java 21 and project dependencies | Not for synthetic local tests |
| View an existing real published release | [Connected dashboard setup](Implementation/SETUP.md#visualization-without-restarting-cloud-compute), approved AWS access and a published release | Yes; bounded Athena/S3 reads can cost money |
| Deploy/process/change AWS resources | Explicit task approval, ownership coordination, current state and budget; then the [runbook](Implementation/RUNBOOK.md) | Yes; **not part of onboarding** |

Do not install the entire stack for a documentation task. Original datasets, generated data, credentials and detailed operational checkpoints are deliberately absent from a fresh clone. Missing private inputs are a handoff request, not a reason to invent results or rerun completed processing.

## 4. GitHub login for pushing

Your editor may already provide GitHub authentication. Otherwise the assistant can help you install the [GitHub CLI](https://cli.github.com/) and run:

```bash
gh auth login
gh auth status
```

Complete the interactive login yourself. Never publish a token or run a token-display command for the agent. Git commit name/email may also need local configuration; choose your own identity (a GitHub no-reply email is an option), not Kelvin's.

If pushing returns a permission error, check that you accepted the collaborator invitation and authenticated as the invited user. Do not share another person's token, change repository visibility or bypass permissions. After a teammate merges your PR, other people can get it from `main`; until then it is on your PR branch. Agents must check both.

## 5. AWS login — only when your assigned task needs it

**Stop here unless AWS access is needed and approved.** Installing AWS CLI is not logging in, and logging in is not approval to spend or deploy. Console access also does not automatically configure CLI credentials.

### Get your own approved access

Ask the team's AWS account administrator which login method to use, and obtain your own access to project account **`160885259244`**, project region **`us-east-1`**. Do not create a new AWS account, use a root login, copy another member's credentials, create IAM users/roles or widen permissions to make setup work.

### Install AWS CLI v2

Use the [official installation instructions](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) for your OS. On macOS, **if Homebrew is already installed**:

```bash
brew install awscli
aws --version
```

The version should be AWS CLI **2.x**. Windows users should let the assistant adapt commands/paths and the Bash profile check to an approved Bash environment; do not blindly paste macOS commands into PowerShell.

### If the administrator provides IAM Identity Center / SSO

This repository does **not** establish that SSO is configured. Use these commands only if the administrator supplies an SSO start/issuer URL, SSO region and assigned account/role:

```bash
aws configure sso --profile is459-project
aws configure set region us-east-1 --profile is459-project
aws sso login --profile is459-project
```

`is459-project` is an example local profile name, not a resource to create in AWS. Select the assigned project account/role. The **SSO directory's region may differ** from the project workload region. Complete browser login yourself. When the session expires, repeat `aws sso login` for the same profile.

If the administrator uses a different method, ask for its approved CLI setup instead. Do not assume `aws configure` creates access or put credentials into project files, command arguments, GitHub issues or AI chat.

### Verify the account/region before other AWS work

From the repository root, with your actual profile name:

```bash
aws sts get-caller-identity --profile is459-project --region us-east-1
bash Implementation/scripts/check_aws_profile.sh is459-project
```

These are read-only AWS checks. Expected account: **`160885259244`**; configured project region: **`us-east-1`**. A successful check proves identity/region, not permission for every service or a new spending approval. If checks fail, stop and ask; never fall back to `default` or change grants yourself.

Follow the [AWS handoff procedure](Implementation/AWS_HANDOFF.md) even for this read-only session. Use an explicit profile/region on later CLI calls and the verified session for SDK calls. Starting the connected dashboard may issue chargeable queries; don't treat it as an offline preview.

## 6. Before ending your task

Ask the agent: **“Did you push the handoff and task changes? Show me the commit and PR link.”**

- Update the relevant docs/status and record any authorised AWS session with outcome, costs, cleanup, blockers and next owner.
- Check the exact diff for private information; stage only the task's explicit files. Never `git add .`, force-push or commit credentials/data/raw AWS evidence.
- Push the task branch and open/update a PR. A teammate reviews and merges it; the agent does not merge its own work.
- If publication is blocked, the agent must report **NOT SYNCED TO GITHUB**. Make authorised compute safe first; do not leave it running while troubleshooting Git.

**For Kelvin/team coordinators:** invite collaborators, assign distinct tasks, provide each member's approved AWS access only when needed, and arrange PR review. AI instructions help collaboration, but are not automatic AWS monitoring or a cloud lock.
