# Connected Cases layout

- **Owner:** Deshaun, with Codex.
- **Branch / PR:** `agent/codex-q2-aws-layout`, [draft PR #25](https://github.com/Kelvinpcw/is459-aml-project/pull/25).
- **Status:** COMPLETED — deployed and verified on the existing AWS dashboard on 8 November 2026.

Port the locally reviewed All snapshots filter, scrollable case cards, and clickable payment arrows to the AWS Connected Cases view. Page the pinned published case index from a private cache on the dashboard host, and keep the existing verified evidence and downloads. Monitoring, evaluation, case detection and published data stay as they are.

The deployed dashboard source is `5fd7741`. The staged and installed files passed checksum checks, and the published index matched the current release before the restart. Streamlit and proxy health passed. Live browser checks confirmed the All snapshots count, independent queue scrolling and pagination, and a published fan-in arrow filtering the evidence table to its 15 payments. All 32 focused local tests passed; the local replay also validated the complete published index. The package builder now includes the case components' static assets for future dashboard packages.

Only the existing dashboard service was restarted. Its previous application file is retained for rollback. The host remains running under the existing manual uptime arrangement. No processing rerun, data publication, infrastructure or permissions changes occurred. The source PR remains open and unmerged.
