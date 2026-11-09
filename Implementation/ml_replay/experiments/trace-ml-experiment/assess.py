"""Evaluate frozen scores on full payment populations and at matched review budgets."""
from collections import defaultdict
from dataclasses import dataclass
from math import ceil
import json
from pathlib import Path
import sys

import numpy as np
from sklearn.metrics import average_precision_score

from input import REPLAY, ROOT, SOURCE_COUNT, require
from model import MODELS, ReleaseFeatures, json_write
from discovery import daily_discovery
from evaluate import ReplayFiles, coverage, matching_cases, window_baseline

PERIODS = {"validation": (6, 8, "development"), "holdout": (9, 16, "holdout"),
           "sparse_tail": (17, 28, "sparse_tail")}
QUEUE_METHODS = ("case_id", "rules", "logistic", "boosted", "mixed_40_10")


@dataclass(frozen=True)
class Scope:
    first: int
    last: int
    ids: np.ndarray
    days: np.ndarray
    positive: np.ndarray
    structural: np.ndarray
    references: list[dict]
    labels: np.ndarray


def load_scope(data: ReplayFiles, name: str) -> Scope:
    start, end, source = PERIODS[name]
    ids = np.flatnonzero((data.days >= start) & (data.days <= end)).astype(np.uint32)
    labels = np.memmap(REPLAY / f"labels-{source}.u8", dtype="u1", mode="r")
    refs = [r for r in json.loads((REPLAY / f"references-{source}.json").read_text())
            if np.all((data.days[r["ordinals"]] >= start) & (data.days[r["ordinals"]] <= end))]
    target = labels[ids]
    require(bool(np.all(target < 2)), f"Incomplete payment labels in {name}")
    return Scope(start, end, ids, data.days[ids], target == 1,
                 (data.motifs[ids] & 31) != 0, refs, labels)


def top_k(values: np.ndarray, count: int) -> np.ndarray:
    result = np.zeros(len(values), dtype=bool)
    if count == 0:
        return result
    if count >= len(values):
        result[:] = True
        return result
    at = len(values) - count
    limit = np.partition(values, at)[at]
    result = values > limit
    needed = count - int(np.count_nonzero(result))
    # Input rows are in ascending source ordinal order for deterministic score ties.
    result[np.flatnonzero(values == limit)[:needed]] = True
    return result


def daily_fraction(values: np.ndarray, scope: Scope, percent: float) -> np.ndarray:
    found = np.zeros(len(values), dtype=bool)
    for day in range(scope.first, scope.last + 1):
        rows = scope.days == day
        found[rows] = top_k(values[rows], ceil(int(np.count_nonzero(rows)) * percent / 100))
    return found


def payment_metrics(scope: Scope, flagged: np.ndarray) -> dict:
    positive = scope.positive
    tp = int(np.count_nonzero(flagged & positive))
    total = int(np.count_nonzero(flagged))
    n_positive = int(np.count_nonzero(positive))
    extra = flagged & ~scope.structural
    coverage_n = 0
    for ref in scope.references:
        positions = np.searchsorted(scope.ids, ref["ordinals"])
        if 5 * int(np.count_nonzero(flagged[positions])) >= 4 * len(positions):
            coverage_n += 1
    return {"alerts": total, "ibm_positive": tp, "ibm_zero": total - tp,
            "missed_ibm_positive": n_positive - tp, "precision": tp / total if total else None,
            "recall": tp / n_positive if n_positive else None,
            "f1": 2 * tp / (total + n_positive) if total + n_positive else None,
            "population_alert_fraction": total / len(flagged),
            "new_ibm_positive_outside_published_q2": int(np.count_nonzero(extra & positive)),
            "new_ibm_zero_outside_published_q2": int(np.count_nonzero(extra & ~positive)),
            "annotation_evidence_80pct_untyped": coverage_n,
            "eligible_annotations": len(scope.references)}


