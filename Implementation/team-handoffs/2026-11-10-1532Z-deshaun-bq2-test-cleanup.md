# Retire isolated BQ2 test infrastructure

- **Owner** Deshaun, with Codex.
- **Status** PLANNED.
- **Scope** Deshaun approved removal of the isolated daily mock, smoke child and historical replay CloudFormation stacks after checking live dependencies.

The main Q1 and rules-based Q2 jobs and the production ML child do not reference these stacks. The mock calls the smoke child, so the mock goes first, followed by the smoke and historical replay stacks. The test triggers are disabled, both test workflows have no running executions and all six test Glue jobs are idle. The stacks own no S3 resources or shared exports. Published outputs, trained models and public TRACE are outside the cleanup scope.

Cleanup uses CloudFormation. Verify terminal stack states, retained jobs and workflows, and the published TRACE output. No processing is planned. See the [daily mock](2026-11-10-0126Z-deshaun-daily-bq2-mock.md) and [historical replay](2026-11-09-1658Z-deshaun-q2-ml-glue-shadow.md) handoffs.
