from __future__ import annotations

from datetime import UTC, date, datetime
import random

import pandas as pd

from core.utils import now_utc, write_json

_SEED = 42
_NOISE_SUFFIX = " xkq77 zzrandom-noise-block !!! lorem-ipsum-injected-noise ??? qwe999"
_STALE_DATE = date(2000, 1, 1)

_DROP_LATEST_FRACTION = 0.10
_BLANK_SUMMARY_FRACTION = 0.20
_NOISE_FRACTION = 0.20
_TRUNCATE_TITLE_FRACTION = 0.15
_STALE_DATE_FRACTION = 0.15
_DUPLICATE_FRACTION = 0.10


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    return f"Title: {row['title']} | Authors: {row['authors_joined']} | Summary: {row['summary']}"


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate nhieu dang data corruption tren cleaned dataframe va ghi corruption log.

    Kich ban:
    1. Drop mot so latest records (co the trung voi tai lieu trong test set -> giam retrieval hit rate).
    2. Blank summary o mot so dong.
    3. Truncate title o mot so dong.
    4. Lam stale publication date (nam 2000) o mot so dong -> fail freshness check.
    5. Rebuild text_for_embedding tu title/authors/summary da bi corrupt.
    6. Add noise vao text_for_embedding (sau khi rebuild) o mot so dong.
    7. Duplicate mot so rows (giu nguyen paper_id) -> fail uniqueness check.
    """
    if df is None or df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")

    rng = random.Random(_SEED)
    working = df.sort_values(by="published", ascending=False).reset_index(drop=True).copy()
    original_row_count = len(working)
    log: dict = {
        "generated_at": now_utc().isoformat(),
        "seed": _SEED,
        "total_rows_before": original_row_count,
        "scenarios": [],
    }

    # 1) Drop some latest records entirely.
    drop_count = max(1, round(original_row_count * _DROP_LATEST_FRACTION))
    dropped_rows = working.iloc[:drop_count]
    dropped_ids = dropped_rows["paper_id"].tolist()
    working = working.iloc[drop_count:].reset_index(drop=True)
    log["scenarios"].append({
        "type": "drop_latest_records",
        "count": len(dropped_ids),
        "paper_ids": dropped_ids,
    })

    n = len(working)

    def _sample(fraction: float) -> list[int]:
        count = max(1, round(n * fraction))
        count = min(count, n)
        return rng.sample(range(n), count)

    # 2) Blank summary.
    blank_idx = _sample(_BLANK_SUMMARY_FRACTION)
    blanked_ids = []
    for i in blank_idx:
        blanked_ids.append(working.at[i, "paper_id"])
        working.at[i, "summary"] = ""
        working.at[i, "summary_chars"] = 0
    log["scenarios"].append({"type": "blank_summary", "count": len(blank_idx), "paper_ids": blanked_ids})

    # 3) Truncate title.
    truncate_idx = _sample(_TRUNCATE_TITLE_FRACTION)
    truncated_ids = []
    for i in truncate_idx:
        original_title = str(working.at[i, "title"])
        truncated = original_title[: max(3, len(original_title) // 2)]
        truncated_ids.append(working.at[i, "paper_id"])
        working.at[i, "title"] = truncated
    log["scenarios"].append({"type": "truncate_title", "count": len(truncate_idx), "paper_ids": truncated_ids})

    # 4) Stale publication date.
    stale_idx = _sample(_STALE_DATE_FRACTION)
    stale_ids = []
    run_date = now_utc().date()
    for i in stale_idx:
        stale_ids.append(working.at[i, "paper_id"])
        working.at[i, "published"] = _STALE_DATE.isoformat()
        working.at[i, "age_days"] = (run_date - _STALE_DATE).days
    log["scenarios"].append({"type": "stale_publication_date", "count": len(stale_idx), "paper_ids": stale_ids})

    # 5) Rebuild text_for_embedding to reflect title/summary corruption above.
    working["text_for_embedding"] = working.apply(_rebuild_text_for_embedding, axis=1)

    # 6) Add noise into text_for_embedding (applied after rebuild so it isn't overwritten).
    noise_idx = _sample(_NOISE_FRACTION)
    noise_ids = []
    for i in noise_idx:
        noise_ids.append(working.at[i, "paper_id"])
        working.at[i, "text_for_embedding"] = working.at[i, "text_for_embedding"] + _NOISE_SUFFIX
    log["scenarios"].append({"type": "add_noise_to_embedding_text", "count": len(noise_idx), "paper_ids": noise_ids})

    # 7) Duplicate rows (same paper_id kept -> breaks uniqueness check).
    dup_count = max(1, round(n * _DUPLICATE_FRACTION))
    dup_count = min(dup_count, n)
    dup_idx = rng.sample(range(n), dup_count)
    dup_rows = working.iloc[dup_idx]
    dup_ids = dup_rows["paper_id"].tolist()
    working = pd.concat([working, dup_rows], ignore_index=True)
    log["scenarios"].append({"type": "duplicate_rows", "count": len(dup_ids), "paper_ids": dup_ids})

    log["total_rows_after"] = len(working)
    write_json(output_log_path, log)
    return working
