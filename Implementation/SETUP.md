# Team setup

New to the project? Start with [TEAM_START_HERE.md](../TEAM_START_HERE.md) for clone/open-folder steps and an AI onboarding prompt. The sections below are task-specific technical references, not a requirement to install everything or access AWS.

Updated 29 October 2026. Read [STATUS.md](STATUS.md), [AWS_HANDOFF.md](AWS_HANDOFF.md), the newest relevant [shared handoffs](team-handoffs/) and [../AGENTS.md](../AGENTS.md) before using an AI assistant. Historical deployment steps remain in [../PROJECT_CHECKPOINT.md](../PROJECT_CHECKPOINT.md) and `aws/reviews/`; do not repeat them as fresh setup.

## 1. Clone and create a feature branch

```bash
git clone https://github.com/Kelvinpcw/is459-aml-project.git
cd is459-aml-project
git switch -c feature/your-task
```

If you already have the repository, use that copy; do not run `git init` again. Only invited collaborators can push even though the repository is public. Prefer pull requests reviewed by a teammate.

## 2. Local Python/Spark environment

The recorded local test environment is Python 3.11, PySpark 3.5.6 and Java 21. Install Python/Java first and ensure `java -version` resolves to the intended JDK (`JAVA_HOME` may need setting). Python packages alone do not install Java.

Run from the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r Implementation/requirements.txt
python -m pytest Implementation/tests -q
```

These tests use local fixtures and local Spark, not paid AWS jobs. A fresh clone does not require the 3 GB original dataset for the regression suite. Do not claim a test passed until you run it; report missing Python/Java/dependencies as setup blockers. This documentation update did not rerun the suite.

## Visualization without restarting cloud compute

If the pipeline already has a published release, run only the dashboard on your laptop. No Spark, raw dataset, EC2 instance or new processing run is needed. This still makes bounded Athena queries and S3 reads, which can incur small query/request charges.

```bash
python3.11 -m venv .venv-dashboard
.venv-dashboard/bin/python -m pip install -r Implementation/dashboard/requirements.txt 'botocore[crt]==1.43.119'
bash Implementation/scripts/start_local_dashboard.sh YOUR_PROJECT_PROFILE
```

Use your actual authorized project profile. Open `http://127.0.0.1:8501/` after startup. The launcher verifies the account/region, selects the dashboard workgroup (512 MB per query instead of the smaller development limit), and binds only to localhost. Application queries have a 30-second cancellation limit. All reads remain pinned to the published release; the launcher does not upload, deploy, change IAM, or start Glue/Step Functions. Stop the local server with Ctrl+C. If you intentionally use another environment, set `AML_DASHBOARD_PYTHON` to its Python executable.

## 3. Original data and generated artifacts

The following are deliberately ignored and absent from a fresh clone:

- `Ibm_dataset_medium/`: original `HI-Medium_Trans.csv`, `HI-Medium_accounts.csv`, `HI-Medium_Patterns.txt`.
- `Implementation/data/`: generated date slices, source manifests, local replays and downloaded cloud bundles.

Get originals from the [IBM dataset on Kaggle](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml), following its access/licence terms; provenance/licence notes are in [IBM/AML-Data](https://github.com/IBM/AML-Data). Do not put the dataset into Git. Existing cloud objects/manifests are recorded in `aws/reviews/` and the checkpoint; ask the relevant owner for the exact required subset rather than uploading another copy.

`scripts/build_development_input.py` creates stable-ID, date-selected copies without changing originals. Its defaults select **only 1 September 2022** (`--start 2022-09-01`, exclusive `--end 2022-09-02`). It scans the unsorted full source locally. Review the intended date scope and use a fresh output directory when building another slice; do not run a full replay automatically as part of onboarding.

## 4. AWS identity — verify before cloud work

Shared project account: **`160885259244`**. Project Region: **`us-east-1`**.

Each member must configure their own authorised console login or CLI profile; cloning does not create AWS access. Profile names are local conveniences, not shared cloud resources. You do not need to use the same profile name as another teammate. Never share keys through GitHub or assume your default account is correct.

For CLI work, replace `YOUR_PROJECT_PROFILE` below with your actual local profile name. These checks are read-only:

```bash
aws sts get-caller-identity --profile YOUR_PROJECT_PROFILE --region us-east-1
bash Implementation/scripts/check_aws_profile.sh YOUR_PROJECT_PROFILE
```

The guard checks both account and configured region. It aborts if either differs/missing; investigate rather than falling back to `default`. Its legacy default profile is `is459`, so always pass your chosen profile explicitly. Re-check identity at the time of any authorised cloud action. Explicitly pass `--profile`/`--region` on subsequent CLI commands and choose a verified profile/session for local SDK calls; do not assume a prior STS command changes the default account.

**No AWS deployment/run is required to start local development.** Project bucket/configuration is described in `aws/environment.json`, but its legacy status field is not an up-to-date deployment summary. Use `STATUS.md` and the newest scoped run/review evidence instead.

## 5. Shared AWS resources are not branch-isolated

- Coordinate with the component owner before editing shared Glue jobs, IAM, Catalog tables or Step Functions.
- For an authorised experiment, use distinct script paths, jobs where necessary, and fresh dataset/run/analysis output namespaces. Do not overwrite validated results or frozen releases.
- Do not reuse Q1's label-reading role for Q2. Keep references/evaluation inaccessible to detection.
- Paid runs, permissions and deletions must stay within the current user's explicit scope. The checkpoint's paused evaluator is not resumed by cloning or reading documentation. Existing exact attempt approval is historical and not blanket permission for new attempts.
- Record actual cloud actions, parameters, evidence and estimated costs in the ledger/checkpoint. Stop authorised compute after use; retain approved S3 artifacts. See [TEARDOWN.md](TEARDOWN.md).
- Publish a sanitised shared handoff for every AWS session, even read-only checks or failures. Before mutations/paid work, publish the plan on a draft PR and confirm shared-resource ownership. Keep detailed evidence/ledger/checkpoint local; see [AWS_HANDOFF.md](AWS_HANDOFF.md).

## 6. Handoff and pull request

Before asking another person or AI to continue, record your task/branch, changed files/contracts, commands/tests actually run, public-safe run/output identities, observed AWS outcome/cost/cleanup and remaining blockers/next owner. Follow [AWS_HANDOFF.md](AWS_HANDOFF.md) and its template. Never paste credentials, signed URLs, raw logs/data or unreviewed private output paths into Git. Keep exact sensitive locators in the private operator record. Update `STATUS.md` when completion state changes.

Commit/push explicit task files and open/update a PR; verify the remote commit matches your local head. Include the commit and PR URL in your final report. A local-only note is not shared context. If blocked, say **NOT SYNCED TO GITHUB** and why. Read relevant open PRs before work, since pushed handoffs may await review. Do not merge your own PR.
