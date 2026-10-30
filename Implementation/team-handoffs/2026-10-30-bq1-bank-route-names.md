# BQ1 bank route names

The user requested clearer bank routes on the existing EC2 dashboard and a source push. Labels now show `Bank of Miami (11) → First Bank of Dallas (214)` throughout monitoring views, including the inspection selector. A caption explains sending-to-receiving direction and that a route can include many accounts. IDs remain visible because bank names are not unique.

Verified the transaction CSV's positional `From Bank` / `To Bank` fields against `Bank ID` / `Bank Name` in the raw accounts CSV. Lookup export includes bank names and IDs only. Duplicate accounts do not multiply aggregates; the lookup changes display text, with no analytical join. Unknown names retain IDs; conflicting names for an ID fail validation. Setup documents exporting the lookup for future deployments.

Validation: four synthetic label/UI tests, seventeen existing dashboard tests and eight release/dashboard tests passed. Raw lookup loaded successfully. The deployed app matched the reviewed base checksum before patching; updated files passed checksum, compilation, example mapping and service-health checks. A rollback backup was retained on the instance. Live browser verification is recorded privately.

Only the existing dashboard service was restarted. No new instance, IAM grant, data pipeline run, detector/evaluator setting change, publication change or frozen-release modification occurred. Existing manual hosting remains running at the user's request; normal hosting/request/storage costs continue. Deployment records, raw lookup, signed download link and AWS details remain private and are excluded from the source PR. No merge is requested.
