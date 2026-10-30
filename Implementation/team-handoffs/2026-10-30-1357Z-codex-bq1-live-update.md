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
