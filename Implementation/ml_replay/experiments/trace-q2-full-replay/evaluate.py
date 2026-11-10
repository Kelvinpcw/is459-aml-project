"""Score every published case with the same AWS evaluation scopes and denominators."""
from collections import Counter, defaultdict
from hashlib import file_digest
from math import ceil
import json
from pathlib import Path
import sys

import numpy as np

from prepare import CASE, KINDS, OBJECTS, PREP, RELEASE, ROOT, SOURCE_COUNT, require, verify_ref
from reference import SCOPES

METHODS = ("baseline", "fan_out_flow", "fan_out_flow_and_history", "fan_in_flow", "fan_in_flow_and_history",
           "cycle_2_value", "cycle_2_value_and_context", "cycles_3_4_order", "cycles_3_4_value", "all_strict_signals")
RESULT = np.dtype([("offset", "<u8"), ("keep", "<u2"), ("signals", "<u2"), ("tier", "u1"), ("path_length", "u1"),
                   ("pad", "<u2"), ("path", "<u4", (4,)), ("context", "<u4"), ("unused", "<u4")])
BUDGET = 50
METRICS = verify_ref(OBJECTS, RELEASE["evaluation"]["metrics"])
assert RESULT.itemsize == 40


def json_write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def window_baseline(scope: str) -> dict:
    if scope == "holdout":
        return METRICS
    field = {"development": "development_report", "sparse_tail": "sparse_tail_report"}[scope]
    return verify_ref(OBJECTS, METRICS[field])


def binary(path: Path, dtype: np.dtype, rows: int) -> np.memmap:
    require(path.stat().st_size == rows * dtype.itemsize, f"Unexpected {path.name} row count")
    return np.memmap(path, dtype=dtype, mode="r", shape=(rows,))


class ReplayFiles:
    def __init__(self, directory: Path):
        n = RELEASE["q2"]["case_count"]
        self.directory = directory
        self.cases = binary(directory / "cases.bin", CASE, n)
        self.scored = binary(directory / "scored.bin", RESULT, n)
        self.case_ids = binary(directory / "case-ids.s64", np.dtype("S64"), n)
        self.evidence = binary(directory / "evidence.u32", np.dtype("<u4"),
                               sum(s["case_evidence_rows_including_case_overlap"] for s in RELEASE["q2"]["snapshots"]))
        self.flags = binary(directory / "flags.u16", np.dtype("<u2"), SOURCE_COUNT + 1)
        self.motifs = binary(directory / "motifs.u8", np.dtype("u1"), SOURCE_COUNT + 1)
        self.days = binary(directory / "days.u8", np.dtype("u1"), SOURCE_COUNT + 1)
        self.degrees = binary(directory / "max-degree.u32", np.dtype("<u4"), SOURCE_COUNT + 1)

    def members(self, row: int) -> np.ndarray:
        first = int(self.scored[row]["offset"])
        return self.evidence[first:first + self.cases[row]["size"]]

    def topology(self, row: int) -> tuple[int, ...]:
        item = self.cases[row]
        kind = int(item["kind"])
        return (kind, *map(int, item["nodes"][:max(1, kind)]))


def scope_view(data: ReplayFiles, name: str) -> tuple[np.ndarray, np.ndarray, list[dict], np.ndarray]:
    start, end = SCOPES[name]
    labels = binary(data.directory / f"labels-{name}.u8", np.dtype("u1"), SOURCE_COUNT + 1)
    refs = json.loads((data.directory / f"references-{name}.json").read_text())
    in_scope = (data.days >= start) & (data.days <= end)
    require(bool(np.all(labels[in_scope] < 2)) and bool(np.all(labels[~in_scope] == 255)),
            f"Labels did not reconcile to {name}")
    rows = np.flatnonzero((data.cases["day"] >= start) & (data.cases["day"] <= end))
    return in_scope, labels, refs, rows


def matching_cases(data: ReplayFiles, refs: list[dict], rows: np.ndarray) -> dict[str, set[int]]:
    by_topology = defaultdict(list)
    for ref in refs:
        by_topology[(ref["kind"], *ref["nodes"])].append(ref)
    possible = {key[1] for key in by_topology}
    candidate_rows = rows[np.isin(data.cases[rows]["nodes"][:, 0], list(possible))]
    matches = {ref["attempt_id"]: set() for ref in refs}
    for row in candidate_rows:
        for ref in by_topology[data.topology(int(row))]:
            seen = int(np.count_nonzero(np.isin(ref["ordinals"], data.members(int(row)))))
            if 5 * seen >= 4 * len(ref["ordinals"]):
                matches[ref["attempt_id"]].add(int(row))
    return matches


