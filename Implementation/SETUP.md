# Team setup

Updated 27 October 2026. Read [STATUS.md](STATUS.md) for implementation state and [../AGENTS.md](../AGENTS.md) before using an AI assistant. Historical deployment steps remain in [../PROJECT_CHECKPOINT.md](../PROJECT_CHECKPOINT.md) and `aws/reviews/`; do not repeat them as fresh setup.

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

## 3. Original data and generated artifacts

The following are deliberately ignored and absent from a fresh clone:

- `Ibm_dataset_medium/`: original `HI-Medium_Trans.csv`, `HI-Medium_accounts.csv`, `HI-Medium_Patterns.txt`.
- `Implementation/data/`: generated date slices, source manifests, local replays and downloaded cloud bundles.

Get originals from the [IBM dataset on Kaggle](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml), following its access/licence terms; provenance/licence notes are in [IBM/AML-Data](https://github.com/IBM/AML-Data). Do not put the dataset into Git. Existing cloud objects/manifests are recorded in `aws/reviews/` and the checkpoint; ask the relevant owner for the exact required subset rather than uploading another copy.

`scripts/build_development_input.py` creates stable-ID, date-selected copies without changing originals. Its defaults select **only 1 September 2022** (`--start 2022-09-01`, exclusive `--end 2022-09-02`). It scans the unsorted full source locally. Review the intended date scope and use a fresh output directory when building another slice; do not run a full replay automatically as part of onboarding.

## 4. AWS identity — verify before cloud work

Kelvin supplied the following verified account identities on 27 October 2026:

| Local profile | Account | Use |
| --- | --- | --- |
| `IS-459-BDA` | `160885259244` | This project, IAM user `g2team7` |
| `default` | `372014757586` | Different personal account; not this project |

Project Region: **`us-east-1`**. A teammate must configure their own authorised login/profile; cloning does not create AWS access. Never share keys through GitHub. Profile names are local conveniences, not shared cloud resources.

Read-only checks (adapt the profile name if yours differs):

```bash
aws sts get-caller-identity --profile IS-459-BDA --region us-east-1
bash Implementation/scripts/check_aws_profile.sh IS-459-BDA
```

The guard checks both account and configured region. It aborts if either differs/missing; investigate rather than falling back to `default`. Its legacy default profile is `is459`, so always pass your chosen profile explicitly. Re-check identity at the time of any authorised cloud action. Explicitly pass `--profile`/`--region` on subsequent CLI commands and choose a verified profile/session for local SDK calls; do not assume a prior STS command changes the default account.

**No AWS deployment/run is required to start local development.** Project bucket/configuration is described in `aws/environment.json`, but its legacy status field is not an up-to-date deployment summary. Use `STATUS.md` and the newest scoped run/review evidence instead.

## 5. Shared AWS resources are not branch-isolated

- Coordinate with the component owner before editing shared Glue jobs, IAM, Catalog tables or Step Functions.
- For an authorised experiment, use distinct script paths, jobs where necessary, and fresh dataset/run/analysis output namespaces. Do not overwrite validated results or frozen releases.
- Do not reuse Q1's label-reading role for Q2. Keep references/evaluation inaccessible to detection.
- Paid runs, permissions and deletions must stay within the current user's explicit scope. The checkpoint's paused evaluator is not resumed by cloning or reading documentation. Existing exact attempt approval is historical and not blanket permission for new attempts.
- Record actual cloud actions, parameters, evidence and estimated costs in the ledger/checkpoint. Stop authorised compute after use; retain approved S3 artifacts. See [TEARDOWN.md](TEARDOWN.md).

## 6. Handoff and pull request

Before asking another person or AI to continue, record: your task/branch, changed files/contracts, commands/tests actually run, any cloud mutations or spend, exact output IDs/paths, and remaining blockers. Never paste credentials or signed URLs into the handoff. Update `STATUS.md` when completion state changes and the deployment checkpoint only when there is an actual deployment handoff to record.
