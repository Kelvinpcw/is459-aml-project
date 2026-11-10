"""Test a same-currency relay review lane on payments outside today's Q2 graph."""
from dataclasses import dataclass

import numpy as np

from model import ReleaseFeatures


@dataclass(frozen=True)
class Choice:
    model: np.ndarray
    relay: np.ndarray
    mixed: np.ndarray
    eligible: int
    supported_relay: int


def highest(ids: np.ndarray, value: np.ndarray, limit: int) -> np.ndarray:
    if not limit or not len(ids):
        return np.array([], dtype=np.uint32)
    # Stable tie-break on source ordinal and full ordering for at most one day's data.
    return ids[np.lexsort((ids, -value))[:limit]]


def daily_discovery(features: ReleaseFeatures, model: np.ndarray, day: int) -> Choice:
    part = features.day_rows(day, day)
    matrix = features.x[part]
    ids = features.ids[part]
    columns = {key: i for i, key in enumerate(features.names)}
    pattern = [columns[key] for key in ("fan_in", "fan_out", "cycle_2", "cycle_3", "cycle_4")]
    eligible = ~np.any(matrix[:, pattern], axis=1) & (matrix[:, columns["self_transfer"]] == 0)
    outside = ids[eligible]
    n = min(50, len(outside))
    ml = highest(outside, model[outside], n)
    before = matrix[eligible, columns["gap_from_sender_receipt"]]
    after = matrix[eligible, columns["gap_to_receiver_outflow_today"]]
    previous_match = matrix[eligible, columns["sender_receipt_amount_similarity"]]
    following_match = matrix[eligible, columns["receiver_outflow_amount_similarity"]]
    bound = np.log1p(np.float32(60.0))
    incoming = (before > 0) & (before <= bound) & (previous_match >= 0.8)
    onward = (after > 0) & (after <= bound) & (following_match >= 0.8)
    # Two matching neighbouring links outrank one, then exact amount similarity
    # and proximity break ties. The IBM labels are unavailable here.
    strength = np.where(incoming, 2 + previous_match - before / 100, 0)
    strength += np.where(onward, 2 + following_match - after / 100, 0)
    support = strength > 0
    relay_only = highest(outside[support], strength[support], n)
    reserved = n // 5
    novel = support & ~np.isin(outside, ml)
    extra = highest(outside[novel], strength[novel], reserved)
    mixed = np.concatenate((ml[:n - len(extra)], extra))
    return Choice(ml, relay_only, mixed, len(outside), int(np.count_nonzero(support)))
