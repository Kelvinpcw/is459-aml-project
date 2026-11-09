"""Case selection and feature calculations reused from the frozen local replay."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from rank_shortlist import CaseFacts, Facts, ReplayFiles, Window

CHUNK = 20_000
CAP = 4


@dataclass(frozen=True)
class CaseGroup:
    begin: int
    end: int
    day: int
    members: np.ndarray
    sizes: np.ndarray
    offsets: np.ndarray
    kind: np.ndarray

def day_groups(data: ReplayFiles, scope: Window) -> list[CaseGroup]:
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

@dataclass(frozen=True)
class Policy:
    name: str
    score_floor: float
    max_gap: int
    max_missing_legs: int
    extra_gap: int
    extra_limit: int

def distance_to_alert(minutes: np.ndarray, anchor_minutes: np.ndarray) -> np.ndarray:
    when = np.unique(anchor_minutes)
    position = np.searchsorted(when, minutes)
    before = when[np.maximum(position - 1, 0)]
    after = when[np.minimum(position, len(when) - 1)]
    return np.minimum(np.abs(minutes - before), np.abs(minutes - after))

def complete_case(ids: np.ndarray, peers: np.ndarray, picked: np.ndarray, distance: np.ndarray,
                  score: np.ndarray, required: int, policy: Policy) -> np.ndarray:
    anchored = np.unique(peers[picked])
    missing = max(0, required - len(anchored))
    if missing > policy.max_missing_legs or not len(anchored):
        return np.empty(0, dtype=np.uint32)
    candidates = np.flatnonzero(~picked & (distance <= policy.max_gap) & (score >= policy.score_floor))
    if len(candidates) == 0:
        return np.empty(0, dtype=np.uint32)
    ordered = candidates[np.lexsort((ids[candidates], -score[candidates]))]
    new_legs = ordered[~np.isin(peers[ordered], anchored)]
    _, first = np.unique(peers[new_legs], return_index=True)
    new_legs = new_legs[np.sort(first)]
    if len(new_legs) < missing:
        return np.empty(0, dtype=np.uint32)
    selected = new_legs[:missing]
    extra = ordered[(distance[ordered] <= policy.extra_gap) & ~np.isin(ordered, selected)]
    extra = extra[:min(policy.extra_limit, CAP - len(selected))]
    return ids[np.r_[selected, extra]]

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

SHAPE_FEATURES = (
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

def payment_peers(facts: Facts, members: np.ndarray, kind: int) -> np.ndarray:
    return facts.receiver[members] if kind == 1 else facts.sender[members]

def features(data: ReplayFiles, facts: CaseFacts, rows: np.ndarray) -> np.ndarray:
    matrix = np.empty((len(rows), len(SHAPE_FEATURES)), dtype=np.float32)
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

PROGRESS_FEATURES = ("fan_in", "fan_out", "cycle_2", "cycle_3", "cycle_4", "core_size_log", "core_peers_log",
            "core_fraction", "core_ach_share", "core_ach_peer_share", "core_same_currency_share",
            "core_dominant_currency_share", "core_dominant_currency_amount_median",
            "core_dominant_currency_amount_iqr", "core_time_span_log", "core_active_days",
            "core_latest_day_share", "core_days_since_latest_payment", "snapshot_count_log",
            "observed_core_peers_log", "core_new_evidence_share", "core_change_since_prior",
            "core_payments_seen_so_far_log", "mean_core_relative_to_peak_size",
            "days_since_first_version")

def progress_features(data: ReplayFiles, facts: CaseFacts, versions: dict[int, list[Version]]) -> tuple[np.ndarray, list[Version]]:
    rows = [version for day in sorted(versions) for version in versions[day]]
    x = np.empty((len(rows), len(PROGRESS_FEATURES)), dtype=np.float32)
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
