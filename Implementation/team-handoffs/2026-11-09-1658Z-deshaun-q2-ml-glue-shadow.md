# Q2 ML shadow validation for the October 30 release

- **Owner** Deshaun, with Codex. Deshaun confirmed the isolated cloud scope.
- **Status** IN_PROGRESS for TRACE. The isolated AWS test is complete. Deshaun approved publishing the separately verified AWS result as a historical replay using its measured numbers.
- **Review** [Draft PR #28](https://github.com/Kelvinpcw/is459-aml-project/pull/28).

Test the reduced Q2 shortlist as a separate Glue job against the existing October 30 cleaned facts and a verified projection of its case evidence. Glue can reconstruct the same fact projection directly from the archived, label-free Parquet inputs and must match its pinned hash. The job recomputes scores and exports case and payment tables to a new attempt prefix. The evaluator reads the outputs afterwards under separate access. The scope is one historical replay. [Previous findings](2026-11-09-1619Z-deshaun-q2-full-month-ml-replay.md)

Local checks rebuilt the full source projection and verified its hashes against the saved inputs. The three frozen payment models regenerated the same scores. The resulting shortlist and alert tables matched the checkpoint, and a separate evaluator verified the counts from the saved labels and original annotations. The local TRACE preview resolved original evidence across all supported pattern types and displayed the final date. The exact test outputs and deployment inputs are in the private operator record.

The managed Glue job rebuilt the complete clean fact projection and matched its pinned hash. All three models scored the full archive and the job reached a successful terminal state. The independent evaluation recovered all eligible patterns. The final alert and snapshot selections differ from the local checkpoint; two payment score files also differ. The AWS result remains isolated. No new compute is running, no trigger was added, and the temporary prefix was empty at verification. [AWS handoff procedure](../AWS_HANDOFF.md)

The approved scope is one immutable historical overlay and an update to the existing TRACE service using its existing role. The main release pointer stays selected and the historical view uses the exact evaluated AWS outputs. No new Glue run, schedule or retraining is in scope.
