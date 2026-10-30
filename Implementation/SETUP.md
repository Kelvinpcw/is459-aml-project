# Task-specific local setup

New teammate: start with [TEAM_START_HERE.md](../TEAM_START_HERE.md). Changes/push/review: [CONTRIBUTING.md](../CONTRIBUTING.md). Current work: [STATUS.md](STATUS.md), [handoffs](team-handoffs/README.md) and open PRs. **No AWS deployment is part of setup.**

Commands below are Unix-shell examples run from the repository root. Windows users can run the Python tool check with `py -3`; have the agent adapt activation/interpreter paths and use an approved Bash environment for `.sh` helpers. Do not blindly paste Unix paths into PowerShell.

## 1. Check tools and choose a branch

```bash
python3 Implementation/scripts/project_doctor.py --task docs
```

Choose `docs`, `prototype`, `dashboard` or `pipeline`. This only checks local versions; it doesn't install, authenticate, read AWS config or verify cloud completion. Compare reported versions with the requirements below. Use the [contribution workflow](../CONTRIBUTING.md) to fetch/check current work and create a clean task branch before editing.

## 2. Local Python/Spark environment

Recorded processing-test environment: **Python 3.11, PySpark 3.5.6, Java 21**. Install the chosen Python/JDK with the user's permission, and verify `python3.11 --version` / `java -version`. Set `JAVA_HOME` to the intended JDK if needed; Python dependencies do not install Java.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r Implementation/requirements.txt
python -m pytest Implementation/tests -q
```

Tests use synthetic fixtures and local Spark; they don't require original data or AWS credentials. Run the relevant subset for a focused change and report the actual command/result. Missing Java/dependencies or an unrun test is a setup limitation, not a passed check. This guide's cleanup did not run the full Spark suite.

## Visualization without restarting cloud compute

The **connected TRACE dashboard** is `Implementation/dashboard/app.py`. It reads an existing verified published release through Athena/S3. The separate `Visulization/` concept uses invented fixtures and works offline. Viewing connected results needs the user's own authorised AWS access and agreed bounded-read scope; it can incur query/request charges.

```bash
python3.11 -m venv .venv-dashboard
.venv-dashboard/bin/python -m pip install -r Implementation/dashboard/requirements.txt 'botocore[crt]==1.43.119'
bash Implementation/scripts/start_local_dashboard.sh YOUR_PROJECT_PROFILE
```

Replace `YOUR_PROJECT_PROFILE`. No Java, Spark, original data or EC2 is needed for this path. Open `http://127.0.0.1:8501/` after startup. The launcher verifies account/configured region, binds only to localhost and uses the bounded dashboard workgroup. The app pins a published release, limits query runtime and provides complete evidence downloads beyond graph previews. Starting it doesn't upload, deploy or start processing.

Ctrl+C stops the local server. Set `AML_DASHBOARD_PYTHON` to another intended environment's executable if needed; never point it at a teammate's laptop path. After pulling changed source, restart the server from that checkout: an already running server can still show an old version. Identify the owner of an occupied port before stopping anything. See [runbook](RUNBOOK.md).

For a focused synthetic UI/data regression check using this environment:

```bash
PYTHONPATH=Implementation:Implementation/tests .venv-dashboard/bin/python -m unittest test_dashboard_trends test_dashboard_navigation test_dashboard_presentation test_dashboard_app test_release_dashboard -q
```

## 3. Original data and generated artifacts

A fresh clone excludes `Ibm_dataset_medium/` and generated `Implementation/data/`, including private operator records. These are unnecessary for synthetic tests and offline design review.

Obtain approved originals from the [IBM dataset on Kaggle](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml), following its access/licence terms; provenance is in [IBM/AML-Data](https://github.com/IBM/AML-Data). Ask the relevant owner for a required existing input/output manifest before generating or uploading more data. Never commit the dataset.

`build_development_input.py` is a local date-selection helper with deterministic original-file/record source IDs. Its default is only 1 September 2022. It is not a full-pipeline start command and should not run automatically during onboarding. Use a fresh local destination for an explicitly requested replay; preserve completed evidence and frozen releases.

## 4. AWS identity — verify before cloud work

Follow the [onboarding login routes](../TEAM_START_HERE.md#4-aws-login--only-for-an-approved-activity). Project account **`160885259244`**, workload region **`us-east-1`**. Each member uses their own approved identity/profile; profile names are local, not shared AWS resources.

After completing the appropriate interactive login:

```bash
aws sts get-caller-identity --profile YOUR_PROJECT_PROFILE --region us-east-1
bash Implementation/scripts/check_aws_profile.sh YOUR_PROJECT_PROFILE
```

The guard requires exactly one explicit profile, refuses a missing/wrong configured region, and queries identity with the explicit workload region. It doesn't silently use a default. Identity/region verification is read-only; it doesn't grant permissions, approve spending or establish completed jobs. Recheck before authorised cloud work and pass explicit `--profile` / `--region` on subsequent CLI calls. Local SDKs need the explicitly selected verified session too.

Use [VERIFY_PROGRESS.md](VERIFY_PROGRESS.md) for read-only completion checks. Missing access/evidence is a blocker to report, not a reason to add IAM permissions or repeat a run. Use [AWS_HANDOFF.md](AWS_HANDOFF.md) for state-changing AWS work: coordination, private detailed records and a pushed public-safe summary. A purely read-only check needs no handoff or PR.

## 5. Hand over your work

Follow [CONTRIBUTING.md](../CONTRIBUTING.md). Update affected docs/status, add a [task handoff](team-handoffs/README.md), review the exact diff, stage explicit paths and push a PR. Verify the remote head and report its commit/link. A merge doesn't deploy cloud code or refresh another laptop's app. If publication fails, say **NOT SYNCED TO GITHUB**; keep the local handoff and name the blocker.

## Bank names in BQ1 route labels

BQ1 displays `Bank of Miami (11) → First Bank of Dallas (214)` for the sending-to-receiving bank route. IDs remain the grouping keys; shared names do not merge banks.

Local dashboards use `Ibm_dataset_medium/HI-Medium_accounts.csv`. For a deployed dashboard, generate a bank-only lookup from the same dataset:

```bash
python3 Implementation/dashboard/bank_labels.py /path/to/HI-Medium_accounts.csv /tmp/bank_names.csv
```

Include that generated CSV beside `Implementation/dashboard/app.py` in the deployment package, or set `AML_BANK_NAMES_CSV` to its installed path. Do not commit source/generated datasets. Only `Bank ID` and `Bank Name` are exported; account/entity data is omitted. Conflicting names for one normalised ID fail validation. Missing lookups retain explicit unknown-bank labels with IDs and a warning.