def payment_counts(alerted: np.ndarray, positive: np.ndarray, population: int) -> dict:
    return from_counts(int(np.count_nonzero(alerted)), int(np.count_nonzero(alerted & positive)),
                       int(np.count_nonzero(positive)), population)


def from_counts(alerted: int, tp: int, positives: int, population: int) -> dict:
    return {
        "population": population, "positive_labels": positives, "unique_alerted_transactions": alerted,
        "true_positive": tp, "false_positive": alerted - tp, "false_negative": positives - tp,
        "precision": tp / alerted if alerted else None, "recall": tp / positives if positives else None,
    }


def coverage(refs: list[dict], matched: dict[str, set[int]], retains, is_flagged) -> dict:
    eligible = Counter(r["kind"] for r in refs)
    recovered = Counter()
    coverage_any = 0
    for ref in refs:
        kind = ref["kind"]
        if any(retains(row) for row in matched[ref["attempt_id"]]):
            recovered[kind] += 1
        if 5 * int(np.count_nonzero(is_flagged(ref["ordinals"]))) >= 4 * len(ref["ordinals"]):
            coverage_any += 1
    return {"eligible": len(refs), "recovered": sum(recovered.values()),
            "typed_recovery": sum(recovered.values()) / len(refs) if refs else None,
            "type_agnostic_80pct_coverage": coverage_any,
            "by_pattern": {kind: {"eligible": eligible[i], "recovered": recovered[i]}
                           for i, kind in enumerate(KINDS)}}


def compare_baseline(data: ReplayFiles, name: str, scope: np.ndarray, labels: np.ndarray,
                     rows: np.ndarray, result: dict) -> None:
    release = window_baseline(name)
    metrics = release["detector_transaction_metrics"]
    for field in ("population", "positive_labels", "unique_alerted_transactions", "true_positive", "false_positive"):
        require(result[field] == metrics[field], f"{name} baseline {field} differs from AWS")
    require(result["cases"] == release["case_count"], f"{name} baseline case count differs from AWS")
    for key, field in (("eligible", "eligible_attempts"), ("recovered", "recovered_attempts")):
        require(result["coverage"][key] == release["annotation_metrics"][field],
                f"{name} {key} baseline attempts differ from AWS")
    motifs, positive = data.motifs[scope], labels[scope] == 1
    for i, published in enumerate(release["pattern_metrics"]):
        kind = KINDS[i]
        by_kind = result["coverage"]["by_pattern"][kind]
        require(published["pattern_type"] == kind and by_kind == {
            "eligible": published["eligible_annotated_attempts"], "recovered": published["recovered_attempts"]},
                f"{name} baseline {kind} annotation result differs from AWS")
        require(np.count_nonzero(data.cases["kind"][rows] == i) == published["case_count"],
                f"{name} baseline {kind} case count differs from AWS")
        alerted = (motifs & (1 << i)) != 0
        counts = payment_counts(alerted, positive, int(np.count_nonzero(scope)))
        for field in ("unique_alerted_transactions", "true_positive"):
            require(counts[field] == published["transaction_metrics"][field],
                    f"{name} baseline {kind} {field} differs from AWS")


def score_variants(data: ReplayFiles, name: str, scope: np.ndarray, labels: np.ndarray,
                   refs: list[dict], rows: np.ndarray, matched: dict[str, set[int]]) -> dict:
    flags = data.flags[scope]
    pos = labels[scope] == 1
    keeps = data.scored["keep"][rows]
    report = {}
    for i, method in enumerate(METHODS):
        bit = 1 << i
        out = payment_counts((flags & bit) != 0, pos, len(flags))
        out["cases"] = int(np.count_nonzero(keeps & bit))
        out["coverage"] = coverage(refs, matched, lambda row: data.scored[row]["keep"] & bit,
                                   lambda ordinals: data.flags[ordinals] & bit)
        report[method] = out
    compare_baseline(data, name, scope, labels, rows, report["baseline"])
    return report


def tail_sum(values: np.ndarray, largest: int) -> np.ndarray:
    return np.cumsum(np.bincount(values, minlength=largest + 2)[::-1])[::-1]


