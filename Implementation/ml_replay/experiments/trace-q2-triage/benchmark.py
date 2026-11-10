"""Compare label-free alert policies against the release's exact typed evidence rule."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import file_digest
from pathlib import Path
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
REPLAY = ROOT.parent / "trace-q2-full-replay"
ML = ROOT.parent / "trace-ml-experiment"
sys.path[:0] = [str(REPLAY), str(ML)]
from evaluate import ReplayFiles, binary, matching_cases, window_baseline
from prepare import FACT, KINDS, SOURCE_COUNT
from assess import Scope, load_scope, top_k

N = SOURCE_COUNT + 1
CHUNK = 20_000
DAY = 1440
BANK_ACCOUNTS = 2_077_023
PAYMENT_FAMILIES = ("boosted_payment_only", "logistic_context", "boosted_context",
                    "history_boost", "random_forest", "extra_trees")
FRACTIONS = (0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0, 15.0)
# A 95% validation payment-recall margin compensates for the small number of
# whole patterns in September 6–8. The much larger development reference set
# is used only for the ACH control because that policy doesn't train a model.
VALIDATION_RECALL_FLOOR = 0.95


@dataclass(frozen=True)
class Facts:
    sender: np.ndarray
    receiver: np.ndarray
    minute: np.ndarray
    ach: np.ndarray

    @classmethod
    def read(cls) -> Facts:
        source = binary(REPLAY / "work" / "facts.bin", FACT, SOURCE_COUNT)
        sender, receiver = np.zeros((2, N), dtype=np.uint32)
        minute = binary(ROOT.parent / "trace-70-30" / "work" / "minutes.i32", np.dtype("<i4"), N)
        for start in range(0, len(source), 500_000):
            block = source[start:start+500_000]
            ids = block["id"]
            if not np.array_equal(minute[ids], block["minute"]):
                raise ValueError("Time index disagrees with curated facts")
            sender[ids] = block["sender"]
            receiver[ids] = block["receiver"]
        formats = binary(ML / "work" / "formats.u8", np.dtype("u1"), N)
        codes = json.loads((ML / "work" / "input.json").read_text())["format_codes"]
        ach = formats == codes["ACH"]
        ach[0] = False
        return cls(sender, receiver, minute, ach)


@dataclass(frozen=True)
class Policy:
    name: str
    model: str
    percent: float
    lower_percent: float
    lookback_days: int
    minimum_seeds: int
    evidence: str


@dataclass(frozen=True)
class Projection:
    retained: np.ndarray
    linked: np.ndarray
    context: np.ndarray
    members_reviewed: int


@dataclass(frozen=True)
class CaseGroup:
    begin: int
    end: int
    day: int
    members: np.ndarray
    sizes: np.ndarray
    offsets: np.ndarray
    kind: np.ndarray


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def day_groups(data: ReplayFiles, scope: Scope) -> list[CaseGroup]:
    days = data.cases["day"]
    first, last = np.searchsorted(days, [scope.first, scope.last+1])
    groups = []
    for day in range(scope.first, scope.last + 1):
        begin, end = np.searchsorted(days[first:last], [day, day+1]) + first
        for a in range(begin, end, CHUNK):
            b = min(a + CHUNK, end)
            sizes = data.cases["size"][a:b].astype(np.int64)
            offsets = data.scored["offset"][a:b].astype(np.int64)
            if np.any(sizes == 0) or not np.array_equal(np.diff(offsets), sizes[:-1]):
                raise ValueError("Published case evidence is empty or not contiguous")
            members = data.evidence[offsets[0]:offsets[-1]+sizes[-1]]
            if np.any(data.days[members] > day):
                raise ValueError(f"Future evidence in a case dated September {day}")
            groups.append(CaseGroup(a, b, day, members, sizes, offsets-offsets[0], data.cases["kind"][a:b]))
    return groups


def scores_path(name: str) -> Path:
    from_prior = name in PAYMENT_FAMILIES[:3]
    return (ML if from_prior else ROOT) / "work" / f"{name}.scores.f32"


def get_scores(name: str) -> np.ndarray:
    scores = binary(scores_path(name), np.dtype("<f4"), N)
    if not np.all(np.isfinite(scores[1:])):
        raise ValueError(f"Non-finite score in {name}")
    return scores


def ranked(scope: Scope, scores: np.ndarray) -> np.ndarray:
    """Assign 1-based ranks within each payment day, resolving ties by source ordinal."""
    values = scores[scope.ids]
    result = np.empty(len(values), dtype=np.uint32)
    for day in range(scope.first, scope.last+1):
        positions = np.flatnonzero(scope.days == day)
        ordered = positions[np.argsort(-values[positions], kind="stable")]
        result[ordered] = np.arange(1, len(ordered)+1, dtype=np.uint32)
    return result


def fraction(scope: Scope, rank: np.ndarray, percent: float) -> np.ndarray:
    counts = np.bincount(scope.days, minlength=29)
    limit = np.ceil(counts * (percent / 100)).astype(np.uint32)
    return rank <= limit[scope.days]


def dates_for(scope: Scope, selected: np.ndarray) -> np.ndarray:
    out = np.zeros(N, dtype=np.uint8)
    out[scope.ids[selected]] = scope.days[selected]
    return out


def shared_account_retro(facts: Facts, scope: Scope, seeds: np.ndarray, weak: np.ndarray,
                         lookback: int) -> np.ndarray:
    """Reopen earlier same-account payments after a later independent seed."""
    seed_ids = scope.ids[seeds]
    support = scope.ids[weak & ~seeds]
    minute = facts.minute[support].astype(np.int64)
    radix = 1 << 16
    if minute.max(initial=0) >= radix or facts.minute[seed_ids].max(initial=0) >= radix:
        raise ValueError("Minute does not fit in the account-time key")
    seed_minute = facts.minute[seed_ids].astype(np.int64)
    times = np.sort(np.concatenate((facts.sender[seed_ids].astype(np.int64)*radix + seed_minute,
                                    facts.receiver[seed_ids].astype(np.int64)*radix + seed_minute)))
    # A sentinel only enables index-safe lookup. The account check excludes it.
    times = np.append(times, np.int64(BANK_ACCOUNTS * radix))
    following = []
    for account in (facts.sender[support], facts.receiver[support]):
        key = account.astype(np.int64)*radix + minute
        hit = times[np.searchsorted(times, key, side="right")]
        delta = hit % radix - minute
        following.append(np.where((hit // radix == account) & (delta <= lookback*DAY), hit % radix, radix))
    trigger = np.minimum(following[0], following[1])
    eligible = trigger < radix
    activated = dates_for(scope, seeds)
    activated[support[eligible]] = trigger[eligible] // DAY + 1
    if np.any(activated[support[eligible]] < scope.days[weak & ~seeds][eligible]):
        raise ValueError("Retroactive alert preceded its payment day")
    return activated


def anchored_case_retro(groups: list[CaseGroup], seeds: np.ndarray, weak: np.ndarray,
                       minimum: int) -> np.ndarray:
    """Activate weak payments only in a published case that has independent seeds."""
    activated = seeds.copy()
    for group in groups:
        m = group.members
        seed_hits = (seeds[m] != 0) & (seeds[m] <= group.day)
        active = np.add.reduceat(seed_hits, group.offsets, dtype=np.int32) >= minimum
        if not np.any(active):
            continue
        fresh = m[np.repeat(active, group.sizes) & weak[m] & (activated[m] == 0)]
        activated[fresh] = group.day
    return activated


def shape_survives(facts: Facts, group: CaseGroup, include: np.ndarray) -> np.ndarray:
    """Recheck five distinct fan peers or every cycle leg in the reduced evidence."""
    indices = np.repeat(np.arange(len(group.sizes), dtype=np.uint64), group.sizes)[include]
    m = group.members[include]
    # Every published cycle has one outgoing edge per node. Distinct senders
    # therefore count legs for a cycle and distinct counterparties for fan-in.
    peer = np.where(group.kind[indices] == 1, facts.receiver[m], facts.sender[m])
    keys = np.unique((indices << np.uint64(32)) | peer)
    distinct = np.bincount((keys >> np.uint64(32)).astype(np.int64), minlength=len(group.sizes))
    return distinct >= np.where(group.kind < 2, 5, group.kind)


def project(data: ReplayFiles, facts: Facts, groups: list[CaseGroup], activated: np.ndarray,
            minimum: int, evidence: str) -> Projection:
    linked = np.zeros(N, dtype=bool)
    context = np.zeros(N, dtype=bool)
    retained = np.zeros(len(data.cases), dtype=bool)
    member_count = 0
    for group in groups:
        when = activated[group.members]
        signal = (when != 0) & (when <= group.day)
        keep = np.add.reduceat(signal, group.offsets, dtype=np.int32) >= minimum
        if evidence == "shape":
            keep &= shape_survives(facts, group, signal)
        retained[group.begin:group.end] = keep
        copies = np.repeat(keep, group.sizes)
        context[group.members[copies]] = True
        linked[group.members[copies & signal]] = True
        member_count += int(np.count_nonzero(copies if evidence == "full" else copies & signal))
    return Projection(retained, linked, context, member_count)


def payment_metrics(scope: Scope, flagged: np.ndarray) -> dict:
    selected = flagged[scope.ids]
    n = int(np.count_nonzero(selected))
    tp = int(np.count_nonzero(selected & scope.positive))
    positives = int(np.count_nonzero(scope.positive))
    return {"payments": len(selected), "ibm_positive_population": positives, "alerts": n,
            "ibm_positive": tp, "ibm_zero": n-tp, "missed_ibm_positive": positives-tp,
            "precision": tp/n if n else None, "recall": tp/positives if positives else None,
            "f1": 2*tp/(n+positives), "outside_published_q2": int(np.count_nonzero(selected & ~scope.structural))}


def coverage(data: ReplayFiles, refs: list[dict], matches: dict[str, set[int]],
             rows: np.ndarray, activated: np.ndarray, evidence: str) -> dict:
    by_kind = Counter()
    witnesses = []
    missing = []
    for ref in refs:
        expected = np.asarray(ref["ordinals"], dtype=np.uint32)
        attempts = []
        for row in matches[ref["attempt_id"]]:
            if not rows[row]:
                continue
            day = int(data.cases[row]["day"])
            allowed = expected
            if evidence != "full":
                when = activated[expected]
                allowed = expected[(when != 0) & (when <= day)]
            present = allowed[np.isin(allowed, data.members(row))]
            if 5*len(present) >= 4*len(expected):
                attempts.append((day, -len(present), row, present))
        if not attempts:
            missing.append({"attempt_id": ref["attempt_id"], "kind": KINDS[ref["kind"]]})
            continue
        day, count, row, present = min(attempts, key=lambda r: r[:3])
        by_kind[ref["kind"]] += 1
        witnesses.append({"attempt_id": ref["attempt_id"], "kind": KINDS[ref["kind"]],
                          "case_id": data.case_ids[row].decode("ascii"), "snapshot_day": day,
                          "annotated_payments": len(expected), "retained_payments": -count,
                          "retained_ordinals": list(map(int, present))})
    eligible = Counter(ref["kind"] for ref in refs)
    return {"eligible": len(refs), "recovered": len(witnesses),
            "by_kind": {kind: [by_kind[i], eligible[i]] for i, kind in enumerate(KINDS)},
            "missed": missing, "witnesses": witnesses}


def setting(name: str, model: str, percent: float, low: float, window: int,
            min_seeds: int, evidence: str) -> Policy:
    return Policy(name, model, percent, low, window, min_seeds, evidence)


def plan(model_names: tuple[str, ...]) -> list[Policy]:
    policies = [setting("published_q2", "none", 0, 0, 0, 0, "full"),
                setting("ach_graph", "ach", 0, 0, 0, 1, "shape")]
    for model in model_names:
        policies.extend(setting(f"{model}_{pct:g}pct", model, pct, 0, 0, 1, "signal")
                        for pct in FRACTIONS)
    for pct in (0.5, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0):
        policies.extend((setting(f"graph_{pct:g}pct_valid_shape", "boosted_context", pct, 0, 0, 1, "shape"),
                         setting(f"graph_{pct:g}pct_full_case", "boosted_context", pct, 0, 0, 2, "full")))
    for high, low in ((0.25, 2.0), (0.5, 3.0), (1.0, 5.0), (2.0, 7.5)):
        for window in (1, 3, 6):
            policies.append(setting(f"shared_account_{high:g}_{low:g}_{window}d",
                                    "boosted_context", high, low, window, 1, "signal"))
        for minimum in (1, 2):
            policies.append(setting(f"same_case_{high:g}_{low:g}_{minimum}seed",
                                    "boosted_context", high, low, 0, minimum, "shape"))
    for percent in (90, 95, 99, 100):
        policies.append(setting(f"graph_frozen_recall_{percent}", "boosted_context", percent, 0, 0, 1,
                                "threshold"))
    return policies


def evaluate_policy(data: ReplayFiles, facts: Facts, scope: Scope, groups: list[CaseGroup],
                    matches: dict[str, set[int]], policy: Policy, ranks: dict[str, np.ndarray],
                    values: dict[str, np.ndarray], thresholds: dict[str, dict]) -> dict:
    if policy.model == "none":
        active = data.days
    elif policy.model == "ach":
        active = np.where(facts.ach, data.days, 0)
    elif policy.evidence == "threshold":
        active = dates_for(scope, values[policy.model][scope.ids] >= thresholds[policy.model][str(int(policy.percent))]["threshold"])
    else:
        rank = ranks[policy.model]
        high = fraction(scope, rank, policy.percent)
        low = fraction(scope, rank, policy.lower_percent)
        active = dates_for(scope, high)
        if policy.lookback_days:
            active = shared_account_retro(facts, scope, high, low, policy.lookback_days)
        elif policy.lower_percent:
            weak = np.zeros(N, dtype=bool)
            weak[scope.ids[low]] = True
            active = anchored_case_retro(groups, active, weak, policy.minimum_seeds)
    minimum = policy.minimum_seeds if policy.evidence == "full" else 1
    projection = project(data, facts, groups, active, minimum, policy.evidence)
    alert = projection.context if policy.evidence == "full" else projection.linked
    if policy.evidence in ("signal", "threshold"):
        alert = active != 0
    case_alerts = projection.context if policy.evidence == "full" else projection.linked
    report = payment_metrics(scope, alert)
    report["typed"] = coverage(data, scope.references, matches, projection.retained, active, policy.evidence)
    report["case_only"] = payment_metrics(scope, case_alerts)
    report["case_snapshots"] = int(np.count_nonzero(projection.retained))
    report["flagged_case_memberships"] = projection.members_reviewed
    report["distinct_full_case_context_payments"] = int(np.count_nonzero(projection.context[scope.ids]))
    report["policy"] = asdict(policy)
    return report


def family(policy: Policy) -> str:
    if policy.name.startswith("shared_account"):
        return "shared_account"
    if policy.name.startswith("same_case"):
        return "same_case"
    if policy.name.endswith("full_case"):
        return "full_case"
    if policy.name.endswith("valid_shape"):
        return "valid_shape"
    if policy.evidence == "threshold":
        return "frozen_score_threshold"
    return policy.model


def validate(data: ReplayFiles, phase: str, scope: Scope, matches: dict[str, set[int]],
             results: dict[str, dict]) -> None:
    baseline = results["published_q2"]
    if baseline["typed"]["recovered"] != len(scope.references) or not np.array_equal(
            np.fromiter((bool(x) for x in matches.values()), dtype=bool), np.ones(len(matches), dtype=bool)):
        raise ValueError("Published baseline does not recover every eligible reference")
    if phase != "validation":
        observed = window_baseline(phase)
        tx = observed["detector_transaction_metrics"]
        expected = (observed["case_count"], tx["population"], tx["unique_alerted_transactions"],
                    tx["true_positive"], tx["false_positive"], observed["annotation_metrics"]["eligible_attempts"])
        actual = (baseline["case_snapshots"], baseline["payments"], baseline["alerts"], baseline["ibm_positive"],
                  baseline["ibm_zero"], baseline["typed"]["eligible"])
        if actual != expected:
            raise ValueError(f"Baseline replay disagrees with AWS for {phase}: {actual} vs {expected}")


def evaluate(data: ReplayFiles, facts: Facts, phase: str, policies: list[Policy]) -> dict[str, dict]:
    scope = load_scope(data, phase)
    groups = day_groups(data, scope)
    rows = np.flatnonzero((data.cases["day"] >= scope.first) & (data.cases["day"] <= scope.last))
    matches = matching_cases(data, scope.references, rows)
    values = {name: get_scores(name) for name in sorted({p.model for p in policies} - {"none", "ach"})}
    ranks = {name: ranked(scope, score) for name, score in values.items()}
    meta = json.loads((ML / "model-freeze.json").read_text())
    thresholds = {name: item["frozen_validation_targets"] for name, item in meta["model_results"].items()}
    results = {}
    for policy in policies:
        report = evaluate_policy(data, facts, scope, groups, matches, policy, ranks, values, thresholds)
        results[policy.name] = report
        print(phase, policy.name, report["alerts"], report["ibm_positive"],
              report["typed"]["recovered"], report["case_snapshots"], flush=True)
    validate(data, phase, scope, matches, results)
    return results


def freeze(data: ReplayFiles, facts: Facts, model_names: tuple[str, ...]) -> None:
    specs = plan(model_names)
    results = evaluate(data, facts, "validation", specs)
    selected = ["published_q2", "ach_graph", "graph_frozen_recall_95", "graph_frozen_recall_99",
                "graph_frozen_recall_100", "boosted_context_0.5pct", "boosted_context_1pct",
                "boosted_context_3pct", "boosted_context_5pct", "boosted_context_10pct",
                "graph_5pct_valid_shape", "graph_10pct_valid_shape", "graph_1pct_full_case",
                "graph_5pct_full_case", "same_case_1_5_1seed", "shared_account_1_5_3d"]
    selected_by_family = {}
    for key in sorted({family(p) for p in specs} - {"ach", "none"}):
        options = [p.name for p in specs if family(p) == key]
        scored = [results[name] for name in options]
        best = [x for x in scored if x["typed"]["recovered"] == x["typed"]["eligible"]
                and x["recall"] >= VALIDATION_RECALL_FLOOR]
        if best:
            choice = min(best, key=lambda x: (x["alerts"], x["case_snapshots"]))
        else:
            # For methods without a feasible high-recall point, compare their best
            # F1 among validation policies with every typed pattern.
            choice = max(scored, key=lambda x: (x["typed"]["recovered"], x["f1"]))
        name = choice["policy"]["name"]
        selected_by_family[key] = {"selected": name, "met_validation_constraint": bool(best)}
        if name not in selected:
            selected.append(name)
    write(ROOT / "validation-results.json", results)
    write(ROOT / "policy-freeze.json", {
        "policy_code_sha256": digest(Path(__file__)), "validation_days": [6, 8], "test_days": [9, 16],
        "sparse_tail_days": [17, 28], "minimum_validation_recall": VALIDATION_RECALL_FLOOR,
        "validation_references": len(next(iter(results.values()))["typed"]["witnesses"]),
        "validation_choice_by_family": selected_by_family,
        "replayed_release": "full-20261030-v1",
        "score_digests": {name: digest(scores_path(name)) for name in model_names},
        "policies": [results[name]["policy"] for name in selected],
    })
    print("Policy choices frozen", selected_by_family, flush=True)


def main() -> None:
    data = ReplayFiles(REPLAY / "work")
    facts = Facts.read()
    command = sys.argv[1]
    if command == "freeze":
        freeze(data, facts, tuple(sys.argv[2:]))
        return
    saved = json.loads((ROOT / "policy-freeze.json").read_text())
    if saved["policy_code_sha256"] != digest(Path(__file__)):
        raise ValueError("Policy code changed after calibration")
    for name, expected in saved["score_digests"].items():
        if expected != digest(scores_path(name)):
            raise ValueError(f"Model score file changed after calibration: {name}")
    specs = [Policy(**p) for p in saved["policies"]]
    for phase in ("holdout", "sparse_tail"):
        result = evaluate(data, facts, phase, specs)
        write(ROOT / f"{phase}-results.json", result)


if __name__ == "__main__":
    main()
