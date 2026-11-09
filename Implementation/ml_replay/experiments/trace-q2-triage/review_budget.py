"""Compare a matched total review budget and larger case-opening budgets."""
from __future__ import annotations

from pathlib import Path
import json

import numpy as np

from benchmark import (
    N, REPLAY, ROOT, Facts, ReplayFiles, anchored_case_retro, coverage, dates_for,
    day_groups, digest, fraction, get_scores, load_scope, matching_cases, payment_metrics,
    project, ranked, write,
)
from hybrid import MODEL, SHARES, Version, queue_result, case_versions

TOTAL_REVIEWS_PER_DAY = 50
EXTRA_OPENING_CAPS = (500, 1000)
METHODS = ("consensus", "novelty", "novelty_by_type", "most_new_evidence", "floor")


def total_queue(versions: dict[int, list[Version]], method: str, cap: int,
                first: int, last: int) -> dict[int, list[Version]]:
    past: dict[int, set[int]] = {}
    output = {}
    for day in range(first, last+1):
        available = []
        for item in versions.get(day, []):
            new = set(map(int, item.ordinals)) - past.get(item.episode, set())
            if not new:
                continue
            freshness = len(new) / len(item.ordinals)
            priority = item.consensus
            if method.startswith("novelty"):
                priority *= 0.35 + 0.65*freshness
            elif method == "most_new_evidence":
                priority *= np.log1p(len(new))
            elif method == "floor":
                priority = item.floor
            available.append((priority, item.row, item, new))
        available.sort(key=lambda v: (-v[0], v[1]))
        chosen = []
        if method == "novelty_by_type":
            for kind, quota in enumerate(SHARES):
                chosen.extend([a for a in available if a[2].kind == kind][:quota*cap//50])
        already = {a[1] for a in chosen}
        chosen.extend([a for a in available if a[1] not in already][:cap-len(chosen)])
        for _, _, item, new in chosen:
            past.setdefault(item.episode, set()).update(new)
        output[day] = [a[2] for a in chosen]
    return output


def summarize(data: ReplayFiles, part: str, facts: Facts, policy: dict) -> dict:
    scope = load_scope(data, part)
    scores = get_scores(MODEL)
    ranks = ranked(scope, scores)
    seeds = dates_for(scope, fraction(scope, ranks, policy["percent"]))
    weak = np.zeros(N, dtype=bool)
    weak[scope.ids[fraction(scope, ranks, policy["lower_percent"])]] = True
    groups = day_groups(data, scope)
    activated = anchored_case_retro(groups, seeds, weak, policy["minimum_seeds"])
    projection = project(data, facts, groups, activated, 1, "shape")
    versions = case_versions(data, facts, projection.retained, activated, scores)
    rows = np.flatnonzero((data.cases["day"] >= scope.first) & (data.cases["day"] <= scope.last))
    matches = matching_cases(data, scope.references, rows)
    report = {}
    for name in METHODS:
        selected = total_queue(versions, name, TOTAL_REVIEWS_PER_DAY, scope.first, scope.last)
        reviewed = np.zeros(len(data.cases), dtype=bool)
        flagged = np.zeros(N, dtype=bool)
        for day in selected:
            for item in selected[day]:
                reviewed[item.row] = True
                flagged[item.ordinals] = True
        report[name] = {**payment_metrics(scope, flagged), "review_slots": int(np.count_nonzero(reviewed)),
                        "slots_by_day": {day: len(values) for day, values in selected.items()},
                        "typed": coverage(data, scope.references, matches, reviewed, activated, "shape")}
        x = report[name]
        print(part, name, x["review_slots"], x["typed"]["recovered"], x["alerts"],
              x["ibm_positive"], flush=True)
    higher = {}
    for cap in EXTRA_OPENING_CAPS:
        higher[str(cap)] = {
            name: queue_result(data, scope, versions, matches, activated, name, cap)
            for name in ("peer_consensus", "consensus_by_type")}
        print(part, "new openings cap", cap,
              [(name, r["typed"]["recovered"], r["case_openings"], r["additional_versions"])
               for name, r in higher[str(cap)].items()], flush=True)
    return {"total_review_budget": report, "opening_budgets_plus_updates": higher}


def main() -> None:
    config = json.loads((ROOT / "hybrid-freeze.json").read_text())
    data, facts = ReplayFiles(REPLAY / "work"), Facts.read()
    validation = summarize(data, "validation", facts, config["case_policy"])
    choice = max(METHODS, key=lambda name: (validation["total_review_budget"][name]["typed"]["recovered"],
                                            validation["total_review_budget"][name]["f1"]))
    write(ROOT / "review-budget-freeze.json",
          {"file_sha256": digest(Path(__file__)), "validated_choice": choice, "validation": validation})
    for part in ("holdout", "sparse_tail"):
        write(ROOT / f"{part}-review-budget.json", summarize(data, part, facts, config["case_policy"]))


if __name__ == "__main__":
    main()
