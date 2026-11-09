# Q2 ML shadow validation for the October 30 release

- **Owner** Deshaun, with Codex. Deshaun confirmed the isolated cloud scope.
- **Status** IN_PROGRESS. The named profile passed verification and the Linux build is underway.
- **Review** [Draft PR #28](https://github.com/Kelvinpcw/is459-aml-project/pull/28).

Test the reduced Q2 shortlist as a separate Glue job against the verified projection of the published cleaned facts and existing case evidence. The job recomputes scores and exports case and payment tables to a new attempt prefix. The evaluator reads the outputs afterwards under separate access. The scope is one historical replay before any publication to TRACE. [Previous findings](2026-11-09-1619Z-deshaun-q2-full-month-ml-replay.md)

Local checks rebuilt the full source projection and verified its hashes against the saved inputs. The three frozen payment models regenerated the same scores. The resulting shortlist and alert tables matched the checkpoint, and a separate evaluator verified the counts from the saved labels and original annotations. The local TRACE preview resolved original evidence across all supported pattern types and displayed the final date. The exact test outputs and deployment inputs are in the private operator record.

The pinned October 30 manifest and the existing project jobs were verified read-only. The owner approved a dedicated job, restricted role and fresh attempt prefix. The managed Glue result is pending. [AWS handoff procedure](../AWS_HANDOFF.md)

Keep the shadow outputs isolated. Use the separate evaluator's exact comparisons and a review of the release inputs before any TRACE update.
