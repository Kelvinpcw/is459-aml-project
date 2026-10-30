# Live BQ1 overview update

- Owner: Kelvin with Codex; branch `codex/bq1-dashboard-overview`, [PR #22](https://github.com/Kelvinpcw/is459-aml-project/pull/22).
- Status: COMPLETED — tested source deployed to the existing dashboard; source PR remains unmerged.
- Authority: the user explicitly requested the live update, then clarified that payment types must come first and currency choices must be busiest-first.

## Result

Payment-type rate/lift and traffic/labelled-share comparisons are visible first, followed by banks overall, with routes and route/format views available. All currencies is the default for counts/rates; the single Currency filter uses payment currency. Dropdown choices keep All currencies first, then currencies ordered by summed transaction count across the pinned published release, with names breaking count ties. The help explains that population. Monetary totals appear only for one selected currency. Sending-bank grouping counts each payment once, including within-bank transfers; route drill-down uses a matching sender-filtered baseline while headline/daily totals remain overall and are labelled separately.

Final deployed dashboard source is `ce122ef`. Both currency fields, receiving-currency API support, exact selected-currency amounts, N/L aggregation, support safeguards, bank names, TRACE styling, Q2/evaluation, frozen artifacts and release pinning are retained. No ingestion schedule was introduced.

## Verification and recovery

Thirty-six focused synthetic checks passed for SQL populations, payment-type exposure relative to size, busiest-first currency ordering, payment-first layout, bank labels, app/navigation, trends, charts, release contracts and public-dashboard configuration. During live testing, returning from routes exposed an old inspection-index string/int mismatch; the final source resets stale selections and includes a regression check.

The explicit project profile passed account/region verification. No overlapping open work or active host command was observed before deployment. Live files matched the reviewed baseline before installation. Each installed patch was checksum-verified with a retained backup and rollback guard. Final file hashes match the tested source; compilation, backend/public health and service/proxy checks passed. Browser verification confirmed the visible payment-type section, all-currency totals, busiest-first currency choices and error-free route-to-bank return. Earlier revision testing also verified USD filtering, bank-specific route baselines and exact amount strings. Final screenshot and detailed operational evidence stay private.

## AWS scope and handoff

Only the existing dashboard service was restarted; existing host remains running under the user's manual-hosting preference. No instance start/stop, processing rerun, IAM change, dataset publication, output deletion or schedule change occurred. Bounded dashboard viewing queries reused published results. Normal hosting/request/query/storage costs continue; exact resource/command IDs, hashes, measurements and cost assumptions are in the ignored private ledger/checkpoint. No account-wide cost or cleanup audit is claimed.

Next safe step: use the updated live dashboard and review the source PR. No merge was requested. The existing operator remains responsible for manual hosting shutdown when finished.
