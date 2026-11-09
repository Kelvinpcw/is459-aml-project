# Q2 ML shadow validation for the October 30 release

- **Owner** Deshaun, with Codex. Cloud resource owner confirmation is pending.
- **Status** PLANNED for AWS. Local validation uses the archived `full-20261030-v1` release.
- **Review branch** `agent/codex-q2-ml-findings`. The draft PR tracks the owner review.

Test the reduced Q2 shortlist as a separate Glue job against the verified projection of the published cleaned facts and existing case evidence. The job recomputes scores and exports case and payment tables to a new attempt prefix. The evaluator reads the outputs afterwards under separate access. The scope is one historical replay before any publication to TRACE. [Previous findings](2026-11-09-1619Z-deshaun-q2-full-month-ml-replay.md)

Local checks rebuilt the full source projection and verified its hashes against the saved inputs. The three frozen payment models regenerated the same scores. The resulting shortlist and alert tables matched the checkpoint, and a separate evaluator verified the counts from the saved labels and original annotations. The local TRACE preview resolved original evidence across all supported pattern types and displayed the final date. The exact test outputs and deployment inputs are in the private operator record.

AWS: none. The managed runtime and permissions have not been validated. Before a cloud run, build the native features and pinned dependencies for Glue Linux, verify the named AWS profile, confirm the job and prefix with the resource owner, and publish this plan in a draft PR. [AWS handoff procedure](../AWS_HANDOFF.md)

Keep the shadow outputs isolated. Use the separate evaluator's exact comparisons and a review of the release inputs before any TRACE update.
