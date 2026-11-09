# Q2 ML shadow validation for the October 30 release

- **Owner** Deshaun, with Codex. Deshaun confirmed the isolated cloud scope.
- **Status** COMPLETED. The verified AWS historical replay is live in TRACE.
- **Review** [PR #28](https://github.com/Kelvinpcw/is459-aml-project/pull/28).

Test the reduced Q2 shortlist as a separate Glue job against the existing October 30 cleaned facts and a verified projection of its case evidence. Glue can reconstruct the same fact projection directly from the archived, label-free Parquet inputs and must match its pinned hash. The job recomputes scores and exports case and payment tables to a new attempt prefix. The evaluator reads the outputs afterwards under separate access. The scope is one historical replay. [Previous findings](2026-11-09-1619Z-deshaun-q2-full-month-ml-replay.md)

Local checks rebuilt the full source projection and verified its hashes against the saved inputs. The three frozen payment models regenerated the same scores. The resulting shortlist and alert tables matched the checkpoint, and a separate evaluator verified the counts from the saved labels and original annotations. The local TRACE preview resolved original evidence across all supported pattern types and displayed the final date. The exact test outputs and deployment inputs are in the private operator record.

The managed Glue job rebuilt the complete clean fact projection and matched its pinned hash. All three models scored the full archive and the job reached a successful terminal state. The independent evaluation recovered all eligible patterns. The alert and snapshot selections differed from the local checkpoint. Deshaun approved publishing the separately verified AWS result using its measured metrics. Glue compute has ended; no trigger was added and the test temporary prefix was empty. [AWS handoff procedure](../AWS_HANDOFF.md)

The same verified AWS tables and original evidence were tested in the local TRACE app, then installed as an immutable historical overlay on the existing host using its existing role. The deployed dashboard source is `b22cbf4`. Live browser checks verified the metrics at a narrow panel width, a directed graph link and the original evidence download controls. The dashboard and proxy were healthy, and the current rules release pointer stayed unchanged. The previous application was retained for rollback. Future releases should independently validate a fresh chronological batch before considering routine scoring.

The GitHub source handoff includes the executed Glue source, local model producers, independent evaluator, overlay builder and editable architecture. AWS scope for the source handoff was none. [Source handoff](../ml_replay/README.md)