def payment_study(name: str, scope: Scope, scores: dict[str, np.ndarray], freeze: dict) -> dict:
    baseline = payment_metrics(scope, scope.structural)
    report = {"population": len(scope.ids), "positive_population": int(scope.positive.sum()),
              "published_q2": baseline, "models": {}, "options": {}}
    if name != "validation":
        official = window_baseline(name)
        standard = official["detector_transaction_metrics"]
        require((baseline["alerts"], baseline["ibm_positive"]) ==
                (standard["unique_alerted_transactions"], standard["true_positive"]),
                f"Published Q2 did not reconcile for {name}")
        report["published_matched_amount_baseline"] = official["amount_baseline_transaction_metrics"]
    winner = freeze["validation_winner"]
    for model in MODELS:
        values = scores[model][scope.ids]
        require(bool(np.all(np.isfinite(values))), f"Missing scores in {name}")
        thresholds = freeze["model_results"][model]["frozen_validation_targets"]
        model_report = {
            "average_precision": float(average_precision_score(scope.positive, values)),
            "same_alert_count_as_published_q2": payment_metrics(scope, top_k(values, baseline["alerts"])),
            "validation_thresholds": {key: payment_metrics(scope, values >= m["threshold"])
                                      for key, m in thresholds.items()},
        }
        percentiles = freeze["fixed_daily_payment_percentiles"] if model == winner else [1]
        model_report["daily_top_percent"] = {
            str(p): payment_metrics(scope, daily_fraction(values, scope, p)) for p in percentiles}
        report["models"][model] = model_report
        if model != winner:
            continue
        priority = daily_fraction(values, scope, 1)
        report["options"]["q2_union_model_daily_top_1_percent"] = payment_metrics(scope, priority | scope.structural)
        for percent in ("95", "99", "100"):
            use = values >= thresholds[percent]["threshold"]
            report["options"][f"q2_union_frozen_validation_{percent}_recall_threshold"] = payment_metrics(
                scope, use | scope.structural)
        if np.any(scope.positive):
            low = np.min(values[scope.positive])
            missing = scope.positive & ~scope.structural
            report["oracle_diagnostic_min_score_for_all_observed_ibm_positives"] = payment_metrics(scope, values >= low)
            if np.any(missing):
                supplement_floor = np.min(values[missing])
                report["oracle_diagnostic_q2_plus_ml_for_all_observed_ibm_positives"] = payment_metrics(
                    scope, scope.structural | (values >= supplement_floor))
    return report


def aggregate_case_scores(data: ReplayFiles, scores: dict[str, np.ndarray], winner: str) -> tuple[np.ndarray, dict]:
    last_payment_day = np.zeros(len(data.cases), dtype=np.uint8)
    families = {"logistic": scores[MODELS[0]], "boosted": scores[MODELS[2]], "winner": scores[winner]}
    ranking = {key: np.full(len(data.cases), -np.inf, dtype=np.float32) for key in families}
    for start in range(0, len(data.cases), 20_000):
        stop = min(start + 20_000, len(data.cases))
        desc = data.cases[start:stop]
        begin = int(data.scored[start]["offset"])
        end = int(data.scored[stop-1]["offset"]) + int(desc[-1]["size"])
        offsets = (data.scored["offset"][start:stop] - begin).astype(np.int64)
        members = data.evidence[begin:end]
        fact_days = data.days[members]
        last_payment_day[start:stop] = np.maximum.reduceat(fact_days, offsets)
        current = fact_days == np.repeat(desc["day"], desc["size"].astype(np.int64))
        for key, scores_by_ordinal in families.items():
            ranking[key][start:stop] = np.maximum.reduceat(
                np.where(current, scores_by_ordinal[members], -np.inf), offsets)
    return last_payment_day, ranking


def preceding_episodes(data: ReplayFiles, last_day: np.ndarray, cutoff: int) -> dict[tuple[int, ...], int]:
    max_day = defaultdict(int)
    rows = np.flatnonzero(data.cases["day"] <= cutoff)
    for row in rows:
        topology = data.topology(int(row))
        observed = int(last_day[row])
        if observed > max_day[topology]:
            max_day[topology] = observed
    return dict(max_day)