def calibrate(data: ReplayFiles) -> None:
    scope, labels, refs, rows = scope_view(data, "development")
    matched = matching_cases(data, refs, rows)
    baseline = score_variants(data, "development", scope, labels, refs, rows, matched)["baseline"]
    is_fan = data.cases["kind"][rows] == 1
    fan_degrees = data.cases["degree"][rows][is_fan]
    highest = int(fan_degrees.max())
    through_other = (data.motifs[scope] & 29) != 0
    degree = data.degrees[scope]
    pos = labels[scope] == 1
    only_fan = ~through_other & (degree >= 5)
    extras = tail_sum(degree[only_fan], highest)
    extra_positive = tail_sum(degree[only_fan & pos], highest)
    cases = tail_sum(fan_degrees, highest)
    fan_capacity = [max(int(data.cases[row]["degree"]) for row in matched[ref["attempt_id"]])
                    for ref in refs if ref["kind"] == 1]
    attempts = tail_sum(np.array(fan_capacity), highest)
    fixed = sum(r["kind"] != 1 and bool(matched[r["attempt_id"]]) for r in refs)
    floor = ceil(119 * len(refs) / 122)
    choices = np.flatnonzero(attempts[5:] + fixed >= floor) + 5
    require(len(choices) > 0 and choices[0] == 5, "No development threshold satisfies the fixed floor")
    chosen = int(choices[-1])
    other_payments = int(np.count_nonzero(through_other))
    other_positive = int(np.count_nonzero(through_other & pos))
    positives = int(np.count_nonzero(pos))
    non_fan_cases = int(np.count_nonzero(~is_fan))
    values = sorted({5, 6, 7, 8, 9, 10, 12, 15, 20, chosen, chosen + 1, highest + 1})
    results = {}
    for k in values:
        results[str(k)] = {**from_counts(other_payments + int(extras[k]), other_positive + int(extra_positive[k]),
                                         positives, len(pos)), "cases": non_fan_cases + int(cases[k]),
                           "recovered": fixed + int(attempts[k]), "eligible": len(refs),
                           "fan_out_recovered": int(attempts[k]), "fan_out_eligible": len(fan_capacity)}
    require(results["5"]["unique_alerted_transactions"] == baseline["unique_alerted_transactions"]
            and results["5"]["true_positive"] == baseline["true_positive"]
            and results["5"]["recovered"] == baseline["coverage"]["recovered"],
            "Development threshold 5 did not match published baseline")
    freeze = {
        "release": RELEASE["release_id"], "selection_scope": "2022-09-01 through 2022-09-08",
        "fan_out_only": True, "reference_eligibility_min_counterparties": 5,
        "development_recovery_floor": floor, "development_eligible": len(refs),
        "holdout_recovery_target": 119, "holdout_eligible": 122,
        "highest_degree_considered": highest + 1, "frozen_threshold": chosen,
        "scored_sha256": digest(data.directory / "scored.bin"),
        "rule_code_sha256": digest(ROOT / "replay.cpp"), "development_sweep": results,
    }
    json_write(ROOT / "threshold-freeze.json", freeze)
    print("Frozen fan-out threshold", chosen, "development floor", floor, flush=True)
    for k, m in results.items():
        print("development", k, f"{m['precision']:.6%}", m["recovered"], m["cases"], flush=True)


def chosen_threshold(data: ReplayFiles, scope: np.ndarray, labels: np.ndarray, refs: list[dict],
                     rows: np.ndarray, matches: dict[str, set[int]], k: int) -> dict:
    memberships = ((data.motifs & 29) != 0) | (data.degrees >= k)
    retained = (data.cases["kind"] != 1) | (data.cases["degree"] >= k)
    report = payment_counts(memberships[scope], labels[scope] == 1, int(np.count_nonzero(scope)))
    report["cases"] = int(np.count_nonzero(retained[rows]))
    report["threshold"] = k
    report["coverage"] = coverage(refs, matches, lambda row: retained[row],
                                  lambda ordinals: memberships[ordinals])
    return report


