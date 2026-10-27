# Exact AWS access-grant review — 28 October 2026

Account **160885259244**, Region **us-east-1**. CodeVersion **full-v1**, RunId/ReleaseId **full-20261028-v1**. Final total project ceiling **US$30**. No stack or full-data paid run has started. Automatic approval review rejected stack creation pending action-time approval of these new grants.

The two reviewed templates create these service roles; no person receives a new login or credential:

| Role | Access |
| --- | --- |
| `is459-aml-full-prepare` | Glue-only trust; reads new full raw input, writes only this run’s curated facts, separate labels, preparation quality/quarantine/temp/logs. |
| `is459-aml-full-risk` | Glue-only; reads this run’s facts/labels/preparation report, writes only its Q1 summaries/quality/temp/logs. |
| `is459-aml-full-detect` | Glue-only; reads label-free facts and sanitised manifest; writes only its Q2 cases/quality/temp/logs. Explicit deny on raw, references/labels/annotations, Q1 and evaluation reads. |
| `is459-aml-full-evaluate` | Glue-only; reads this run’s facts, labels, cases, pinned annotations and quality reports; writes only evaluator artifacts/calibration/quality/temp/logs. Cannot modify detection inputs. |
| `is459-aml-full-control` | Glue-only; reads this run’s reports/outputs, creates only the dedicated full Catalog tables/partitions, writes sanitised manifest and the conditional published release/current pointer. |
| `is459-aml-full-workflow` | Step-Functions-only trust; may start/read/stop only the five named full-project Glue jobs. No IAM or raw-data grant. |
| `is459-aml-dashboard` | EC2-only trust; read-only published summaries/cases/metrics and approved Catalog tables; writes only dashboard Athena results. Explicit deny raw/curated/references reads. Adds the standard AmazonSSMManagedInstanceCore managed policy and an instance profile for private SSM access. |

No recurring schedule or public application ingress. The temporary dashboard has no inbound rules, uses IMDSv2 and an encrypted root disk deleted with the instance. Creation of the full stack starts no processing; EC2 is created only for validation and removed afterward.

Exact policy action/resource statements are in the linked templates. No earlier pilot role/job/output is changed.

- [full-pipeline-stack.json](/Users/kelvinpoh/Desktop/Y4S1/IS459%20Big%20data/BDA%20Project/Implementation/deployment/full-pipeline-stack.json) — SHA256 `ce59687453c7e4a232acbeda2970b47a771f3be644ba565a3ee8e442b794ee29`
- [dashboard-stack.json](/Users/kelvinpoh/Desktop/Y4S1/IS459%20Big%20data/BDA%20Project/Implementation/deployment/dashboard-stack.json) — SHA256 `61ee7059411ea5d7f8077e2786a7493619161a04f83ccb6c19f7e6547027755f`
