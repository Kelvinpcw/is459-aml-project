"""Show a verified historical ML shortlist alongside the published rules."""

from datetime import date, timedelta
from io import BytesIO
import json
from typing import NamedTuple, TypedDict

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import streamlit as st

from dashboard.case_connections import render_graph
from dashboard.data import full_evidence_archive, get_case, read_evidence_part
from dashboard.presentation import PATTERNS, kpis, period
from pipeline.release import read_object, sha, split_uri, verify_ref


class PatternResult(TypedDict):
    recovered: int
    eligible: int


class ReplayMetrics(TypedDict):
    release_id: str
    first_date: str
    last_date: str
    payments: int
    payment_alerts: int
    ibm_positive_alerts: int
    ibm_positive_payments: int
    payment_precision: float
    payment_recall: float
    eligible_patterns: int
    recovered_patterns: int
    investigations: int
    case_snapshots: int
    by_pattern: dict[str, PatternResult]


class Replay(NamedTuple):
    release: dict
    metrics: ReplayMetrics
    cases: pa.Table
    alerts: pa.Table
    evidence_index: pa.Table


def parquet_table(s3, prefix: str, filename: str, checksum: str, rows: int) -> pa.Table:
    raw = read_object(s3, prefix + filename)
    if sha(raw) != checksum:
        raise ValueError(f"ML release artifact changed: {filename}")
    table = pq.read_table(BytesIO(raw))
    if len(table) != rows:
        raise ValueError(f"ML release row count differs for {filename}: expected {rows}, got {len(table)}")
    return table


@st.cache_data(show_spinner=False, max_entries=1)
def load_replay(_s3, pin: str) -> Replay:
    uri, checksum = pin.split()
    _, key = split_uri(uri)
    if not key.startswith("published/ml-replays/") or not key.endswith("/release.json"):
        raise ValueError("Require an immutable published ML release reference")
    release_ref = verify_ref(_s3, {"uri": uri, "sha256": checksum})
    if release_ref["schema_version"] != 1:
        raise ValueError("Unknown ML replay release format")
    release = verify_ref(_s3, release_ref["base_release"])
    prefix = uri.removesuffix("release.json")
    raw_manifest = read_object(_s3, prefix + "manifest.json")
    if sha(raw_manifest) != release_ref["shortlist_sha256"]:
        raise ValueError("ML shortlist manifest changed")
    manifest = json.loads(raw_manifest)
    metrics = verify_ref(_s3, {"uri": prefix + "evaluation.json", "sha256": release_ref["evaluation_sha256"]})
    if (manifest["release_id"] != release["release_id"] or manifest["dataset_version"] != release["dataset_version"]
            or metrics["release_id"] != release["release_id"] or metrics["shortlist_manifest_sha256"] != sha(raw_manifest)
            or metrics["exact_checkpoint_parity"] is not True):
        raise ValueError("The evaluation and shortlist do not match the pinned rules release")
    for field in ("first_date", "last_date", "payment_alerts", "case_snapshots", "investigations"):
        if metrics[field] != manifest[field]:
            raise ValueError(f"Evaluation and shortlist disagree on {field}")
    ranked = manifest["artifacts"]["ranked_cases"]
    alerts = manifest["artifacts"]["payment_alerts"]
    return Replay(release, metrics,
                  parquet_table(_s3, prefix, "ranked_cases.parquet", ranked["sha256"], metrics["case_snapshots"]),
                  parquet_table(_s3, prefix, "payment_alerts.parquet", alerts["sha256"], metrics["payment_alerts"]),
                  parquet_table(_s3, prefix, "evidence_index.parquet", release_ref["evidence_index_sha256"],
                                metrics["case_snapshots"]))


def release_caption(replay: Replay) -> str:
    m = replay.metrics
    return f"Historical replay · {period(m['first_date'], m['last_date'])} · Source release {m['release_id']}"


def replay_evaluation(s3, pin: str) -> None:
    replay = load_replay(s3, pin)
    m = replay.metrics
    with st.container(border=True):
        st.subheader("Full archive ML replay")
        st.caption(release_caption(replay))
        st.markdown(kpis([
            ("Eligible patterns recovered", f"{m['recovered_patterns']:,}/{m['eligible_patterns']:,}", "Searchable shortlist"),
            ("Payment precision", f"{m['payment_precision']:.4%}", "IBM-positive share of unique alerts"),
            ("Payment recall", f"{m['payment_recall']:.4%}", "Share of IBM-positive payments found"),
            ("Distinct payment alerts", f"{m['payment_alerts']:,}", "Counted once per source payment"),
        ]), unsafe_allow_html=True)
        st.caption(f"{m['ibm_positive_alerts']:,} IBM-positive alerts · {m['ibm_positive_payments']:,} IBM-positive "
                   f"payments · {m['payments']:,} payments evaluated")
        st.dataframe(pd.DataFrame([{"Pattern": PATTERNS[k], "Recovered": v["recovered"], "Eligible": v["eligible"]}
                                   for k, v in m["by_pattern"].items()]), hide_index=True, width="stretch")


