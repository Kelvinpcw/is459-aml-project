# TRACE AWS cleanup plan

- **Owner** Kelvin, with Codex. Deshaun owns the test workflows and ML replay.
- **Branch** `agent/codex-trace-aws-cleanup`.
- **Status** PLANNED. Awaiting confirmation from the resource owner for shared test resources and review of the exact S3 deletion list.
- **Evidence kind** Read-only AWS inventory and release manifest checksum verification on 10 November 2026.

Use the existing main Step Functions workflow as the operator entry point. The live main definition calls the full-volume Daily BQ2 child and still supports the historical workflow. Preserve both definitions and their Glue jobs. Preserve the public TRACE host, both current release pointers and all data, code, model bundles and evidence they or the retained workflows use. The two routes have distinct publication targets. [Daily route handoff](2026-11-10-0203Z-deshaun-daily-bq2-main.md) · [Public TRACE handoff](2026-11-10-0647Z-deshaun-unify-trace-bq2.md)

The disabled mock and its smoke-test child are cleanup candidates, including their dedicated disabled triggers and Glue jobs. Confirm ownership, dependencies and any evidence retention before retiring their CloudFormation stacks. The earlier ML shadow job is a separate candidate and its artifacts need a provenance and rollback check. None of the four workflows had running executions at inspection. No active runs appeared in the inspected recent Glue history.

Inventory S3 against both release manifests, retained workflows, Glue job settings, Catalog locations, dashboard configuration and rollback or assessment needs. Bucket versioning is absent. Limit any later deletion to exact reviewed keys, preserve the execution proof and retained releases, and recheck the inventory before acting. Keep raw inputs by default, including teammate-owned inputs. Keep the detailed inventory private.

AWS scope so far is read-only. No resources or objects deleted, no compute started or stopped, no schedules changed. Update this handoff before and after any approved AWS mutation. [AWS handoff procedure](../AWS_HANDOFF.md)
