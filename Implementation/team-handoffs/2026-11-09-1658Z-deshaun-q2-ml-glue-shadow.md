# Q2 ML shadow validation for the October 30 release

- **Owner** Deshaun, with Codex. Deshaun confirmed the isolated cloud scope.
- **Status** COMPLETED for the isolated AWS test. Exact parity failed, so the TRACE update was held.
- **Review** [Draft PR #28](https://github.com/Kelvinpcw/is459-aml-project/pull/28).

Test the reduced Q2 shortlist as a separate Glue job against the existing October 30 cleaned facts and a verified projection of its case evidence. Glue can reconstruct the same fact projection directly from the archived, label-free Parquet inputs and must match its pinned hash. The job recomputes scores and exports case and payment tables to a new attempt prefix. The evaluator reads the outputs afterwards under separate access. The scope is one historical replay. [Previous findings](2026-11-09-1619Z-deshaun-q2-full-month-ml-replay.md)

Local checks rebuilt the full source projection and verified its hashes against the saved inputs. The three frozen payment models regenerated the same scores. The resulting shortlist and alert tables matched the checkpoint, and a separate evaluator verified the counts from the saved labels and original annotations. The local TRACE preview resolved original evidence across all supported pattern types and displayed the final date. The exact test outputs and deployment inputs are in the private operator record.

The managed Glue job rebuilt the complete clean fact projection and matched its pinned hash. All three models scored the full archive and the job reached a successful terminal state. The independent evaluation recovered all eligible patterns. The final alert and snapshot selections differ from the local checkpoint; two payment score files also differ. The AWS result remains isolated. No new compute is running, no trigger was added, and the temporary prefix was empty at verification. [AWS handoff procedure](../AWS_HANDOFF.md)

The existing TRACE service and published rules pointer were left in place. The locally tested historical view is ready on the branch. To release the independently measured AWS replay, agree to use its actual metrics as the checkpoint, or resolve the score differences and repeat parity validation under a separately authorised attempt. No automatic scoring or retraining is in scope.
