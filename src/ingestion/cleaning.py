from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw PaperRecords into a pandas DataFrame ready for embedding."""
    if not records:
        return pd.DataFrame()

    rows = []
    run_date_naive = run_date.replace(tzinfo=None) if run_date.tzinfo else run_date

    for r in records:
        # Normalize fields
        title = r.title.strip()
        summary = r.summary.strip() if r.summary else ""
        
        # Filter invalid rows (e.g. empty title or empty summary)
        if not title:
            continue

        authors_list = [a.strip() for a in r.authors if a.strip()]
        authors_joined = ", ".join(authors_list) if authors_list else "Unknown"

        categories_list = [c.strip() for c in r.categories if c.strip()]
        categories_joined = ", ".join(categories_list) if categories_list else (r.primary_category or "General CS/AI")

        # Parse date and calculate age_days
        try:
            pub_date = datetime.strptime(r.published, "%Y-%m-%d")
        except ValueError:
            pub_date = run_date_naive

        age_days = max(0, (run_date_naive - pub_date).days)
        summary_chars = len(summary)

        # Build text_for_embedding
        text_for_embedding = f"Title: {title}\nAuthors: {authors_joined}\nCategories: {categories_joined}\nSummary: {summary}"

        rows.append(
            {
                "paper_id": r.paper_id,
                "title": title,
                "summary": summary,
                "authors": r.authors,
                "authors_joined": authors_joined,
                "categories": r.categories,
                "categories_joined": categories_joined,
                "primary_category": r.primary_category or "General CS/AI",
                "published": r.published,
                "updated": r.updated,
                "age_days": age_days,
                "summary_chars": summary_chars,
                "abs_url": r.abs_url,
                "pdf_url": r.pdf_url,
                "comment": r.comment,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Drop duplicates by paper_id or title
    df = df.drop_duplicates(subset=["paper_id"]).drop_duplicates(subset=["title"])

    # Sort by published date descending
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df


def save_clean_data(df: pd.DataFrame, csv_path: str | Path, json_path: str | Path) -> None:
    """Save cleaned DataFrame to CSV and JSON files."""
    import json
    
    csv_path = Path(csv_path)
    json_path = Path(json_path)
    
    # Create directories
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save as CSV
    df.to_csv(csv_path, index=False, encoding="utf-8")
    
    # Prepare JSON format - keep authors and categories as lists
    json_data = []
    for _, row in df.iterrows():
        json_data.append(row.to_dict())
    
    # Save as JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
