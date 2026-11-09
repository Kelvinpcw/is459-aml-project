"""Stage only the published facts and the verified IBM HI-Small training file."""
from __future__ import annotations

import json
import sys
from hashlib import file_digest
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as csv
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent
REPLAY = ROOT.parent / "trace-q2-full-replay"
MEDIUM = REPLAY / "work"
MEDIUM_AUX = ROOT.parent / "trace-ml-experiment" / "work"
SMALL = ROOT / "work" / "small"
DOWNLOAD = ROOT / "inputs" / "HI-Small_Trans.csv.part"
SMALL_FILE = DOWNLOAD.with_suffix("")
SMALL_SHA = "b19d39f515523373f991b689c07e11e7b0b95c17a2c27a87d91584ae16c5b040"
SMALL_ROWS, SMALL_POSITIVES = 5_078_345, 5_177

sys.path.insert(0, str(REPLAY))
from prepare import EPOCH, FACT, RELEASE, SOURCE_COUNT, coded, decimal_words, require, sources

RAW_HEADER = "Timestamp,From Bank,Account,To Bank,Account,Amount Received,Receiving Currency,Amount Paid,Payment Currency,Payment Format,Is Laundering"
COLS = ("timestamp", "sender_bank", "sender_account", "receiver_bank", "receiver_account",
        "amount_received", "receiving_currency", "amount_paid", "payment_currency",
        "payment_format", "label")


def currency_codes() -> dict[str, int]:
    """Verify the legacy binary currency IDs against their published string values."""
    facts = np.memmap(MEDIUM / "facts.bin", dtype=FACT, mode="r", shape=(SOURCE_COUNT,))
    currencies: dict[str, int] = {}
    offset = 0
    for day in range(1, 29):
        for path in sources("facts", day):
            for batch in pq.ParquetFile(path).iter_batches(
                batch_size=262144,
                columns=["source_record_ordinal", "payment_currency", "receiving_currency"],
            ):
                block = facts[offset:offset + len(batch)]
                require(np.array_equal(block["id"], batch[0].to_numpy()), "Curated fact order changed")
                for column, field in ((batch[1], "paid_currency"), (batch[2], "received_currency")):
                    values = column.dictionary_encode()
                    require(values.null_count == 0, "Missing HI-Medium currency")
                    keys = np.unique((block[field].astype(np.uint32) << 16)
                                     | values.indices.to_numpy().astype(np.uint32))
                    for key in keys:
                        name = values.dictionary[int(key & 65535)].as_py()
                        code = int(key >> 16)
                        require(currencies.setdefault(name, code) == code,
                                f"Inconsistent currency mapping for {name}")
                offset += len(batch)
    require(offset == SOURCE_COUNT and len(set(currencies.values())) == len(currencies),
            "HI-Medium currency mapping was incomplete or ambiguous")
    return currencies


def checked_download() -> Path:
    source = SMALL_FILE if SMALL_FILE.is_file() else DOWNLOAD
    with source.open("rb") as stream:
        require(file_digest(stream, "sha256").hexdigest() == SMALL_SHA, "HI-Small SHA-256 mismatch")
    if source != SMALL_FILE:
        source.rename(SMALL_FILE)
    return SMALL_FILE


def stage() -> None:
    source = checked_download()
    with source.open("rb") as stream:
        require(stream.readline().decode("utf-8").strip() == RAW_HEADER, "IBM CSV header changed")
    currencies = currency_codes()
    aux = json.loads((MEDIUM_AUX / "input.json").read_text())
    formats: dict[str, int] = aux["format_codes"]
    accounts: dict[str, int] = {}
    label_count, count = 0, 0
    SMALL.mkdir(parents=True, exist_ok=True)
    types = {name: pa.string() for name in COLS}
    types.update(timestamp=pa.timestamp("s"), amount_paid=pa.decimal128(38, 8),
                 amount_received=pa.decimal128(38, 8), label=pa.uint8(),
                 sender_bank=pa.uint32(), receiver_bank=pa.uint32())
    reader = csv.open_csv(
        source,
        read_options=csv.ReadOptions(skip_rows=1, column_names=list(COLS), block_size=8 << 20),
        convert_options=csv.ConvertOptions(column_types=types, timestamp_parsers=["%Y/%m/%d %H:%M"]),
    )
    with ((SMALL / "facts.bin").open("wb") as fact_file,
          (SMALL / "formats.u8").open("wb") as format_file,
          (SMALL / "labels.u8").open("wb") as label_file):
        format_file.write(bytes([255]))
        label_file.write(bytes([255]))
        for batch in reader:
            table = pa.Table.from_batches([batch])
            require(all(col.null_count == 0 for col in table.columns), "Unexpected null HI-Small field")
            records = np.zeros(len(batch), dtype=FACT)
            records["id"] = np.arange(count + 1, count + len(batch) + 1, dtype=np.uint32)
            delta = pc.cast(table["timestamp"], pa.int64()).to_numpy() - int(
                (EPOCH - EPOCH.replace(year=1970, month=1, day=1)).total_seconds())
            require(bool(np.all(delta >= 0) and np.all(delta % 60 == 0)), "Invalid HI-Small timestamp")
            records["minute"] = delta // 60
            for side in ("sender", "receiver"):
                identity = pc.binary_join_element_wise(pc.cast(table[f"{side}_bank"], pa.string()),
                                                       table[f"{side}_account"], ":")
                records[side] = coded(identity, accounts, np.dtype("<u4"))
            records["paid"] = decimal_words(table, "amount_paid")
            records["received"] = decimal_words(table, "amount_received")
            records["paid_currency"] = coded(table["payment_currency"], currencies, np.dtype("<u2"))
            records["received_currency"] = coded(table["receiving_currency"], currencies, np.dtype("<u2"))
            labels = table["label"].to_numpy()
            require(bool(np.all(labels < 2)), "Invalid HI-Small IBM label")
            records.tofile(fact_file)
            coded(table["payment_format"], formats, np.dtype("u1")).tofile(format_file)
            labels.tofile(label_file)
            count += len(batch)
            label_count += int(labels.sum())
    require((count, label_count) == (SMALL_ROWS, SMALL_POSITIVES), "Unexpected HI-Small input totals")
    np.fromiter((int(key.split(":", 1)[0]) for key in accounts), dtype="<u4",
                count=len(accounts)).tofile(SMALL / "banks.u32")
    (SMALL / "manifest.json").write_text(json.dumps({
        "source": "IBM AMLworld HI-Small Kaggle file, verified public mirror",
        "sha256": SMALL_SHA, "rows": count, "positive_labels": label_count,
        "accounts": len(accounts), "currency_codes": currencies, "format_codes": formats,
        "target_release": RELEASE["release_id"], "target_rows": SOURCE_COUNT,
        "target_accounts": aux["accounts"],
    }, indent=2) + "\n")
    print(f"Staged {count:,} verified HI-Small payments ({label_count:,} IBM-positive); "
          f"aligned categorical codes to {SOURCE_COUNT:,} verified HI-Medium facts", flush=True)


if __name__ == "__main__":
    stage()