def build_queue(data: ReplayFiles, rows: np.ndarray, order: str, quotas: dict[int, int]) -> dict[int, list[int]]:
    selected = {}
    reviewed = defaultdict(set)
    for day, quota in quotas.items():
        batch = rows[data.cases["day"][rows] == day]
        if order == "signals":
            batch = batch[np.argsort(-data.scored["tier"][batch].astype(np.int8), kind="stable")]
        queue = []
        for row in batch:
            if len(queue) == quota:
                break
            row = int(row)
            members = data.members(row)
            if not np.any(data.days[members] == day):
                continue
            topology = data.topology(row)
            evidence = set(map(int, members))
            if reviewed[topology] & evidence:
                continue
            reviewed[topology].update(evidence)
            queue.append(row)
        selected[day] = queue
    return selected


def review_comparison(data: ReplayFiles, name: str, scope: np.ndarray, labels: np.ndarray,
                      refs: list[dict], rows: np.ndarray, matches: dict[str, set[int]]) -> dict:
    start, end = SCOPES[name]
    cap = dict.fromkeys(range(start, end + 1), BUDGET)
    draft = {key: build_queue(data, rows, key, cap) for key in ("case_id", "signals")}
    quotas = {day: min(len(queues[day]) for queues in draft.values()) for day in cap}
    scores = {}
    for method in draft:
        picked = build_queue(data, rows, method, quotas)
        require(all(len(picked[day]) == quota for day, quota in quotas.items()), "Review budgets did not match")
        cases = {row for items in picked.values() for row in items}
        alerted = np.zeros(SOURCE_COUNT + 1, dtype=bool)
        for row in cases:
            alerted[data.members(row)] = True
        alerted &= scope
        out = payment_counts(alerted[scope], labels[scope] == 1, int(np.count_nonzero(scope)))
        out["cases"] = len(cases)
        out["coverage"] = coverage(refs, matches, lambda row: row in cases, lambda ordinals: alerted[ordinals])
        scores[method] = out
    return {"matched_slots_per_day": quotas, "results": scores}


def all_scopes(data: ReplayFiles) -> None:
    freeze = json.loads((ROOT / "threshold-freeze.json").read_text())
    require(freeze["release"] == RELEASE["release_id"] and freeze["scored_sha256"] == digest(data.directory / "scored.bin")
            and freeze["rule_code_sha256"] == digest(ROOT / "replay.cpp"), "Expected the frozen development run")
    k = freeze["frozen_threshold"]
    summary = {}
    for name in SCOPES:
        scope, labels, refs, rows = scope_view(data, name)
        matched = matching_cases(data, refs, rows)
        variants = score_variants(data, name, scope, labels, refs, rows, matched)
        variants["frozen_fan_out_threshold"] = chosen_threshold(data, scope, labels, refs, rows, matched, k)
        review = review_comparison(data, name, scope, labels, refs, rows, matched)
        base = variants["baseline"]
        for method, result in variants.items():
            precision, recall = result["precision"], result["recall"]
            result["precision_delta_pp"] = 100 * (precision - base["precision"]) if precision is not None else None
            result["recall_delta_pp"] = 100 * (recall - base["recall"]) if recall is not None else None
            result["false_positives_removed"] = base["false_positive"] - result["false_positive"]
            result["coverage_delta_attempts"] = result["coverage"]["recovered"] - base["coverage"]["recovered"]
            shown_precision = f"{precision:.5%}" if precision is not None else "unmeasurable"
            shown_recall = f"{recall:.4%}" if recall is not None else "unmeasurable"
            print(name, method, shown_precision, shown_recall, result["coverage"]["recovered"],
                  result["cases"], flush=True)
        summary[name] = {"case_filters": variants, "review_queues": review}
        for key, result in review["results"].items():
            print(name, "queue", key, result["cases"], result["true_positive"], result["unique_alerted_transactions"],
                  result["coverage"]["recovered"], flush=True)
    local = json.loads((data.directory / "manifest.json").read_text())
    require(sum(r["case_filters"]["baseline"]["population"] for r in summary.values()) == PREP["accepted_rows"],
            "Scoring periods did not exhaust the entire published dataset")
    actual = summary["holdout"]["case_filters"]["frozen_fan_out_threshold"]["coverage"]["recovered"]
    json_write(ROOT / "full-evaluation.json", {"release": RELEASE["release_id"], "input": local,
               "threshold": k, "holdout_119_target_passed": actual >= 119, "scopes": summary})


if __name__ == "__main__":
    data = ReplayFiles(Path(sys.argv[1]).resolve())
    {"calibrate": calibrate, "evaluate": all_scopes}[sys.argv[2]](data)
