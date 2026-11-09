"""Build the frozen full-month shortlist without reading any evaluation inputs."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys

from joblib import load
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from threadpoolctl import threadpool_limits

from archive_algorithms import (CaseGroup, Policy, Version, anchored_case_retro, archive,
                                case_versions, complete_case, day_groups, distance_to_alert,
                                features, progress_features, shape_survives, top_k)
from score_payments import sha256 as file_hash

KINDS = ("fan_in", "fan_out", "cycle_2", "cycle_3", "cycle_4")
CASE = np.dtype([("kind", "u1"), ("day", "u1"), ("pad", "<u2"), ("size", "<u4"),
                 ("degree", "<u4"), ("nodes", "<u4", (4,))])
FACT = np.dtype([("paid", "<u8", (2,)), ("received", "<u8", (2,)), ("id", "<u4"), ("sender", "<u4"),
                 ("receiver", "<u4"), ("minute", "<u4"), ("paid_currency", "<u2"),
                 ("received_currency", "<u2"), ("pad", "<u4")])
RESULT = np.dtype({"names": ["offset", "signals"], "formats": ["<u8", "<u2"], "offsets": [0, 10], "itemsize": 40})


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def binary(path: Path, dtype: np.dtype, rows: int) -> np.memmap:
    require(path.stat().st_size == rows * dtype.itemsize, f"Unexpected byte size for {path}")
    return np.memmap(path, dtype=dtype, mode="r", shape=(rows,))


@dataclass(frozen=True)
class Window:
    first: int
    last: int


@dataclass(frozen=True)
class Facts:
    sender: np.ndarray
    receiver: np.ndarray
    minute: np.ndarray
    ach: np.ndarray


@dataclass(frozen=True)
class CaseFacts:
    links: Facts
    paid: np.ndarray
    currency: np.ndarray
    same_currency: np.ndarray
    same_bank: np.ndarray
    cents: np.ndarray


@dataclass(frozen=True)
class ReplayFiles:
    cases: np.ndarray
    scored: np.ndarray
    case_ids: np.ndarray
    evidence: np.ndarray
    days: np.ndarray

    def members(self, row: int) -> np.ndarray:
        start = int(self.scored[row]["offset"])
        return self.evidence[start:start + int(self.cases[row]["size"])]

    def topology(self, row: int) -> tuple[int, ...]:
        case = self.cases[row]
        kind = int(case["kind"])
        return (kind, *map(int, case["nodes"][:max(1, kind)]))


@dataclass(frozen=True)
class Settings:
    release_id: str
    dataset_version: str
    first_date: date
    last_date: date
    source_sha256: str
    seed_percent: float
    support_percent: float
    minimum_seeds: int
    rejoin_cutoff: float
    transfer: Policy
    archive_limit: int
    standalone_cutoff: float


def read_facts(root: Path, aux: Path, payments: int, accounts: int) -> CaseFacts:
    records = binary(root / "facts.bin", FACT, payments)
    bank = binary(aux / "banks.u32", np.dtype("<u4"), accounts)
    formats = binary(aux / "formats.u8", np.dtype("u1"), payments + 1)
    codes = json.loads((aux / "input.json").read_text())["format_codes"]
    sender, receiver = np.zeros((2, payments + 1), dtype=np.uint32)
    minute = np.zeros(payments + 1, dtype=np.int32)
    paid = np.zeros(payments + 1, dtype=np.float64)
    currency, same_currency, same_bank, cents = np.zeros((4, payments + 1), dtype=np.uint8)
    for start in range(0, payments, 300_000):
        part = records[start:start + 300_000]
        ids, words = part["id"], part["paid"]
        sender[ids], receiver[ids], minute[ids] = part["sender"], part["receiver"], part["minute"]
        paid[ids] = np.log1p((words[:, 1].astype(np.float64) * 2**64 + words[:, 0]) / 1e8)
        currency[ids] = part["paid_currency"]
        same_currency[ids] = part["paid_currency"] == part["received_currency"]
        same_bank[ids] = bank[part["sender"]] == bank[part["receiver"]]
        cents[ids] = ((words[:, 1] % 100_000_000) * (2**64 % 100_000_000) +
                      words[:, 0] % 100_000_000) % 100_000_000 == 0
    ach = formats == codes["ACH"]
    ach[0] = False
    return CaseFacts(Facts(sender, receiver, minute, ach), paid, currency, same_currency, same_bank, cents)


def within_cutoff(group: CaseGroup, activation: np.ndarray) -> np.ndarray:
    seen = activation[group.members]
    return (seen != 0) & (seen <= group.day)


def seed_cases(data: ReplayFiles, facts: Facts, groups: list[CaseGroup], graph: np.ndarray,
               settings: Settings) -> np.ndarray:
    seeds = np.zeros(len(data.days), dtype=np.uint8)
    support = np.zeros(len(data.days), dtype=bool)
    for day in range(1, (settings.last_date - settings.first_date).days + 2):
        ids = np.flatnonzero(data.days == day)
        seeds[ids[top_k(graph[ids], ceil(len(ids) * (settings.seed_percent / 100)))]] = day
        support[ids[top_k(graph[ids], ceil(len(ids) * (settings.support_percent / 100)))]] = True
    active = anchored_case_retro(groups, seeds, support, settings.minimum_seeds)
    first_seen = np.full(len(data.days), 255, dtype=np.uint8)
    for group in groups:
        allowed = within_cutoff(group, active)
        retained = shape_survives(facts, group, allowed)
        np.minimum.at(first_seen, group.members[np.repeat(retained, group.sizes) & allowed], group.day)
    return first_seen


def supporting_payments(facts: Facts, groups: list[CaseGroup], alerts: np.ndarray,
                        scores: np.ndarray, policy: Policy) -> np.ndarray:
    offers = np.full(len(alerts), 255, dtype=np.uint8)
    for group in groups:
        already = alerts[group.members] <= group.day
        needed = np.where(group.kind < 2, 5, group.kind)
        enough = np.add.reduceat(already, group.offsets, dtype=np.int32) >= np.maximum(1, needed - policy.max_missing_legs)
        has_new = np.logical_or.reduceat(~already & (scores[group.members] >= policy.score_floor), group.offsets)
        for index in np.flatnonzero(enough & has_new):
            span = slice(group.offsets[index], group.offsets[index] + group.sizes[index])
            ids, picked = group.members[span], already[span]
            peers = facts.receiver[ids] if group.kind[index] == 1 else facts.sender[ids]
            minutes = facts.minute[ids]
            gap = distance_to_alert(minutes, minutes[picked])
            extra = complete_case(ids, peers, picked, gap, scores[ids], int(needed[index]), policy)
            np.minimum.at(offers, extra, group.day)
    return offers


def shortlist(data: ReplayFiles, facts: CaseFacts, graph: np.ndarray, risk: np.ndarray,
              transfer: np.ndarray, settings: Settings) -> dict[int, list[Version]]:
    days = (settings.last_date - settings.first_date).days + 1
    groups = day_groups(data, Window(1, days))
    seed_day = seed_cases(data, facts.links, groups, graph, settings)
    starting = np.minimum(np.where(risk >= settings.rejoin_cutoff, data.days, 255), seed_day)
    offers = supporting_payments(facts.links, groups, starting, transfer, settings.transfer)
    activation = np.minimum(starting, offers)
    flagged = np.zeros(len(data.cases), dtype=bool)
    for group in groups:
        flagged[group.begin:group.end] = shape_survives(facts.links, group, within_cutoff(group, activation))
    print(f"Retained {int(flagged.sum()):,} snapshots after completing the directed shapes", flush=True)
    return case_versions(data, facts.links, flagged, activation, risk)


def save_table(table: pa.Table, path: Path) -> dict:
    pq.write_table(table, path, compression="zstd")
    require(table.equals(pq.read_table(path)), f"Parquet readback differs for {path.name}")
    return {"file": path.name, "rows": len(table), "sha256": file_hash(path)}


def snapshot_cutoff(first: date, day: int) -> datetime:
    return datetime.combine(first + timedelta(days=day), time.min)


def export(data: ReplayFiles, facts: CaseFacts, versions: dict[int, list[Version]], risk: np.ndarray,
           shape_model: Path, progress_model: Path, settings: Settings, destination: Path) -> dict:
    matrix, rows = progress_features(data, facts, versions)
    shape = load(shape_model)["pointwise"]
    progress = load(progress_model)
    with threadpool_limits(limits=4):
        shape_score = shape.predict_proba(features(data, facts, np.asarray([v.row for v in rows], dtype=np.int64)))[:, 1]
        progress_score = progress.predict_proba(matrix)[:, 1]
    score = (shape_score + progress_score) / 2
    file_count = max(v.episode for v in rows) + 1
    file_score = np.zeros(file_count, dtype=np.float64)
    np.maximum.at(file_score, [v.episode for v in rows], score)
    file_order = np.argsort(-file_score, kind="stable")[:settings.archive_limit]
    _, maximal = archive(versions)
    grouped: dict[int, list[Version]] = defaultdict(list)
    for batch in maximal.values():
        for version in batch:
            grouped[version.episode].append(version)
    scores_by_row = {v.row: float(value) for v, value in zip(rows, score, strict=True)}
    selected = []
    evidence_mask = np.zeros(len(risk), dtype=bool)
    case_prefix = settings.source_sha256 + ":"
    for rank, episode in enumerate(file_order, 1):
        snapshots = grouped[int(episode)]
        first_case_id = data.case_ids[min(v.row for v in snapshots)].decode("ascii")
        investigation = sha256(f"{settings.release_id}:{first_case_id}".encode()).hexdigest()
        for v in sorted(snapshots, key=lambda item: (item.day, item.row)):
            ids = np.sort(v.ordinals)
            require(bool(np.all(data.days[ids] <= v.day)), "Selected evidence includes future payments")
            evidence_mask[ids] = True
            selected.append({"case_id": data.case_ids[v.row].decode("ascii"), "case_row": v.row,
                             "investigation_id": investigation, "archive_rank": rank,
                             "snapshot_cutoff": snapshot_cutoff(settings.first_date, v.day), "pattern_type": KINDS[v.kind],
                             "case_score": scores_by_row[v.row], "investigation_score": float(file_score[episode]),
                             "highlighted_ordinals": [int(i) for i in ids],
                             "highlighted_source_ids": [f"{case_prefix}{i}" for i in ids]})
    standalone = risk >= np.float32(settings.standalone_cutoff)
    alerts = np.flatnonzero(evidence_mask | standalone)
    require(bool(len(alerts) and alerts[0] > 0), "Shortlist includes an invalid source ID")
    payments = pa.table({"source_id": [f"{case_prefix}{i}" for i in alerts], "source_record_ordinal": alerts,
                         "event_date": [settings.first_date + timedelta(days=int(data.days[i]) - 1) for i in alerts],
                         "blended_score": risk[alerts], "standalone_alert": standalone[alerts],
                         "case_evidence": evidence_mask[alerts]})
    cases_ref = save_table(pa.Table.from_pylist(selected), destination / "ranked_cases.parquet")
    payments_ref = save_table(payments, destination / "payment_alerts.parquet")
    print(f"Exported {len(file_order):,} investigations, {len(selected):,} snapshots and {len(alerts):,} payments",
          flush=True)
    return {"release_id": settings.release_id, "dataset_version": settings.dataset_version,
            "first_date": settings.first_date.isoformat(), "last_date": settings.last_date.isoformat(),
            "candidate_investigations": file_count, "candidate_snapshots": len(rows),
            "investigations": len(file_order), "case_snapshots": len(selected), "payment_alerts": len(alerts),
            "artifacts": {"ranked_cases": cases_ref, "payment_alerts": payments_ref}}


def main(arguments: list[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", required=True, type=Path)
    parser.add_argument("--input-check", required=True, type=Path)
    parser.add_argument("--formats", required=True, type=Path)
    parser.add_argument("--graph-scores", required=True, type=Path)
    parser.add_argument("--history-scores", required=True, type=Path)
    parser.add_argument("--transfer-scores", required=True, type=Path)
    parser.add_argument("--case-model", required=True, type=Path)
    parser.add_argument("--evidence-model", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args(arguments)
    raw = json.loads(args.policy.read_text())
    source = json.loads(args.input_check.read_text())
    settings = Settings(raw["release_id"], raw["dataset_version"], date.fromisoformat(raw["first_date"]),
                        date.fromisoformat(raw["last_date"]), raw["source_sha256"], raw["seed_percent"],
                        raw["support_percent"], raw["minimum_seeds"], raw["rejoin_cutoff"],
                        Policy(**raw["transfer"]), raw["archive_limit"], raw["standalone_cutoff"])
    require((source["release_id"], source["dataset_version"]) == (settings.release_id, settings.dataset_version),
            "Policy and staged release identities differ")
    for name, path in (("case_shape", args.case_model), ("evidence_progress", args.evidence_model),
                       ("graph_scores", args.graph_scores), ("history_scores", args.history_scores),
                       ("transfer_scores", args.transfer_scores)):
        require(file_hash(path) == raw["artifact_hashes"][name], f"Frozen {name} differs from the replay policy")
    args.destination.mkdir(mode=0o700)
    payments, cases = source["facts"], source["case_rows"]
    data = ReplayFiles(binary(args.replay / "cases.bin", CASE, cases), binary(args.replay / "scored.bin", RESULT, cases),
                       binary(args.replay / "case-ids.s64", np.dtype("S64"), cases),
                       binary(args.replay / "evidence.u32", np.dtype("<u4"), source["evidence_memberships"]),
                       binary(args.replay / "days.u8", np.dtype("u1"), payments + 1))
    facts = read_facts(args.replay, args.formats, payments, source["accounts"])
    graph, history, transfer = (binary(p, np.dtype("<f4"), payments + 1)
                                for p in (args.graph_scores, args.history_scores, args.transfer_scores))
    risk = (graph + history) / 2
    versions = shortlist(data, facts, graph, risk, transfer, settings)
    report = export(data, facts, versions, risk, args.case_model, args.evidence_model, settings, args.destination)
    report["policy_sha256"] = file_hash(args.policy)
    report["input_check_sha256"] = file_hash(args.input_check)
    (args.destination / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