def filtered_candidates(data: ReplayFiles, scope: Scope, last_day: np.ndarray,
                        exclude_earlier: dict[tuple[int, ...], int]) -> dict[int, np.ndarray]:
    days = data.cases["day"]
    rows = {}
    for day in range(scope.first, scope.last + 1):
        # Fresh evidence means there is a reason to act at today's cutoff.
        eligible = np.flatnonzero((days == day) & (last_day == day))
        if exclude_earlier:
            beginning = max(1, day - 6)
            eligible = np.asarray([row for row in eligible
                                   if exclude_earlier.get(data.topology(int(row)), 0) < beginning], dtype=np.int64)
        rows[day] = eligible
    return rows


def ordered(rows: np.ndarray, scores: np.ndarray) -> np.ndarray:
    # Published case IDs are already in ascending order within a cutoff.
    return rows[np.argsort(-scores[rows].astype(np.float32), kind="stable")]


def take(data: ReplayFiles, ordered_rows: np.ndarray, count: int, day: int,
         seen: dict[tuple[int, ...], int]) -> list[int]:
    picked = []
    beginning = max(1, day - 6)
    for row in ordered_rows:
        if len(picked) == count:
            break
        row = int(row)
        shape = data.topology(row)
        if seen.get(shape, 0) >= beginning:
            continue
        seen[shape] = day
        picked.append(row)
    return picked


def ranked_day(data: ReplayFiles, rows: np.ndarray, quota: int, day: int, rank: dict,
               method: str, seen: dict[tuple[int, ...], int]) -> tuple[list[int], list[int]]:
    if method == "case_id":
        return take(data, rows, quota, day, seen), []
    if method != "mixed_40_10":
        scores = data.scored["tier"] if method == "rules" else rank[method]
        return take(data, ordered(rows, scores), quota, day, seen), []
    main = ordered(rows, rank["winner"])
    reserve = quota // 5
    main_rows = take(data, main, quota-reserve, day, seen)
    # The discovery lane gets strong rule-supported cases beyond the model's raw
    # top 50 today. Remaining places return to the model.
    elsewhere = rows[(data.scored["tier"][rows] >= 2) & ~np.isin(rows, main[:50])]
    novel = take(data, ordered(elsewhere, data.scored["tier"]), reserve, day, seen)
    return main_rows + novel + take(data, main, quota-len(main_rows)-len(novel), day, seen), novel


def case_metrics(data: ReplayFiles, scope: Scope, picked: dict[int, list[int]],
                 matches: dict[str, set[int]], discovery: list[int]) -> dict:
    chosen = {row for batch in picked.values() for row in batch}
    evidence = np.zeros(SOURCE_COUNT + 1, dtype=bool)
    for row in chosen:
        evidence[data.members(row)] = True
    amounts = payment_metrics(scope, evidence[scope.ids])
    eligible = (data.days >= scope.first) & (data.days <= scope.last)
    evidence &= eligible
    typed = coverage(scope.references, matches, lambda row: row in chosen, lambda ids: evidence[ids])
    contextual = [data.members(row) for row in discovery]
    supplemental = np.unique(np.concatenate(contextual)) if contextual else np.array([], dtype=np.uint32)
    supplemental = supplemental[eligible[supplemental]]
    return {
        "cases_reviewed": len(chosen), "scope_evidence": amounts,
        "all_evidence_rows_including_repeats_and_history": sum(int(data.cases[row]["size"]) for row in chosen),
        "typed_pattern_coverage": typed, "daily_cases": {day: len(batch) for day, batch in picked.items()},
        "discovery_lane_cases": len(discovery),
        "discovery_lane_distinct_ibm_positive_payments": int(np.count_nonzero(scope.labels[supplemental] == 1)),
        "discovery_lane_distinct_ibm_zero_payments": int(np.count_nonzero(scope.labels[supplemental] == 0)),
    }


