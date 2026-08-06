from __future__ import annotations

from datetime import datetime
import re

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

_TAG_RE = re.compile(r"<[^>]+>")
_MIN_SUMMARY_CHARS = 100


def _strip_markup(text: str) -> str:
    return normalize_whitespace(_TAG_RE.sub(" ", text or ""))


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw PaperRecord list thanh DataFrame san sang de embed.

    - Strip the XML/HTML khoi title/summary.
    - Gop authors/categories thanh chuoi.
    - Tinh age_days tu published.
    - Tao text_for_embedding.
    - Drop record khong hop le / duplicate paper_id.
    """
    rows: list[dict] = []

    for record in records:
        title = _strip_markup(record.title)
        summary = _strip_markup(record.summary)
        if not title or not record.paper_id or len(summary) < _MIN_SUMMARY_CHARS:
            continue

        published_dt = _parse_date(record.published)
        if published_dt is None:
            continue
        updated_dt = _parse_date(record.updated) or published_dt

        authors = [normalize_whitespace(a) for a in record.authors if a]
        categories = [normalize_whitespace(c) for c in record.categories if c]
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        primary_category = record.primary_category or (categories[0] if categories else "uncategorized")

        age_days = max(0, (run_date.date() - published_dt.date()).days)
        text_for_embedding = f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"

        rows.append(
            {
                "paper_id": record.paper_id,
                "title": title,
                "summary": summary,
                "summary_chars": len(summary),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "primary_category": primary_category,
                "published": published_dt.date().isoformat(),
                "updated": updated_dt.date().isoformat(),
                "age_days": age_days,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "text_for_embedding": text_for_embedding,
            }
        )

    columns = [
        "paper_id", "title", "summary", "summary_chars", "authors_joined", "categories_joined",
        "primary_category", "published", "updated", "age_days", "abs_url", "pdf_url", "comment",
        "text_for_embedding",
    ]
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return df

    df = df.drop_duplicates(subset="paper_id", keep="first")
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    return df
