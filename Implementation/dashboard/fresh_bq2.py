"""Load and display the currently published fresh BQ2 batch."""

from datetime import date, timedelta
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard.ml_replay import Replay, parquet_table, render_explorer
from dashboard.presentation import PATTERNS, kpis, period
from pipeline.bq2_release import BQ2_CURRENT_URI, LocalBQ2Objects, TABLES, release_uri
from pipeline.release import read_object, sha, verify_ref


@st.cache_data(show_spinner=False, max_entries=4)
def load_fresh_release(_s3, uri: str, checksum: str) -> Replay:
    release = verify_ref(_s3, {"uri": uri, "sha256": checksum})
    if release["schema_version"] != 1 or release["release_kind"] != "fresh-bq2" or uri != release_uri(release["release_id"]):
        raise ValueError("Invalid BQ2 release descriptor")
    prefix = uri.removesuffix("release.json")
    if release["shortlist"]["uri"] != prefix + "manifest.json" or release["evaluation"]["uri"] != prefix + "evaluation.json":
        raise ValueError("BQ2 release references escape the published batch")
    raw = read_object(_s3, release["shortlist"]["uri"])
    if sha(raw) != release["shortlist"]["sha256"]:
        raise ValueError("Published BQ2 shortlist changed")
    shortlist = json.loads(raw)
    evaluation = verify_ref(_s3, release["evaluation"])
    if (any(shortlist[key] != release[key] for key in ("release_id", "dataset_version", "run_id", "cutoff"))
            or shortlist["analysis_id"] != release["q2"]["analysis_id"]
            or evaluation["schema_version"] != 1 or evaluation["status"] != "PASSED"
            or evaluation["release_id"] != release["release_id"]
            or evaluation["shortlist_manifest_sha256"] != sha(raw)
            or evaluation["detector_report_sha256"] != shortlist["detector_report_sha256"]
            or evaluation["scored_payments"] != shortlist["scored_payments"]):
        raise ValueError("Published BQ2 validation, shortlist and release identities disagree")
    metrics = {**shortlist, **evaluation}
    tables = {}
    for name, count_key in TABLES.items():
        artifact = shortlist["artifacts"][name]
        filename = name + ".parquet"
        if artifact["file"] != filename or artifact["rows"] != shortlist[count_key]:
            raise ValueError(f"Invalid BQ2 artifact reference: {name}")
        tables[name] = parquet_table(_s3, prefix, filename, artifact["sha256"], artifact["rows"])
    return Replay(release, metrics, tables["ranked_cases"], tables["payment_alerts"], tables["evidence_index"])


def fresh_bq2(s3, pointer_uri: str) -> Replay:
    if pointer_uri != BQ2_CURRENT_URI:
        raise ValueError("Require the project BQ2 release pointer")
    pointer = json.loads(read_object(s3, pointer_uri))
    return load_fresh_release(s3, pointer["uri"], pointer["sha256"])


def batch_caption(replay: Replay) -> str:
    metrics = replay.metrics
    last = date.fromisoformat(metrics["cutoff"]) - timedelta(days=1)
    return f"Batch {period(metrics['batch_start'], last.isoformat())} · Release {replay.release['release_id']}"


def fresh_evaluation(replay: Replay) -> None:
    m = replay.metrics
    st.subheader("Fresh batch ML evaluation")
    st.caption(batch_caption(replay))
    precision, recall = m["payment_precision"], m["payment_recall"]
    patterns = f"{m['recovered_patterns']:,}/{m['eligible_patterns']:,}" if m["eligible_patterns"] else "Unavailable"
    st.markdown(kpis([
        ("Payment precision", f"{precision:.4%}" if precision is not None else "Unavailable", "Share of labelled alerts"),
        ("Payment recall", f"{recall:.4%}" if recall is not None else "Unavailable", "Share of verified positive payments found"),
        ("Pattern recovery", patterns, "Annotations fully matched by one ranked case"),
        ("New payment alerts", f"{m['eligible_alerts']:,}", "Distinct payments in this batch"),
    ]), unsafe_allow_html=True)
    st.caption(f"Verified labels cover {m['labelled_payments']:,} of {m['eligible_payments']:,} new payments "
               f"and {m['labelled_alerts']:,} of {m['eligible_alerts']:,} new alerts.")
    st.caption(f"{m['scored_payments']:,} payments scored across the batch and its available history.")
    if m["by_pattern"]:
        st.dataframe(pd.DataFrame([{"Pattern": PATTERNS[key], "Recovered": value["recovered"],
                                    "Eligible": value["eligible"]} for key, value in m["by_pattern"].items()]),
                     hide_index=True, width="stretch")
    st.caption(f"Model bundle SHA-256 {m['model_bundle_sha256']}")


def local_bq2_workspace(mirror: Path) -> None:
    store = LocalBQ2Objects(mirror)
    st.title("TRACE · Fresh batch BQ2")
    view = st.sidebar.radio("Workspace", ["Connected cases", "Evaluation & coverage"], key="fresh_bq2_workspace")
    replay = fresh_bq2(store, BQ2_CURRENT_URI)
    if view == "Connected cases":
        render_explorer(store, replay, batch_caption(replay))
    else:
        fresh_evaluation(replay)
