# Fresh BQ2 AWS smoke test

- **Owner** Deshaun, with Codex.
- **Status** PLANNED. One manual run approved on the separate fresh BQ2 stack.
- **Scope** Build the Linux runtime, deploy the reviewed stack with the upload rule disabled, and run one synthetic batch through all five stages. Use the dedicated fresh BQ2 input, stage and publication namespaces.

The two local fixtures passed through preparation, detection, all five fitted estimators, evaluation, publication and the TRACE app. The AWS test must verify the same chain in a single Step Functions execution and open the published shortlist and original evidence in a TRACE preview. The shared workflow and live dashboard are outside this test scope. [Local workflow handoff](2026-11-09-2019Z-deshaun-fresh-bq2-workflow.md)

Paid compute starts only after the signed-in project identity, immutable package, isolated resources and change set have been checked. The run and any cleanup will be recorded here by outcome. [AWS handoff rules](../AWS_HANDOFF.md)
