"""Attach the published payment-format field and normalized same-bank indicators."""
import json
from pathlib import Path
import sys

import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parent / "trace-q2-full-replay"
REPLAY = PREVIOUS / "work"
sys.path.insert(0, str(PREVIOUS))
from prepare import FACT, SOURCE_COUNT, inventory, require, sources, verified_file


def stage(work: Path) -> None:
    formats = np.full(SOURCE_COUNT + 1, 255, dtype=np.uint8)
    values: dict[str, int] = {}
    checks = inventory()
    days = np.memmap(REPLAY / "days.u8", dtype=np.uint8, mode="r")
    for day in range(1, 29):
        count = 0
        for path in sources("facts", day):
            verified_file(path, checks)
            table = pq.ParquetFile(path).read(columns=["source_record_ordinal", "payment_format"])
            ids = table["source_record_ordinal"].to_numpy()
            encoded = table["payment_format"].combine_chunks().dictionary_encode()
            require(encoded.null_count == 0 and bool(np.all(days[ids] == day))
                    and len(np.unique(ids)) == len(ids) and bool(np.all(formats[ids] == 255)),
                    f"Unexpected payment-format identity in {path}")
            codes = np.array([values.setdefault(x, len(values)) for x in encoded.dictionary.to_pylist()],
                             dtype=np.uint8)
            formats[ids] = codes[encoded.indices.to_numpy()]
            count += len(ids)
        print(f"Verified payment format for September {day:02}: {count:,}", flush=True)
    require(bool(np.all(formats[1:] != 255)), "Missing published payment formats")
    accounts = json.loads((REPLAY / "accounts.json").read_text())
    bank_ids: dict[str, int] = {}
    banks = np.fromiter((bank_ids.setdefault(key.split(":", 1)[0], len(bank_ids)) for key in accounts),
                        dtype=np.uint32, count=len(accounts))
    formats.tofile(work / "formats.u8")
    banks.tofile(work / "banks.u32")
    (work / "input.json").write_text(json.dumps({"format_codes": values, "accounts": len(accounts),
                                                 "transactions": SOURCE_COUNT}, indent=2) + "\n")


if __name__ == "__main__":
    stage(Path(sys.argv[1]).resolve())
