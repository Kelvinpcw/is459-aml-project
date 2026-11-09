"""Test case evidence progress and a queue that can review older available snapshots."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import sys

import numpy as np
from joblib import dump, load
from threadpoolctl import threadpool_limits

from case_rank import (
    CAP, N, OUTPUT, PRIOR, REPLAY, CaseFacts, ReplayFiles, Scope, Version, coverage, development,
    digest, features, fit_tree, load_scope, matching_cases, payment_metrics, payment_peers, shortlist,
    total_queue, write,
)

FEATURES = ("fan_in", "fan_out", "cycle_2", "cycle_3", "cycle_4", "core_size_log", "core_peers_log",
            "core_fraction", "core_ach_share", "core_ach_peer_share", "core_same_currency_share",
            "core_dominant_currency_share", "core_dominant_currency_amount_median",
            "core_dominant_currency_amount_iqr", "core_time_span_log", "core_active_days",
            "core_latest_day_share", "core_days_since_latest_payment", "snapshot_count_log",
            "observed_core_peers_log", "core_new_evidence_share", "core_change_since_prior",
            "core_payments_seen_so_far_log", "mean_core_relative_to_peak_size",
            "days_since_first_version")
METHODS = ("case_backlog", "case_backlog_with_risk", "progress_today", "progress_backlog",
           "progress_blend", "progress_blend_by_type", "progress_blend_new_evidence")
BUDGETS = (50, 100, 150, 250, 500)


@dataclass(frozen=True)
class Review:
    review_day: int
    case: Version


def progress_features(data: ReplayFiles, facts: CaseFacts, versions: dict[int, list[Version]]) -> tuple[np.ndarray, list[Version]]:
    rows = [version for day in sorted(versions) for version in versions[day]]
    x = np.empty((len(rows), len(FEATURES)), dtype=np.float32)
    history: dict[int, tuple[int, int, set[int], set[int], int]] = {}
    for i, v in enumerate(rows):
        ids = v.ordinals
        seen_today = set(map(int, ids))
        seen = history.get(v.episode)
        if seen:
            first, version_count, prior_union, prior_latest, peak = seen
        else:
            first, version_count, prior_union, prior_latest, peak = v.day, 0, set(), set(), 0
        peers = payment_peers(facts.links, ids, v.kind)
        active_days = data.days[ids]
        if np.any(active_days > v.day):
            raise ValueError("Progress features include a future payment")
        ach = facts.links.ach[ids]
        codes = facts.currency[ids]
        names, counts = np.unique(codes, return_counts=True)
        cohort = codes == names[counts.argmax()]
        lower, median, upper = np.quantile(facts.paid[ids[cohort]], [0.25, 0.5, 0.75])
        now_count = len(ids)
        all_seen = prior_union | seen_today
        peak = max(peak, now_count)
        x[i] = (
            *(v.kind == j for j in range(5)),
            np.log1p(now_count), np.log1p(len(np.unique(peers))), now_count / int(data.cases[v.row]["size"]),
            ach.mean(), len(np.unique(peers[ach]))/len(np.unique(peers)), facts.same_currency[ids].mean(),
            cohort.mean(), median, upper-lower, np.log1p(np.ptp(facts.links.minute[ids])),
            len(np.unique(active_days)), (active_days == v.day).mean(), v.day-int(active_days.max()),
            np.log1p(version_count+1),
            np.log1p(len(np.unique(payment_peers(facts.links, np.asarray(sorted(all_seen), dtype=np.uint32), v.kind)))),
            len(seen_today-prior_union)/now_count, len(seen_today-prior_latest)/now_count,
            np.log1p(len(all_seen)), now_count/peak, v.day-first,
        )
        history[v.episode] = (first, version_count+1, all_seen, seen_today, peak)
    return x, rows


def train_progress(data: ReplayFiles, scope: Scope, matrix: np.ndarray, candidates: list[Version]) -> tuple[object, dict]:
    early = [i for i, v in enumerate(candidates) if v.day <= 6]
    refs = [ref for ref in scope.references if int(max(data.days[ref["ordinals"]])) <= 6]
    by_shape = defaultdict(list)
    for ref in refs:
        by_shape[(ref["kind"], *ref["nodes"])].append(np.asarray(ref["ordinals"], dtype=np.uint32))
    complete, controls = np.zeros((2, len(early)), dtype=bool)
    row_indices = np.empty(len(early), dtype=np.int64)
    for j, i in enumerate(early):
        v = candidates[i]
        row_indices[j] = v.row
        options = by_shape[data.topology(v.row)]
        count = [int(np.count_nonzero(np.isin(ids, v.ordinals))) for ids in options]
        complete[j] = any(5*n >= 4*len(ids) for n, ids in zip(count, options, strict=True))
        # For the completion task, partial versions of a known attempt make useful controls.
        partial = any(count) and not complete[j]
        controls[j] = partial or not np.any(scope.labels[v.ordinals] == 1)
    if complete.sum() < 20:
        raise ValueError("Not enough completed early examples to learn case progress")
    return fit_tree(matrix[early], complete, controls, data, row_indices), {
        "positive_snapshot_rows": int(complete.sum()), "controls": int(controls.sum()),
        "training_cases": len(early), "training_days": [1, 6], "training_reference_attempts": len(refs),
        "feature_order": list(FEATURES),
    }


def review(data: ReplayFiles, candidates: list[Version], case_strength: dict[int, float],
           progress: dict[int, float], method: str, first: int, last: int, cap: int) -> list[Review]:
    by_day = defaultdict(list)
    for v in candidates:
        if first <= v.day <= last:
            by_day[v.day].append(v)
    prior_evidence = defaultdict(set)
    reviewed_any = set()
    pending: dict[int, dict[frozenset[int], Version]] = defaultdict(dict)
    output = []
    for day in range(first, last+1):
        if method == "progress_today":
            pending.clear()
        for v in by_day[day]:
            evidence = frozenset(map(int, v.ordinals))
            if not evidence.difference(prior_evidence[v.episode]):
                continue
            versions = pending[v.episode]
            # An available later superset can stand in for an unreviewed subset.
            # Exact duplicate evidence keeps its earliest source snapshot.
            if any(evidence <= older for older in versions):
                continue
            for old in [old for old in versions if old < evidence]:
                del versions[old]
            versions[evidence] = v
        options = []
        for episode, versions in pending.items():
            potential = []
            for evidence, version in versions.items():
                novel = evidence.difference(prior_evidence[episode])
                if not novel:
                    continue
                case = case_strength[version.row]
                full = progress[version.row]
                signal = case if method.startswith("case_backlog") else full
                if method.startswith("progress_blend"):
                    signal = 0.5*case + 0.5*full
                if method == "case_backlog_with_risk":
                    signal += 0.6*np.log1p(version.consensus) + 0.2*np.log1p(len(novel))
                if method == "progress_blend_new_evidence":
                    new_share = len(novel-reviewed_any)/len(evidence)
                    signal += 0.4*np.log1p(len(novel)) + 0.5*np.log(0.2+0.8*new_share)
                # Prefer a fresh version when scores are identical.
                potential.append((float(signal), version.day, version.row, version, novel))
            if potential:
                options.append(max(potential, key=lambda item: (item[0], item[1], -item[2])))
        options.sort(key=lambda item: (-item[0], -item[1], item[2]))
        selected = []
        if method == "progress_blend_by_type":
            for kind in range(5):
                selected.extend([item for item in options if item[3].kind == kind][:cap//10])
        used = {item[2] for item in selected}
        selected.extend([item for item in options if item[2] not in used][:cap-len(selected)])
        for _, available, _, version, novel in selected:
            if available > day:
                raise ValueError("Review queue used a snapshot before its cutoff")
            prior_evidence[version.episode].update(novel)
            reviewed_any.update(novel)
            output.append(Review(day, version))
    return output


def evaluate(data: ReplayFiles, scope: Scope, refs: list[dict], matches: dict, active: np.ndarray,
             reviews: list[Review], first: int, last: int, cap: int) -> dict:
    rows = np.zeros(len(data.cases), dtype=bool)
    flag = np.zeros(N, dtype=bool)
    counts = dict.fromkeys(range(first, last+1), 0)
    report = []
    for item in reviews:
        v = item.case
        if not first <= v.day <= item.review_day <= last or np.any(active[v.ordinals] > v.day):
            raise ValueError("Review evidence falls outside the as-of snapshot")
        rows[v.row] = True
        flag[v.ordinals] = True
        counts[item.review_day] += 1
        report.append({"day": item.review_day, "snapshot_day": v.day, "episode": v.episode,
                       "case_id": data.case_ids[v.row].decode("ascii"), "payment_ordinals": list(map(int, v.ordinals))})
    if max(counts.values()) > cap:
        raise ValueError("Daily capacity exceeded")
    return {**payment_metrics(scope, flag), "review_slots": len(reviews), "daily_slots": counts,
            "typed": coverage(data, refs, matches, rows, active, "shape"), "reviews": report}


def run(data: ReplayFiles, facts: CaseFacts, scope: Scope, versions: dict[int, list[Version]],
        matrix: np.ndarray, candidates: list[Version], active: np.ndarray, progress_model: object,
        first: int, last: int, refs: list[dict], method_names: tuple[str, ...], cap: int) -> dict:
    possible = np.asarray([v.row for v in candidates if first <= v.day <= last], dtype=np.int64)
    matches = matching_cases(data, refs, possible)
    case_model = load(OUTPUT / "case-models.joblib")["pointwise"]
    p_case = case_model.predict_proba(features(data, facts, possible))[:, 1]
    p_progress = progress_model.predict_proba(matrix)[:, 1]
    case_strength = dict(zip(map(int, possible), np.log(np.maximum(1e-6, p_case)), strict=True))
    completion = {v.row: float(np.log(max(1e-6, p))) for v, p in zip(candidates, p_progress, strict=True)}
    out = {}
    for method in method_names:
        if method == "old_novelty":
            daily = total_queue(versions, "novelty", cap, first, last)
            reviews = [Review(day, v) for day, vs in daily.items() for v in vs]
        else:
            reviews = review(data, candidates, case_strength, completion, method, first, last, cap)
        out[method] = evaluate(data, scope, refs, matches, active, reviews, first, last, cap)
        p = out[method]
        print("Case queue", first, last, "budget", cap, method, "patterns", p["typed"]["recovered"],
              "reviews", p["review_slots"], "payments", p["alerts"], "positives", p["ibm_positive"], flush=True)
    return out


def main() -> None:
    data, facts = ReplayFiles(REPLAY / "work"), CaseFacts.read()
    policy = json.loads((PRIOR / "hybrid-freeze.json").read_text())["case_policy"]
    command = sys.argv[1]
    scope = development(data) if command == "freeze" else load_scope(data, "holdout")
    _, active, versions = shortlist(data, facts.links, scope, policy)
    x, candidates = progress_features(data, facts, versions)
    with threadpool_limits(limits=4):
        model_file = OUTPUT / "progress-model.joblib"
        if command == "freeze":
            model, fit = train_progress(data, scope, x, candidates)
            refs = [r for r in scope.references if int(max(data.days[r["ordinals"]])) >= 7]
            metrics = run(data, facts, scope, versions, x, candidates, active, model, 7, 8, refs,
                          ("old_novelty", *METHODS), CAP)
            winner = max(metrics, key=lambda k: (metrics[k]["typed"]["recovered"], metrics[k]["ibm_positive"],
                                                -metrics[k]["alerts"]))
            dump(model, model_file)
            write(OUTPUT / "backlog-validation.json", metrics)
            write(OUTPUT / "backlog-freeze.json", {
                **fit, "selected": winner, "validation_days": [7, 8], "source_sha256": digest(Path(__file__)),
                "model_sha256": digest(model_file), "case_model_sha256": digest(OUTPUT / "case-models.joblib")})
        else:
            freeze = json.loads((OUTPUT / "backlog-freeze.json").read_text())
            expected = (digest(Path(__file__)), digest(model_file), digest(OUTPUT / "case-models.joblib"))
            if expected != (freeze["source_sha256"], freeze["model_sha256"], freeze["case_model_sha256"]):
                raise ValueError("Case progress ranker changed after development")
            model = load(model_file)
            report = run(data, facts, scope, versions, x, candidates, active, model, scope.first, scope.last,
                         scope.references, ("old_novelty", *METHODS), CAP)
            write(OUTPUT / "backlog-holdout.json", report)
            winner = freeze["selected"]
            curve = {str(CAP): report[winner]}
            for cap in BUDGETS[1:]:
                result = run(data, facts, scope, versions, x, candidates, active, model, scope.first, scope.last,
                             scope.references, (winner,), cap)
                curve[str(cap)] = result[winner]
            for result in curve.values():
                result.pop("reviews")
            write(OUTPUT / "backlog-budget-curve.json", curve)


if __name__ == "__main__":
    main()