def highlighted_evidence(s3, case: dict, highlighted: set[str]) -> list[dict]:
    payments = {row["source_id"]: row for row in case["transactions"] if row["source_id"] in highlighted}
    cache = {}
    for part in case.get("evidence_parts", []):
        if payments.keys() == highlighted:
            break
        for line in read_evidence_part(s3, part, cache).splitlines():
            row = json.loads(line)
            if row["source_id"] in highlighted:
                payments[row["source_id"]] = row
    if payments.keys() != highlighted:
        raise ValueError("Some highlighted payments are missing from the original case evidence")
    return sorted(payments.values(), key=lambda row: (row["event_time"], row["source_id"]))


def replay_explorer(s3, pin: str) -> None:
    replay = load_replay(s3, pin)
    m = replay.metrics
    st.caption(release_caption(replay))
    st.caption(f"{m['investigations']:,} ranked investigations · {m['case_snapshots']:,} retained snapshots")
    investigation_tab, payment_tab = st.tabs(["Ranked investigations", "Payment alerts"])
    with investigation_tab:
        pattern = st.selectbox("Pattern family", ["All", *PATTERNS], format_func=lambda x: PATTERNS.get(x, x),
                               key="ml_replay_pattern")
        cases = replay.cases if pattern == "All" else replay.cases.filter(pc.equal(replay.cases["pattern_type"], pattern))
        if not len(cases):
            st.info("No ranked investigations match this pattern.")
        else:
            show_ranked_case(s3, replay, cases)
    with payment_tab:
        show_alerts(replay)


def show_ranked_case(s3, replay: Replay, cases: pa.Table) -> None:
    ranks = pc.unique(cases["archive_rank"]).to_pylist()
    rank = st.selectbox("Investigation rank", ranks, key="ml_replay_rank")
    snapshots = cases.filter(pc.equal(cases["archive_rank"], rank)).to_pylist()
    selection = st.selectbox("Retained snapshot cutoff", list(range(len(snapshots))),
                             format_func=lambda i: snapshots[i]["snapshot_cutoff"].isoformat(),
                             key=f"ml_replay_snapshot_{rank}")
    snapshot = snapshots[selection]
    cutoff = snapshot["snapshot_cutoff"].isoformat()
    index = replay.evidence_index
    match = index.filter(pc.and_(pc.equal(index["case_id"], snapshot["case_id"]),
                                 pc.equal(index["snapshot_cutoff"], cutoff)))
    if len(match) != 1:
        raise ValueError("Ranked case does not resolve to one original snapshot")
    case, raw = get_case(s3, replay.release, match.to_pylist()[0])
    highlighted = set(snapshot["highlighted_source_ids"])
    payments = highlighted_evidence(s3, case, highlighted)
    st.markdown(kpis([
        ("Pattern", PATTERNS[case["pattern_type"]], "Existing published case"),
        ("Accounts", f"{case['participant_count']:,}", "In the original graph"),
        ("Highlighted payments", f"{len(payments):,}", f"Of {case['evidence_transaction_count']:,} evidence payments"),
    ]), unsafe_allow_html=True)
    st.caption(f"Original case {case['case_id'][:16]}… · Snapshot ends {cutoff}")
    clicked = render_graph(case, True, s3, replay.release["release_id"], "ml_replay_edge_" + case["case_id"])
    fields = ["event_time", "sender_account", "receiver_account", "amount_paid", "payment_currency",
              "payment_format", "source_id"]
    st.subheader("Highlighted source payments")
    st.dataframe(pd.DataFrame(payments, columns=fields), hide_index=True, width="stretch")
    if clicked is not None:
        edge = pd.DataFrame(clicked, columns=fields)
        edge["ML highlighted"] = edge["source_id"].isin(highlighted)
        st.subheader("Payments on the selected link")
        st.dataframe(edge, hide_index=True, width="stretch")
    case_id = case["case_id"]
    with st.expander("Original case evidence"):
        st.download_button("Download case manifest", raw, file_name=f"{case_id}.json",
                           mime="application/json", key=f"ml_manifest_{case_id}", on_click="ignore")
        if case.get("evidence_parts"):
            st.download_button("Download complete payments", lambda: full_evidence_archive(s3, case),
                               file_name=f"{case_id}-evidence.zip", mime="application/zip",
                               key=f"ml_evidence_{case_id}", on_click="ignore")


def show_alerts(replay: Replay) -> None:
    first, last = (date.fromisoformat(replay.metrics[key]) for key in ("first_date", "last_date"))
    dates = [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
    day = st.selectbox("Payment date", dates, key="ml_alert_day")
    daily = replay.alerts.filter(pc.equal(replay.alerts["event_date"], day))
    st.caption(f"{len(daily):,} unique payment alerts on this date")
    page = st.number_input("Alert page", min_value=1, max_value=max(1, (len(daily) + 99) // 100),
                           value=1, key=f"ml_alert_page_{day}")
    st.dataframe(daily.slice((page - 1) * 100, 100).to_pandas(), hide_index=True, width="stretch")
