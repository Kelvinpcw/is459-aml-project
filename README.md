# IS459 AML data pipeline

Shared implementation and design context for a six-person team using the synthetic IBM HI-Medium anti-money-laundering dataset.

**The complete software path is implemented on `main`.** Detailed AWS validation records and the operational checkpoint remain local. **Public-safe AWS session summaries must be committed and pushed for team/AI handoff**; see [AWS handoff](Implementation/AWS_HANDOFF.md). Source/configuration is not proof of live cloud state.

## Start here — humans and AI assistants

| Read | Purpose |
| --- | --- |
| [AGENTS.md](AGENTS.md) | AI working rules: safety, data contracts, testing and collaboration |
| [Implementation/STATUS.md](Implementation/STATUS.md) | Current implementation scope and remaining work |
| [Implementation/AWS_HANDOFF.md](Implementation/AWS_HANDOFF.md) | Mandatory AWS session reporting, shared records and push/PR workflow |
| [Implementation/SETUP.md](Implementation/SETUP.md) | Local setup, data access and AWS profile checks |
| [Confirmed proposal](Proposal/Project_Proposal.md) | Business questions, requirements, analysis rules and evaluation protocol |
| [Pipeline explanation](Proposal/Architecture/Pipeline_Explanation.md) | How the target components connect |
| [Detailed architecture](Proposal/Architecture/Detailed/AWS_Architecture_Pack.pdf) | Technical diagrams; editable source is in the same folder |
| [PROJECT_CHECKPOINT.md](PROJECT_CHECKPOINT.md) | Historical deployment handoff, exact resource IDs and evidence |

