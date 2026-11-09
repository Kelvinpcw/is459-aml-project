# Fresh BQ2 AWS smoke test

- **Owner** Deshaun, with Codex.
- **Status** IN_PROGRESS. One manual run approved on the separate fresh BQ2 stack.
- **Scope** Build the Linux runtime, deploy the reviewed stack with the upload rule disabled, and run one synthetic batch through all five stages. Use the dedicated fresh BQ2 input, stage and publication namespaces.

The two local fixtures passed through preparation, detection, all five fitted estimators, evaluation, publication and the TRACE app. The AWS test must verify the same chain in a single Step Functions execution and open the published shortlist and original evidence in a TRACE preview. The shared workflow and live dashboard are outside this test scope. [Local workflow handoff](2026-11-09-2019Z-deshaun-fresh-bq2-workflow.md)

The project identity and isolated input and output namespaces passed the preflight. The Linux package and change set are under review before the manual run. [Draft PR](https://github.com/Kelvinpcw/is459-aml-project/pull/29) · [AWS handoff rules](../AWS_HANDOFF.md)
