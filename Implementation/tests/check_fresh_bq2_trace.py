"""Exercise the real TRACE app against a locally published fresh BQ2 mirror."""

import argparse
from pathlib import Path
import os
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from dashboard.data import get_case
from dashboard.fresh_bq2 import fresh_bq2
from pipeline.bq2_release import BQ2_CURRENT_URI, LocalBQ2Objects


def check(mirror: Path) -> None:
    store = LocalBQ2Objects(mirror)
    published = fresh_bq2(store, BQ2_CURRENT_URI)
    metrics = published.metrics
    app_path = Path(__file__).resolve().parents[1] / "dashboard/app.py"
    with patch.dict(os.environ, {"TRACE_BQ2_LOCAL_MIRROR": str(mirror.resolve())}):
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        assert not app.exception and not app.error, [item.value for item in [*app.exception, *app.error]]
        assert [tab.label for tab in app.tabs] == ["Ranked investigations", "Payment alerts"]
        assert any(published.release["release_id"] in caption.value for caption in app.caption)
        if len(published.cases):
            first = published.cases.to_pylist()[0]
            evidence = next(item.value for item in app.dataframe if "amount_paid" in item.value.columns)
            assert set(evidence["source_id"]) == set(first["highlighted_source_ids"])
            locator = next(row for row in published.evidence_index.to_pylist()
                           if row["case_id"] == first["case_id"]
                           and row["snapshot_cutoff"] == first["snapshot_cutoff"].isoformat())
            case, _ = get_case(store, published.release, locator)
            edge = case["edges"][0]
            # AppTest drives Python state. The browser component sets this state when an arrow is selected.
            app.session_state["ml_replay_edge_" + case["case_id"]] = (edge["source"], edge["target"])
            app.run()
            assert not app.exception and not app.error, [item.value for item in [*app.exception, *app.error]]
            linked = next(item.value for item in app.dataframe if "ML highlighted" in item.value.columns)
            assert 0 < len(linked) <= edge["transaction_count"]
            print(f"TRACE displayed {len(evidence)} highlighted payments and {len(linked)} payments for the selected link")
        else:
            assert any(item.value == "No ranked investigations match this pattern." for item in app.info)

        app.radio(key="fresh_bq2_workspace").set_value("Evaluation & coverage").run()
        assert not app.exception and not app.error, [item.value for item in [*app.exception, *app.error]]
        assert any(item.value == "Fresh batch ML evaluation" for item in app.subheader)
        coverage = f"{metrics['labelled_payments']:,} of {metrics['eligible_payments']:,}"
        assert any(coverage in caption.value for caption in app.caption)
        for field in ("payment_precision", "payment_recall"):
            value = metrics[field]
            display = "Unavailable" if value is None else f"{value:.4%}"
            assert any(display in row.value for row in app.markdown)
        print(f"TRACE evaluated cutoff {metrics['cutoff']} with verified label coverage {coverage}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mirror", type=Path)
    check(parser.parse_args().mirror)
