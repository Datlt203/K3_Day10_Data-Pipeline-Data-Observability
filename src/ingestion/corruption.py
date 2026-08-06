from __future__ import annotations

import pandas as pd


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate various types of data corruption on clean dataframe."""
    import json
    from pathlib import Path

    if df.empty:
        return df.copy()

    corrupted_df = df.copy()
    log_entries = []
    total_rows = len(corrupted_df)

    # 1. Drop some latest records (e.g. 15% of records)
    drop_count = max(1, int(total_rows * 0.15))
    dropped_ids = corrupted_df.iloc[:drop_count]["paper_id"].tolist()
    corrupted_df = corrupted_df.iloc[drop_count:].reset_index(drop=True)
    log_entries.append({"action": "drop_latest_records", "count": len(dropped_ids), "dropped_ids": dropped_ids})

    current_len = len(corrupted_df)
    if current_len > 0:
        # 2. Blank summary on some rows (row 0)
        blank_idx = 0
        target_paper_id = corrupted_df.at[blank_idx, "paper_id"]
        corrupted_df.at[blank_idx, "summary"] = ""
        corrupted_df.at[blank_idx, "summary_chars"] = 0
        log_entries.append({"action": "blank_summary", "paper_id": target_paper_id})

    if current_len > 1:
        # 3. Inject noise into text summary (row 1)
        noise_idx = 1
        target_paper_id = corrupted_df.at[noise_idx, "paper_id"]
        original = corrupted_df.at[noise_idx, "summary"]
        corrupted_df.at[noise_idx, "summary"] = "CORRUPTED_TEXT_NOISE " * 5 + original[:50]
        log_entries.append({"action": "inject_noise", "paper_id": target_paper_id})

    if current_len > 2:
        # 4. Truncate title (row 2)
        trunc_idx = 2
        target_paper_id = corrupted_df.at[trunc_idx, "paper_id"]
        original_title = corrupted_df.at[trunc_idx, "title"]
        corrupted_df.at[trunc_idx, "title"] = original_title[:10] + "..."
        log_entries.append({"action": "truncate_title", "paper_id": target_paper_id})

    if current_len > 3:
        # 5. Make published date stale (row 3)
        stale_idx = 3
        target_paper_id = corrupted_df.at[stale_idx, "paper_id"]
        corrupted_df.at[stale_idx, "published"] = "2000-01-01"
        corrupted_df.at[stale_idx, "age_days"] = 9000
        log_entries.append({"action": "make_stale_date", "paper_id": target_paper_id})

    if current_len > 4:
        # 6. Add duplicate rows (duplicate row 4)
        dup_row = corrupted_df.iloc[[4]].copy()
        corrupted_df = pd.concat([corrupted_df, dup_row], ignore_index=True)
        log_entries.append({"action": "add_duplicate_row", "paper_id": dup_row.iloc[0]["paper_id"]})

    # 7. Rebuild text_for_embedding
    corrupted_df["text_for_embedding"] = (
        "Title: " + corrupted_df["title"].astype(str) + "\n"
        + "Authors: " + corrupted_df["authors_joined"].astype(str) + "\n"
        + "Categories: " + corrupted_df["categories_joined"].astype(str) + "\n"
        + "Summary: " + corrupted_df["summary"].astype(str)
    )

    # 8. Write log
    if output_log_path:
        log_path = Path(output_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({"corruption_actions": log_entries}, f, ensure_ascii=False, indent=2)

    return corrupted_df

