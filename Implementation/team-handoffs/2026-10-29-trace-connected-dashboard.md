# TRACE layout for the connected dashboard

- **Owner:** Kelvinpcw, assisted by Codex.
- **Branch / PR:** `feature/trace-connected-dashboard`; [PR #10](https://github.com/Kelvinpcw/is459-aml-project/pull/10).
- **Status:** COMPLETED — source published for teammate review; not merged.
- **Updated at:** 2026-10-29T19:07:54.022487+08:00.
- **Evidence kind:** local synthetic tests and fresh bounded AWS dashboard reads.

## Authorised scope and coordination

The user requested adapting TRACE's visual structure to the connected Streamlit dashboard, retaining published results, rolling reporting dates, daily trends and complete evidence downloads. This follows merged PRs #8 and #9. No other open PRs were found at task start. Based on main `0c039240ac0fa0002d64d387c2e8977ede428822`; initial layout source `2fd1e6c54fdf56fc1358e9f34f9d8e16be9921d9` was pushed before connected preview, followed by browser-driven responsive corrections. The final source commit is identified by the PR head and task report.

The planned record was pushed and a draft PR opened before cloud reads. Only the operator's local server and separate read-only query requests were used. No shared cloud job, output prefix, IAM role or publication pointer was modified. Existing US$30 total ceiling remains; no new processing, deployment or recurring schedule was authorised by this task.

## Changes and checks

- TRACE-inspired sidebar (compact menu on narrow screens), cards, full-baseline monitoring explanation, visible supported ranking, segment inspection, case queue and separate provenance page.
- Daily trends and rolling dates remain. Zero-label supported groups appear in volume/rate comparisons; low-support groups are unranked. Counts and shares use the same supplied population, not capped preview totals. Exact monetary strings remain intact.
- Case explanations use actual published participant/evidence counts and exclusive windows. Graph bounds and complete evidence downloads remain intact. Existing evaluation metrics/denominators and baseline comparisons are preserved.
- Offline `Visulization/` fixtures remain separate and are not imported by the connected app. Detector/evaluator rules, analytical SQL, immutable published data and frozen releases are unchanged. Future bundle creation includes the new stylesheet; the packaging test writes only to a temporary directory.
- **25 local tests passed** in 2.272 seconds: trends, navigation, explanation support/shares/escaping, graph safety, complete source evidence, release retention and bundle assets. Final CSS corrections were verified in the browser. Markdown local file links: 22 checked, zero missing. `git diff --check` passed. No Spark/backend processing suite or new full-data replay was run.
- Browser verified monitoring, the case queue/graph/window explanation, evaluation and provenance. Wide 1440px and narrow 618px layouts checked; viewport override reset. Screenshots and raw query records remain private with the operator.

## AWS observations, cost and cleanup

- Explicit project profile passed the account/region launcher guard for expected project account / `us-east-1`. The app independently checked its SDK identity. A separate short-timeout SDK diagnostic timed out; the connected app subsequently loaded the published outputs successfully. No credentials or profile files were published.
- Reused the existing immutable published release. Dashboard interactions made read-only S3 requests and bounded Athena queries; no Glue processing, EC2, IAM, orchestration or publication changes occurred.
- Query metadata observation: **14 queries, all SUCCEEDED**, total scanned bytes **623,367,146**, zero unprocessed IDs. The requests were bounded to the existing dashboard workgroup's 512 MB/query limit and app's 30-second cancellation policy. Related preview retries/restarts are included. No observed preview query remained running at this check.
- Cost basis: measured scan volume only; actual billed AWS dollars and account-wide remaining budget were not queried. Small Athena/S3 read charges apply. No hourly cloud compute was started by this task. This is not an account-wide cleanup/cost audit; pre-existing cloud resource state was not rechecked.
- Earlier local preview processes were stopped. The final localhost-only dashboard remains running intentionally for the user's review at port 8501. It is laptop compute; further interaction can make bounded AWS reads. No automatic polling/schedule was added.

## Handoff

Review/merge PR #10 through a teammate. The operator can reuse the current local preview or restart it with `start_local_dashboard.sh` from this feature checkout and their verified profile. The launcher uses that checkout's source; an older checkout can display an older UI. No frozen dashboard ZIP was replaced or uploaded. Private operator checkpoint and raw evidence remain local; prior full-pipeline/cloud-cleanup history was not retroactively verified or published.

GitHub sync: source and this sanitised record are committed/pushed on the task branch; final report verifies the remote head. Do not treat this completed preview as approval to start processing or deploy another service.
