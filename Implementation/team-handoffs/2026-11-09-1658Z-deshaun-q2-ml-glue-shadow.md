# Q2 ML shadow validation for the October 30 release

- **Owner** Deshaun, with Codex. Deshaun confirmed the isolated cloud scope.
- **Status** IN_PROGRESS. The named profile and Linux build passed verification. The managed replay is pending.
- **Review** [Draft PR #28](https://github.com/Kelvinpcw/is459-aml-project/pull/28).

Test the reduced Q2 shortlist as a separate Glue job against the existing October 30 cleaned facts and a verified projection of its case evidence. Glue can reconstruct the same fact projection directly from the archived, label-free Parquet inputs and must match its pinned hash. The job recomputes scores and exports case and payment tables to a new attempt prefix. The evaluator reads the outputs afterwards under separate access. The scope is one historical replay. [Previous findings](2026-11-09-1619Z-deshaun-q2-full-month-ml-replay.md)

Local checks rebuilt the full source projection and verified its hashes against the saved inputs. The three frozen payment models regenerated the same scores. The resulting shortlist and alert tables matched the checkpoint, and a separate evaluator verified the counts from the saved labels and original annotations. The local TRACE preview resolved original evidence across all supported pattern types and displayed the final date. The exact test outputs and deployment inputs are in the private operator record.

The pinned October 30 manifest and the existing project jobs were verified read-only. The owner approved a dedicated job, restricted role and fresh attempt prefix. The managed Glue result is pending. [AWS handoff procedure](../AWS_HANDOFF.md)

If the evaluator and the case and payment identities match the verified local replay, the owner authorised a historical ML shortlist on the existing TRACE host. The locally tested view reads a separate pinned ML archive and keeps the latest rules release available. No automatic scoring or retraining is in scope.