def queue_study(data: ReplayFiles, scope: Scope, candidates: dict[int, np.ndarray], rank: dict) -> dict:
    rows = np.flatnonzero((data.cases["day"] >= scope.first) & (data.cases["day"] <= scope.last))
    matches = matching_cases(data, scope.references, rows)
    shared = {}
    seen = {method: {} for method in QUEUE_METHODS}
    queues = {method: {} for method in QUEUE_METHODS}
    discovery = {method: [] for method in QUEUE_METHODS}
    for day, eligible in candidates.items():
        quota = min(len(ranked_day(data, eligible, 50, day, rank, m, seen[m].copy())[0])
                    for m in QUEUE_METHODS)
        shared[day] = quota
        for method in QUEUE_METHODS:
            picked, extra = ranked_day(data, eligible, quota, day, rank, method, seen[method])
            require(len(picked) == quota, "Case review workload did not match")
            queues[method][day] = picked
            discovery[method].extend(extra)
    report = {method: case_metrics(data, scope, queues[method], matches, discovery[method])
              for method in QUEUE_METHODS}
    return {"candidate_snapshots_with_fresh_evidence": sum(map(len, candidates.values())),
            "matched_daily_slots": shared, "results": report}



def discovery_study(features: ReleaseFeatures, scope: Scope, model: np.ndarray) -> dict:
    methods = ("model", "relay", "mixed")
    picked = {name: [] for name in methods}
    inventory = []
    for day in range(scope.first, scope.last + 1):
        result = daily_discovery(features, model, day)
        for name in methods:
            picked[name].append(getattr(result, name))
        inventory.append({"day": day, "outside_day_end_q2": result.eligible,
                          "relay_supported": result.supported_relay,
                          **{name + "_slots": len(getattr(result, name)) for name in methods}})
    outcomes = {}
    for name in methods:
        selected = np.concatenate(picked[name])
        # The model and mixed lists use the same workload. The relay-only list
        # reports its actual size when fewer than 50 payments meet the rule.
        flag = np.zeros(len(scope.ids), dtype=bool)
        flag[np.searchsorted(scope.ids, selected)] = True
        outcomes[name] = payment_metrics(scope, flag)
    return {"scope": "Up to 50 payments per day outside the graph at that day's cutoff",
            "relay": "Non-self payment with a same-currency receipt or onward transfer within 60 minutes, and min/max amount >=0.8",
            "mixed": "40 model + up to 10 relay payments outside the raw model shortlist, unused slots returned to model",
            "daily": inventory, "results": outcomes}


def main(work: Path) -> None:
    freeze = json.loads((ROOT / "model-freeze.json").read_text())
    require(freeze["model_results"][MODELS[0]].get("optimizer_converged") is True,
            "Finish logistic optimization and freeze it before opening holdout labels")
    data = ReplayFiles(REPLAY)
    features = ReleaseFeatures(work)
    scores = {name: np.memmap(work / f"{name}.scores.f32", dtype="<f4", mode="r", shape=(SOURCE_COUNT+1,))
              for name in MODELS}
    last_day, rank = aggregate_case_scores(data, scores, freeze["validation_winner"])
    report = {"release": freeze["release"], "total_payments_scored_per_model": SOURCE_COUNT,
              "candidate_case_snapshots_scored": len(data.cases), "validation_winner": freeze["validation_winner"],
              "scopes": {}}
    for name in PERIODS:
        scope = load_scope(data, name)
        earlier = preceding_episodes(data, last_day, 5) if name == "validation" else {}
        candidates = filtered_candidates(data, scope, last_day, earlier)
        study = payment_study(name, scope, scores, freeze)
        queues = queue_study(data, scope, candidates, rank)
        supplementary = discovery_study(features, scope, scores[freeze["validation_winner"]])
        report["scopes"][name] = {"payments": study, "case_queues": queues,
                                  "outside_q2_discovery": supplementary}
        if name == "holdout":
            unseen = filtered_candidates(data, scope, last_day, preceding_episodes(data, last_day, 8))
            report["scopes"][name]["new_episode_case_queues"] = queue_study(data, scope, unseen, rank)
        for model, row in study["models"].items():
            top = row["daily_top_percent"]["1"]
            print(name, model, "AP", f"{row['average_precision']:.4%}", "top1%", top["ibm_positive"],
                  top["alerts"], flush=True)
        for m, outcome in queues["results"].items():
            print(name, "case queue", m, outcome["cases_reviewed"], outcome["scope_evidence"]["ibm_positive"],
                  outcome["scope_evidence"]["alerts"], outcome["typed_pattern_coverage"]["recovered"], flush=True)
    json_write(ROOT / "ml-results.json", report)


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
