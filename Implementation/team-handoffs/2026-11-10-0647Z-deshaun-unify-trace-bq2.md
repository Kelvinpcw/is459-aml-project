# Use the current BQ2 release in public TRACE

- **Owner** Deshaun with Codex
- **Branch and PR** [Full-volume BQ2 rollout](https://github.com/Kelvinpcw/is459-aml-project/pull/29)
- **Status** PLANNED
- **Evidence** Deployed dashboard and workflow inspection

The existing public TRACE site shows the pinned historical replay, whose pattern recovery used an 80% evidence threshold. The validated full-volume workflow reports complete matches. Use its existing immutable output to initialize the current BQ2 pointer in place of the daily smoke-test fixture, then configure the existing site to follow that pointer.

The scope covers the dashboard overlay and BQ2 pointer only. Confirm that the pointer still references the smoke fixture and the workflows are idle before updating it. Verify the displayed metrics and open original payment evidence on the public site. Reuse the host's existing read permissions and keep the historical artifacts available for audit. No new processing or schedule is planned.
