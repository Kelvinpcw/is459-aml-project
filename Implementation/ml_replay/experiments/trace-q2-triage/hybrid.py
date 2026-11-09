"""Combine a small shape-preserving case pool with an independent payment screen."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import json
import sys

import numpy as np

from benchmark import (
    N, ROOT, REPLAY, Facts, ReplayFiles, Scope, anchored_case_retro, coverage,
    dates_for, day_groups, digest, fraction, get_scores, load_scope, matching_cases,
    payment_metrics, project, ranked, scores_path, write,
)

MODEL = "boosted_context"
BASELINE_MARGIN = 0.05
FRACTIONS = (0.25, 0.5, 1.0, 2.0, 3.0)
CAPS = (50, 100, 250)
SHARES = (17, 10, 15, 5, 3)
RANKS = ("weakest_leg", "strongest_peer", "peer_consensus", "consensus_by_type")


@dataclass(frozen=True)
class Version:
    row: int
    episode: int
    day: int
    kind: int
    ordinals: np.ndarray
    floor: float
    strongest: float
    consensus: float


def freeze() -> dict:
    validation = json.loads((ROOT / "validation-results.json").read_text())
    previous = json.loads((ROOT / "policy-freeze.json").read_text())
    case_policy = previous["validation_choice_by_family"]["same_case"]["selected"]
    case = validation[case_policy]
    baseline = validation["published_q2"]
    choices = [validation[f"{MODEL}_{pct:g}pct"] for pct in FRACTIONS]
    qualifying = [item for item in choices if item["recall"] >= baseline["recall"] + BASELINE_MARGIN]
    if not qualifying or case["typed"]["recovered"] != case["typed"]["eligible"]:
        raise ValueError("Validation constraints for the two lanes were not met")
    selected = min(qualifying, key=lambda item: item["alerts"])
    config = {
        "case_policy": case["policy"],
        "direct_payment_policy": selected["policy"],
        "validation_days": [6, 8],
        "validation_recall_baseline": baseline["recall"],
        "validation_recall_direct": selected["recall"],
        "validation_recall_improvement_floor": BASELINE_MARGIN,
        "previous_experiments_exposed_the_holdout": True,
        "frozen_score_sha256": digest(scores_path(MODEL)),
        "source_sha256": digest(Path(__file__)),
        "benchmark_sha256": digest(ROOT / "benchmark.py"),
    }
    write(ROOT / "hybrid-freeze.json", config)
    print("Hybrid chosen from development figures", case_policy, selected["policy"]["name"], flush=True)
    return config


def case_versions(data: ReplayFiles, facts: Facts, accepted: np.ndarray, activated: np.ndarray,
                  probabilities: np.ndarray) -> dict[int, list[Version]]:
    previous = {}
    versions = defaultdict(list)
    next_id = 0
    for index in np.flatnonzero(accepted):
        row = int(index)
        item = data.cases[row]
        day, kind = int(item["day"]), int(item["kind"])
        original = data.members(row)
        when = activated[original]
        chosen = original[(when > 0) & (when <= day)]
        key = data.topology(row)
        seen = previous.get(key)
        if seen and day-seen.day <= 6 and np.any(np.isin(chosen, seen.ordinals)):
            episode = seen.episode
        else:
            episode = next_id
            next_id += 1
        peer = facts.receiver[chosen] if kind == 1 else facts.sender[chosen]
        names, indices = np.unique(peer, return_inverse=True)
        peaks = np.zeros(len(names), dtype=np.float32)
        np.maximum.at(peaks, indices, probabilities[chosen])
        needed = 5 if kind < 2 else kind
        if len(peaks) < needed:
            raise ValueError("Retained case has incomplete structure")
        core = np.sort(peaks)[-needed:]
        weakest = float(core[0])
        strongest = float(core[-1])
        consensus = float(np.mean(core)) * (1 + 0.2 * (len(core)-2))
        version = Version(row, episode, day, kind, chosen, weakest, strongest, consensus)
        previous[key] = version
        versions[day].append(version)
    return dict(versions)


def episode_queue(versions: dict[int, list[Version]], method: str, cap: int,
                  first: int, last: int) -> tuple[list[Version], dict[int, int], dict[int, int]]:
    opened = set()
    reviewed = []
    openings, updates = {}, {}
    for day in range(first, last+1):
        daily = versions.get(day, [])
        fresh = [v for v in daily if v.episode not in opened]
        ongoing = [v for v in daily if v.episode in opened]
        if method == "weakest_leg":
            order = sorted(fresh, key=lambda v: (-v.floor, -v.consensus, v.row))
        elif method == "strongest_peer":
            order = sorted(fresh, key=lambda v: (-v.strongest, -v.consensus, v.row))
        else:
            order = sorted(fresh, key=lambda v: (-v.consensus, -v.floor, v.row))
        chosen = []
        if method == "consensus_by_type":
            for kind, slots in enumerate(SHARES):
                chosen.extend([v for v in order if v.kind == kind][:cap*slots//50])
        picked_today = {v.episode for v in chosen}
        chosen.extend([v for v in order if v.episode not in picked_today][:cap-len(chosen)])
        opened.update(v.episode for v in chosen)
        openings[day] = len(chosen)
        updates[day] = len(ongoing)
        reviewed.extend(ongoing)
        reviewed.extend(chosen)
    return reviewed, openings, updates


def queue_result(data: ReplayFiles, scope: Scope, versions: dict[int, list[Version]],
                 matches: dict[str, set[int]], activated: np.ndarray, method: str, cap: int) -> dict:
    reviewed, opened, updates = episode_queue(versions, method, cap, scope.first, scope.last)
    reviewed_rows = np.zeros(len(data.cases), dtype=bool)
    seen = np.zeros(N, dtype=bool)
    for version in reviewed:
        reviewed_rows[version.row] = True
        seen[version.ordinals] = True
    result = payment_metrics(scope, seen)
    result.update(case_openings=sum(opened.values()), case_openings_by_day=opened,
                  additional_versions=sum(updates.values()), version_updates_by_day=updates,
                  typed=coverage(data, scope.references, matches, reviewed_rows, activated, "shape"))
    return result


def run(data: ReplayFiles, facts: Facts, config: dict, phase: str) -> dict:
    scope = load_scope(data, phase)
    groups = day_groups(data, scope)
    score = get_scores(MODEL)
    rank = ranked(scope, score)
    case = config["case_policy"]
    seeds = dates_for(scope, fraction(scope, rank, case["percent"]))
    weak = np.zeros(N, dtype=bool)
    weak[scope.ids[fraction(scope, rank, case["lower_percent"])]] = True
    activated = anchored_case_retro(groups, seeds, weak, case["minimum_seeds"])
    projection = project(data, facts, groups, activated, 1, "shape")
    direct = fraction(scope, rank, config["direct_payment_policy"]["percent"])
    union = projection.linked.copy()
    union[scope.ids[direct]] = True
    rows = np.flatnonzero((data.cases["day"] >= scope.first) & (data.cases["day"] <= scope.last))
    matches = matching_cases(data, scope.references, rows)
    typed = coverage(data, scope.references, matches, projection.retained, activated, "shape")
    pools = case_versions(data, facts, projection.retained, activated, score)
    queue = {str(cap): {name: queue_result(data, scope, pools, matches, activated, name, cap)
                        for name in RANKS} for cap in CAPS}
    report = {
        "case_lane": payment_metrics(scope, projection.linked),
        "case_snapshots": int(np.count_nonzero(projection.retained)),
        "case_episodes": len({v.episode for versions in pools.values() for v in versions}),
        "context_payments_in_case_lane": int(np.count_nonzero(projection.context[scope.ids])),
        "typed": typed, "direct_lane": payment_metrics(scope, dates_for(scope, direct) != 0),
        "combined": payment_metrics(scope, union),
        "combined_separate_payment_alerts": int(np.count_nonzero(~projection.linked[scope.ids] & direct)),
        "combined_positive_outside_published_q2": int(np.count_nonzero(union[scope.ids] & ~scope.structural & scope.positive)),
        "case_episode_queue": queue,
    }
    print(phase, report["case_snapshots"], report["case_episodes"], typed["recovered"],
          report["combined"]["alerts"], report["combined"]["ibm_positive"], flush=True)
    for cap, values in queue.items():
        print(phase, cap, [(name, d["case_openings"], d["typed"]["recovered"], d["alerts"])
                           for name, d in values.items()], flush=True)
    return report


def main() -> None:
    config = freeze()
    data = ReplayFiles(REPLAY / "work")
    facts = Facts.read()
    for phase in ("validation", "holdout", "sparse_tail"):
        write(ROOT / f"{phase}-hybrid.json", run(data, facts, config, phase))


if __name__ == "__main__":
    main()
