"""Train a second-stage case ranker and test it at the same daily review budget."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import sys

import numpy as np
from joblib import dump, load
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

OUTPUT = Path(__file__).resolve().parent
PRIOR = OUTPUT.parent / "trace-q2-triage"
sys.path.insert(0, str(PRIOR))
from benchmark import (
    N, ML, REPLAY, Facts, ReplayFiles, Scope, anchored_case_retro, binary, coverage,
    dates_for, day_groups, digest, fraction, get_scores, load_scope, matching_cases,
    payment_metrics, project, ranked, write,
)
from hybrid import Version, case_versions
from prepare import FACT, SOURCE_COUNT
from evaluate import scope_view
from review_budget import total_queue

SEED = 459
CAP = 50
TRAIN_END = 6
VALIDATION_FIRST = 7
VALIDATION_END = 8
SAMPLE_PER_TYPE = 12_000
FEATURES = (
    "motif_fan_in", "motif_fan_out", "motif_cycle_2", "motif_cycle_3", "motif_cycle_4",
    "payments_log", "peers_log", "transfers_per_peer_log",
    "ach_fraction", "ach_peers_share", "cross_bank_fraction", "same_currency_fraction",
    "dominant_currency_fraction", "dominant_currency_ach_peers_fraction", "currency_count_log",
    "dominant_currency_log_amount_median", "dominant_currency_log_amount_iqr",
    "dominant_currency_exact_amount_repeat_fraction", "dominant_currency_cent_amount_fraction",
    "dominant_currency_largest_bucket_fraction", "minutes_span_log", "unique_payment_minutes_fraction",
    "active_days", "same_day_share", "age_since_last_payment_log", "max_daily_payment_share",
    "max_daily_peer_share", "past_days_one_peer_fraction", "payments_without_same_peer_same_day",
    "signal_burst", "signal_related_flow", "signal_history", "signal_unusual_fan",
    "signal_ordered_cycle", "signal_value_continuity", "signal_unusual_pair", "signal_wider_flow",
)
METHODS = ("pointwise", "pairwise", "payment_shape", "pointwise_with_risk", "pairwise_with_risk",
           "pointwise_balanced", "payment_shape_balanced", "pointwise_novelty", "payment_shape_novelty")


@dataclass(frozen=True)
class CaseFacts:
    links: Facts
    paid: np.ndarray
    currency: np.ndarray
    same_currency: np.ndarray
    same_bank: np.ndarray
    cents: np.ndarray

    @classmethod
    def read(cls) -> CaseFacts:
        links = Facts.read()
        records = binary(REPLAY / "work" / "facts.bin", FACT, SOURCE_COUNT)
        banks = binary(ML / "work" / "banks.u32", np.dtype("<u4"), 2_077_023)
        paid = np.zeros(N, dtype=np.float64)
        currency, same_currency, same_bank, cents = np.zeros((4, N), dtype=np.uint8)
        for start in range(0, len(records), 300_000):
            part = records[start:start+300_000]
            idx = part["id"]
            words = part["paid"]
            amount = words[:, 1].astype(np.float64) * 2**64 + words[:, 0]
            paid[idx] = np.log1p(amount / 1e8)
            currency[idx] = part["paid_currency"]
            same_currency[idx] = part["paid_currency"] == part["received_currency"]
            same_bank[idx] = banks[part["sender"]] == banks[part["receiver"]]
            # Work with exact scaled integers when checking for round amounts.
            cents[idx] = ((words[:, 1] % 100_000_000) * (2**64 % 100_000_000) +
                          words[:, 0] % 100_000_000) % 100_000_000 == 0
        return cls(links, paid, currency, same_currency, same_bank, cents)


def payment_peers(facts: Facts, members: np.ndarray, kind: int) -> np.ndarray:
    return facts.receiver[members] if kind == 1 else facts.sender[members]


def features(data: ReplayFiles, facts: CaseFacts, rows: np.ndarray) -> np.ndarray:
    matrix = np.empty((len(rows), len(FEATURES)), dtype=np.float32)
    for pos, raw in enumerate(rows):
        row = int(raw)
        case = data.cases[row]
        kind, day = int(case["kind"]), int(case["day"])
        members = data.members(row)
        peers, peer_index, peer_counts = np.unique(payment_peers(facts.links, members, kind),
                                                    return_inverse=True, return_counts=True)
        minutes = facts.links.minute[members]
        member_days = data.days[members]
        if not len(members) or np.any(member_days > day):
            raise ValueError("Case evidence exceeded its snapshot")
        days, day_index, day_counts = np.unique(member_days, return_inverse=True, return_counts=True)
        ach = facts.links.ach[members]
        ccy = facts.currency[members]
        codes, currency_counts = np.unique(ccy, return_counts=True)
        ccy_main = ccy == codes[np.argmax(currency_counts)]
        values = facts.paid[members[ccy_main]]
        lower, median, upper = np.quantile(values, [0.25, 0.5, 0.75])
        _, repeated_amount = np.unique(values, return_counts=True)
        distinct_daily_peers, daily_peer_counts = np.unique(
            np.unique((day_index.astype(np.uint64) << np.uint64(32)) | peer_index.astype(np.uint64)) >>
            np.uint64(32), return_counts=True)
        per_peer_day = np.unique((peer_index.astype(np.uint64) << np.uint64(8)) |
                                 day_index.astype(np.uint64), return_counts=True)[1]
        signals = int(data.scored[row]["signals"])
        length = len(members)
        matrix[pos] = (
            *(float(kind == k) for k in range(5)), np.log1p(length), np.log1p(len(peers)),
            np.log1p(length/len(peers)), ach.mean(), len(np.unique(peer_index[ach]))/len(peers),
            facts.same_bank[members].mean() * -1 + 1, facts.same_currency[members].mean(),
            ccy_main.mean(), len(np.unique(peer_index[ccy_main & ach]))/len(peers), np.log1p(len(codes)),
            median, upper-lower, (repeated_amount.max()-1)/len(values),
            facts.cents[members[ccy_main]].mean(), np.bincount(
                np.minimum(np.floor(values).astype(np.int32), 50)).max()/len(values),
            np.log1p(int(np.ptp(minutes))), len(np.unique(minutes))/length, len(days),
            np.count_nonzero(member_days == day)/length, np.log1p(day*1440-1-int(minutes.max())),
            day_counts.max()/length, daily_peer_counts.max()/len(peers),
            np.count_nonzero(daily_peer_counts == 1)/len(distinct_daily_peers),
            np.count_nonzero(per_peer_day == 1)/length,
            *(float(bool(signals & (1 << k))) for k in range(8)),
        )
    return matrix


def development(data: ReplayFiles) -> Scope:
    mask, labels, refs, _ = scope_view(data, "development")
    ids = np.flatnonzero(mask).astype(np.uint32)
    return Scope(1, 8, ids, data.days[ids], labels[ids] == 1, (data.motifs[ids] & 31) != 0, refs, labels)


def shortlist(data: ReplayFiles, facts: Facts, scope: Scope, policy: dict) -> tuple[np.ndarray, np.ndarray, dict[int, list[Version]]]:
    scores = get_scores(policy["model"])
    ranks = ranked(scope, scores)
    seeds = dates_for(scope, fraction(scope, ranks, policy["percent"]))
    weak = np.zeros(N, dtype=bool)
    weak[scope.ids[fraction(scope, ranks, policy["lower_percent"])]] = True
    groups = day_groups(data, scope)
    activated = anchored_case_retro(groups, seeds, weak, policy["minimum_seeds"])
    retained = project(data, facts, groups, activated, 1, "shape").retained
    return retained, activated, case_versions(data, facts, retained, activated, scores)


def sample_training(data: ReplayFiles, facts: Facts, scope: Scope, retained: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    rng = np.random.default_rng(SEED)
    train = np.flatnonzero((data.cases["day"] >= 1) & (data.cases["day"] <= TRAIN_END))
    refs = [ref for ref in scope.references if max(data.days[ref["ordinals"]]) <= TRAIN_END]
    mapping = matching_cases(data, refs, train)
    anchors = np.array(sorted(set().union(*mapping.values())), dtype=np.int64)
    annotated_topologies = {(r["kind"], *r["nodes"]) for r in refs}
    sampled = [anchors, train[retained[train]]]
    for kind in range(5):
        pool = train[data.cases["kind"][train] == kind]
        count = min(len(pool), SAMPLE_PER_TYPE)
        sampled.append(rng.choice(pool, count, replace=False))
    rows = np.unique(np.concatenate(sampled))
    matches = np.isin(rows, anchors)
    clean = np.zeros(len(rows), dtype=bool)
    labelled_shape = np.zeros(len(rows), dtype=bool)
    for pos, item in enumerate(rows):
        row = int(item)
        kind = int(data.cases[row]["kind"])
        members = data.members(row)
        known = scope.labels[members] == 1
        clean[pos] = not np.any(known) and data.topology(row) not in annotated_topologies
        if np.count_nonzero(known) * 2 >= len(members):
            labelled_peers = payment_peers(facts, members[known], kind)
            labelled_shape[pos] = len(np.unique(labelled_peers)) >= (5 if kind < 2 else kind)
    if len(refs) < 30 or np.count_nonzero(matches) < 30 or np.count_nonzero(clean) < 500:
        raise ValueError("Insufficient early development case support")
    details = {"train_days": [1, TRAIN_END], "eligible_train_attempts": len(refs),
               "matching_training_snapshots": int(matches.sum()), "strictly_ibm_zero_cases": int(clean.sum()),
               "positive_shape_training_snapshots": int(labelled_shape.sum()), "sampled_training_cases": len(rows)}
    return rows, matches, clean, labelled_shape, details


def fit_tree(matrix: np.ndarray, target: np.ndarray, negative: np.ndarray,
             data: ReplayFiles, rows: np.ndarray) -> HistGradientBoostingClassifier:
    keep = target | negative
    counts = Counter(data.topology(int(row)) for row in rows[target])
    weights = np.ones(len(rows), dtype=np.float64)
    weights[target] = [1/np.sqrt(counts[data.topology(int(row))]) for row in rows[target]]
    weights[target] *= np.count_nonzero(negative) / (4*weights[target].sum())
    estimator = HistGradientBoostingClassifier(
        max_iter=85, learning_rate=0.065, max_leaf_nodes=12, max_depth=4, min_samples_leaf=12,
        l2_regularization=4.0, early_stopping=False, random_state=SEED)
    estimator.fit(matrix[keep], target[keep], sample_weight=weights[keep])
    return estimator


def fit_pairs(matrix: np.ndarray, target: np.ndarray, negative: np.ndarray,
              kinds: np.ndarray, days: np.ndarray) -> tuple[StandardScaler, LogisticRegression]:
    rng = np.random.default_rng(SEED)
    scaler = StandardScaler().fit(matrix)
    scaled = scaler.transform(matrix)
    examples = []
    for pos in np.flatnonzero(target):
        pool = np.flatnonzero(negative & (kinds == kinds[pos]) & (days == days[pos]))
        if len(pool) == 0:
            raise ValueError("No same-day, same-motif case controls")
        controls = rng.choice(pool, min(96, len(pool)), replace=False)
        examples.append(scaled[pos] - scaled[controls])
    delta = np.concatenate(examples)
    x = np.vstack((delta, -delta))
    y = np.repeat([1, 0], len(delta))
    model = LogisticRegression(C=0.08, fit_intercept=False, max_iter=200, random_state=SEED)
    model.fit(x, y)
    return scaler, model


def model_scores(features_by_row: np.ndarray, estimators: dict) -> dict[str, np.ndarray]:
    pair_scaler, pair_model = estimators["pairwise"]
    return {
        "pointwise": estimators["pointwise"].predict_proba(features_by_row)[:, 1],
        "payment_shape": estimators["payment_shape"].predict_proba(features_by_row)[:, 1],
        "pairwise": pair_model.decision_function(pair_scaler.transform(features_by_row)),
    }


def queue(versions: dict[int, list[Version]], signals: dict[int, float], method: str,
          first: int, last: int, cap: int) -> dict[int, list[Version]]:
    reviewed: dict[int, set[int]] = {}
    output = {}
    for day in range(first, last+1):
        candidates = []
        for version in versions.get(day, []):
            novel = set(map(int, version.ordinals)) - reviewed.get(version.episode, set())
            if not novel:
                continue
            strength = signals[version.row]
            if method.endswith("_with_risk"):
                strength += 0.6*np.log1p(version.consensus) + 0.2*np.log1p(len(novel))
            if method.endswith("_novelty"):
                strength += 0.5*np.log(0.35+0.65*len(novel)/len(version.ordinals))
            candidates.append((float(strength), version, novel))
        candidates.sort(key=lambda v: (-v[0], v[1].row))
        chosen = []
        if method.endswith("_balanced"):
            # A small floor for each motif prevents one large family taking the whole queue.
            floor = cap//10
            for kind in range(5):
                chosen.extend([c for c in candidates if c[1].kind == kind][:floor])
        used = {item[1].row for item in chosen}
        chosen.extend([c for c in candidates if c[1].row not in used][:cap-len(chosen)])
        for _, version, novel in chosen:
            reviewed.setdefault(version.episode, set()).update(novel)
        output[day] = [c[1] for c in chosen]
    return output


def summary(data: ReplayFiles, scope: Scope, mapping: dict, activated: np.ndarray,
            refs: list[dict], selected: dict[int, list[Version]]) -> dict:
    rows = np.zeros(len(data.cases), dtype=bool)
    ids = np.zeros(N, dtype=bool)
    snapshots = []
    for day, versions in selected.items():
        for rank, version in enumerate(versions, start=1):
            if day != version.day or np.any(activated[version.ordinals] > day):
                raise ValueError("Future transfers entered a review queue")
            rows[version.row] = True
            ids[version.ordinals] = True
            snapshots.append({"day": day, "position": rank, "episode": version.episode,
                              "case_id": data.case_ids[version.row].decode("ascii"),
                              "payment_ordinals": list(map(int, version.ordinals))})
    return {**payment_metrics(scope, ids), "review_slots": sum(map(len, selected.values())),
            "reviews_by_day": {d: len(v) for d, v in selected.items()},
            "typed": coverage(data, refs, mapping, rows, activated, "shape"), "snapshots": snapshots}


def archive(versions: dict[int, list[Version]]) -> tuple[dict[int, list[Version]], dict[int, list[Version]]]:
    """Retain earliest identical evidence and find maximal sets for completed archives."""
    seen = set()
    unique = defaultdict(list)
    by_episode = defaultdict(list)
    for day, batch in versions.items():
        for version in batch:
            ids = frozenset(map(int, version.ordinals))
            key = version.episode, ids
            if key in seen:
                continue
            seen.add(key)
            unique[day].append(version)
            by_episode[version.episode].append((version, ids))
    maximum = defaultdict(list)
    for batch in by_episode.values():
        for version, ids in batch:
            if not any(ids < other_ids for _, other_ids in batch):
                maximum[version.day].append(version)
    return dict(unique), dict(maximum)


def assess(data: ReplayFiles, facts: CaseFacts, scope: Scope, settings: dict, estimators: dict,
           first: int, last: int, refs: list[dict], part: str) -> dict:
    _, activated, all_versions = shortlist(data, facts.links, scope, settings)
    versions = {day: batch for day, batch in all_versions.items() if first <= day <= last}
    rows = np.asarray([v.row for group in versions.values() for v in group], dtype=np.int64)
    mapping = matching_cases(data, refs, rows)
    model_values = model_scores(features(data, facts, rows), estimators)
    names = {k: dict(zip(map(int, rows), v, strict=True)) for k, v in model_values.items()}
    out = {}
    for method in ("old_novelty", *METHODS):
        if method == "old_novelty":
            chosen = total_queue(versions, "novelty", CAP, first, last)
        else:
            base = next(k for k in names if method.startswith(k))
            chosen = queue(versions, names[base], method, first, last, CAP)
        result = summary(data, scope, mapping, activated, refs, chosen)
        out[method] = result
        print(part, method, result["typed"]["recovered"], "/", result["typed"]["eligible"],
              "payments", result["alerts"], "positives", result["ibm_positive"], flush=True)
    unique, maximal = archive(versions)
    evidence = {name: summary(data, scope, mapping, activated, refs, cases) for name, cases in
                (("all", versions), ("exact_dedup", unique), ("maximal_archive", maximal))}
    for candidate in evidence.values():
        candidate.pop("snapshots")
    if any(evidence["all"]["alerts"] != v["alerts"] or
           evidence["all"]["typed"]["recovered"] != v["typed"]["recovered"] for v in evidence.values()):
        raise ValueError("Archiving dropped payment evidence or typed coverage")
    return {"review_budget_per_day": CAP, "queues": out, "archive": evidence}


def main() -> None:
    data = ReplayFiles(REPLAY / "work")
    facts = CaseFacts.read()
    policy = json.loads((PRIOR / "hybrid-freeze.json").read_text())["case_policy"]
    with threadpool_limits(limits=5):
        if sys.argv[1] == "freeze":
            scope = development(data)
            retained, _, _ = shortlist(data, facts.links, scope, policy)
            rows, target, negative, labelled_shape, meta = sample_training(data, facts.links, scope, retained)
            print("Case ranker fit population", meta, flush=True)
            x = features(data, facts, rows)
            estimators = {"pointwise": fit_tree(x, target, negative, data, rows),
                          "payment_shape": fit_tree(x, labelled_shape, negative, data, rows),
                          "pairwise": fit_pairs(x, target, negative, data.cases["kind"][rows], data.cases["day"][rows])}
            dev_refs = [r for r in scope.references if max(data.days[r["ordinals"]]) >= VALIDATION_FIRST]
            validation = assess(data, facts, scope, policy, estimators, VALIDATION_FIRST, VALIDATION_END,
                                dev_refs, "development_validation")
            ranking = max(validation["queues"], key=lambda k: (validation["queues"][k]["typed"]["recovered"],
                                                              validation["queues"][k]["ibm_positive"],
                                                              -validation["queues"][k]["alerts"]))
            dump(estimators, OUTPUT / "case-models.joblib")
            write(OUTPUT / "case-validation.json", validation)
            write(OUTPUT / "case-freeze.json", {**meta, "validation_days": [VALIDATION_FIRST, VALIDATION_END],
                    "eligible_validation_attempts": len(dev_refs), "chosen_queue": ranking, "features": list(FEATURES),
                    "source_sha256": digest(Path(__file__)), "model_sha256": digest(OUTPUT / "case-models.joblib")})
        else:
            freeze = json.loads((OUTPUT / "case-freeze.json").read_text())
            if freeze["source_sha256"] != digest(Path(__file__)) or freeze["model_sha256"] != digest(OUTPUT / "case-models.joblib"):
                raise ValueError("Case ranker changed after calibration")
            scope = load_scope(data, "holdout")
            result = assess(data, facts, scope, policy, load(OUTPUT / "case-models.joblib"),
                            scope.first, scope.last, scope.references, "holdout")
            if result["archive"]["all"]["typed"]["recovered"] != 122:
                raise ValueError("Expected verified case shortlist did not reconcile")
            write(OUTPUT / "case-holdout.json", result)


if __name__ == "__main__":
    main()
