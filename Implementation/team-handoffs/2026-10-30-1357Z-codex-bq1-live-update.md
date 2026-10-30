# Live BQ1 overview update

- Owner: Kelvin with Codex; branch `codex/bq1-dashboard-overview`, [PR #22](https://github.com/Kelvinpcw/is459-aml-project/pull/22).
- Status: IN_PROGRESS. The user explicitly requested updating the live dashboard after the source-only implementation.
- Scope: deploy the tested dashboard app, read-query helper and bank-label helper from source commit `72e10f4` onto the existing dashboard host. Preserve current bank-name lookup, styling, graph/evaluation code, service role, published release and manual-hosting preference. No processing rerun, IAM change, replacement instance, data publication or schedule is authorised or planned.
- Coordination: current main includes the previous bank-name update. No overlapping open PR or active instance command was observed. The operator's explicit profile passed project account/region verification; existing host is running and management agent is online. These are preflight observations, not deployment success.
- Plan: verify live file hashes against the prior reviewed version, retain a rollback backup, install a checksum-verified uniquely named private patch, compile and smoke-check, restart only the dashboard service, and verify health plus all-currency/bank-first UI and a currency/route interaction. Reuse existing immutable published results for bounded viewing reads.
- Validation available: 34 local synthetic source tests passed before deployment. No new cloud UI success is claimed at this stage.
- AWS scope/cost: existing host update and bounded dashboard verification reads only. Patch/request and existing hosting/query costs are recorded privately. No compute start/stop is planned; existing host remains running for user-controlled manual shutdown. No account-wide cost or cleanup audit is claimed.
- Detailed resource IDs, commands, hashes, private patch location, measurements and screenshots remain in the ignored operator record.
- Next step: publish this plan on the existing draft PR, then start the scoped update. On failure retain/restore the previous working dashboard and report the outcome before additional changes.

## User clarification during verification

The user explicitly highlighted BQ1's payment-type comparison. Added a visible Payment types relative to their size section alongside the bank overview rather than relying on the Compare dropdown. It includes supported relative-risk bars, transaction and historical-label counts, traffic share, labelled share, labelled rate, relative risk and support. This section uses the same date/currency/format population and remains overall when route drill-down selects one sending bank. Low-support types are visible and unranked. Thirty-five focused synthetic checks pass, including a smaller payment type accounting for a larger share of historical labels. Browser verification also caught a stale persisted inspection-index type when returning to banks; it is corrected with a regression check. These are presentation/read-query changes within the authorised existing-host update; live verification of the final revision is in progress.

## Final ordering clarification

The user requested payment types at the top and confirmed the currency dropdown should list busiest currencies first. Payment-type chart/table now precede bank comparisons; All currencies remains first, followed by currencies ordered by summed transaction count across the pinned published release (name breaks count ties). The dropdown help states that population. This ordering uses counts only and never combines monetary units. Thirty-six focused synthetic checks pass, including payment-first heading order and paid/receiving currency-order reconciliation. Final scoped deployment/verification is in progress.
