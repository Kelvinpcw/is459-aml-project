# Connected Cases layout

- **Owner:** Deshaun, with Codex.
- **Branch:** `agent/codex-q2-aws-layout`.
- **Status:** PLANNED — source checks underway; the live dashboard is unchanged.

Port the locally reviewed All snapshots filter, scrollable case cards, and clickable payment arrows to the AWS Connected Cases view. Page the pinned published case index from a private cache on the dashboard host, and keep the existing verified evidence and downloads. Monitoring, evaluation, case detection and published data stay as they are.

Scope is the existing dashboard service. Check the live baseline before installation, build and verify the index before restarting the app, and retain a rollback copy. No processing rerun, release publication, infrastructure or permissions changes are part of this update.