To view an existing published release without restarting processing or EC2, follow [local visualization setup](Implementation/SETUP.md#visualization-without-restarting-cloud-compute).

For the independent **TRACE visual prototype**, open [`Visulization/index.html`](Visulization/index.html) locally; see its [README](Visulization/README.md). It works offline with invented fixtures, not actual pipeline results.

The newest scoped evidence wins over older status sentences. Read the checkpoint when resuming deployment, but **reading it is not an instruction to resume paid work**.

## What are we building?

- **Q1 — monitoring allocation:** Which payment formats and bank-pair segments have unusually high historical labelled laundering exposure relative to transaction volume?
- **Q2 — connected investigation:** Which account groups exhibit fan-in, fan-out or bounded cycles worth investigating? Generate leads without reading labels or pattern annotations.

Target workflow:

```text
S3 inputs → Glue preparation → label-free enriched facts
                                 ├─ Q1 + separate labels → risk summaries
                                 └─ Q2 without labels → cases + evidence
                                                          ↓
                         facts + cases + labels/annotations → evaluator

Complete outputs + quality reports + evaluation → shared release gate
    → one published-run manifest → dashboard using Athena + S3 case bundles

Step Functions coordinates the target workflow; EC2 hosts the target dashboard.
```

## Implementation and evidence

The branch adds conditional publication, a pinned read-only Streamlit dashboard, distributed fan/cycle detection, a separate chronological evaluator, on-demand orchestration and cleanup. The latest evaluator corrections passed 87 synthetic tests; the deployment templates pass cfn-lint. Frozen detection rules and evaluator settings are preserved while complete evidence is packed into bounded, checksum-verified schema3 ZIP shards.

The full implementation uses distributed fan aggregation and bounded, degree-eligible 2–4-cycle joins over overlapping seven-day daily snapshots. The frozen first-minute driver detector is preserved separately; its pilot is not proof of full-data effectiveness. See [status](Implementation/STATUS.md) and [runbook](Implementation/RUNBOOK.md).

Raw AWS reports, detailed cost records and operational checkpoints are intentionally local. Fresh clones contain neither these private records nor source/generated data. From 29 October 2026, agents must publish sanitised session summaries, including observations, cost basis, cleanup and next steps, in [`Implementation/team-handoffs/`](Implementation/team-handoffs/). Prior private runs have not been retroactively verified or published. Previously committed pilot records are historical; never infer current resource state or deployment authority from them.

## Code map

| Location | Contents |
| --- | --- |
| `Implementation/jobs/` | Editable preparation, Q1, Q2 and evaluator source |
| `Implementation/scripts/` | Input builders, manifest helpers, audits and verifiers |
| `Implementation/sql/` | Athena schemas, validation and analytical queries |
| `Implementation/tests/` | Local synthetic regression tests, including Spark tests |
| `Implementation/releases/` | Frozen code used/reviewed for specific cloud attempts; preserve unchanged |
| `Implementation/aws/` | Resource configuration, manifests, run records and review evidence |
| `Implementation/results/` | Human-readable validation findings and limitations |
| `Implementation/team-handoffs/` | Dated, public-safe collaboration/AWS session summaries; not raw operational evidence |
| `Implementation/evidence/` | Retained console screenshots; historical, not a live inventory |
| `Proposal/` | Confirmed requirements and target architecture, not old question-selection drafts |
| `Visulization/` | Offline TRACE dashboard design, invented fixtures and local UI/model checks |

## Working together

Use one feature branch per task and a pull request reviewed by a teammate. A Git branch **does not isolate AWS**: use distinct development jobs/script paths/output namespaces when cloud testing is authorised. Never overwrite another person's run.

Component ownership areas (assign actual owners; these are not claims that implementation is missing):

1. Ingestion/preparation and wider input scope.
2. Q1 multi-day analytics and dashboard query contracts.
3. Scalable Q2 fan-in/fan-out.
4. Scalable bounded cycles and shared case/evidence contracts.
5. Dashboard and graph explorer.
6. Evaluation/orchestration/release integration, supported by component owners.

```bash
git pull --ff-only
git switch -c feature/your-task
# Edit and test locally, then stage only your task's files.
git add path/to/your/files
git commit -m "Describe your change"
git push -u origin feature/your-task
```

Do not `git add .`: the tree may contain someone else's edits, gitignored AWS records or macOS `Name 2.md` duplicates. Stage explicit paths. `main` is shared — push your branch and open a PR rather than committing to `main`.

Include changed contracts, tests actually run, and any AWS effects/costs in the pull request. Record the deployed Git commit and job arguments when deploying. Review schema changes with downstream owners before merging.

**Required AI completion rule:** after each task, commit/push the scoped changes and open/update a PR. For AWS work, first read the [handoff procedure](Implementation/AWS_HANDOFF.md), coordinate shared-resource ownership, and publish a sanitised session record even if the attempt failed or was read-only. Before starting, check open PRs as well as `main`; unmerged handoffs still matter. If a push is blocked, explicitly report **NOT SYNCED TO GITHUB**. A pushed branch is visible but is not merged into `main` until a teammate reviews it. These are agent instructions, not an automated AWS/GitHub enforcement service.

## Give your AI assistant this starting prompt

> Read AGENTS.md, README.md, Implementation/STATUS.md and Implementation/AWS_HANDOFF.md, plus the newest shared handoffs and open PRs relevant to my task. My assigned task is: [describe it]. Distinguish implemented code, local tests and actual cloud observations. Start locally; do not run, deploy, change IAM, overwrite outputs or delete AWS resources without my explicit scoped approval. After authorised AWS work, publish a sanitised handoff with outcome, costs, cleanup, blockers and next steps. Commit/push scoped changes and open/update a PR; do not merge it yourself. Report the commit/PR and tests actually run, or explicitly say NOT SYNCED TO GITHUB and why.

AI tools that do not automatically load `AGENTS.md` should be explicitly asked to read it.

## Data and credentials

The large source dataset and generated `Implementation/data/` artifacts are intentionally not in Git. Cloning does not download them. See [SETUP.md](Implementation/SETUP.md) before requesting data or attempting a replay. Never commit credentials, signed S3 URLs or environment secrets; this repository is public.

The shared project account is **`160885259244`**, Region **`us-east-1`**. Each member must independently authenticate and verify their own AWS console login or CLI profile. Local profile names and credentials are not shared by GitHub; do not assume your default account is correct.
