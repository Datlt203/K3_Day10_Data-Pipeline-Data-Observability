from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json

_MIN_SUMMARY_CHARS_CHECK = 20


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay bo data quality checks (completeness, uniqueness, freshness) va luu report."""
    total_rows = len(df)
    checks: list[dict[str, Any]] = []

    checks.append({
        "name": "row_count_min",
        "passed": total_rows >= 1,
        "detail": f"{total_rows} rows in dataset",
    })

    paper_id_null = int(df["paper_id"].isna().sum()) if total_rows else 0
    checks.append({
        "name": "paper_id_not_null",
        "passed": paper_id_null == 0,
        "detail": f"{paper_id_null} rows with null paper_id",
    })

    duplicate_ids = int(df["paper_id"].duplicated().sum()) if total_rows else 0
    checks.append({
        "name": "paper_id_unique",
        "passed": duplicate_ids == 0,
        "detail": f"{duplicate_ids} duplicate paper_id rows",
    })

    title_missing = int((df["title"].isna() | (df["title"].astype(str).str.strip() == "")).sum()) if total_rows else 0
    checks.append({
        "name": "title_not_null",
        "passed": title_missing == 0,
        "detail": f"{title_missing} rows with missing title",
    })

    short_summary = int((df["summary"].astype(str).str.len() < _MIN_SUMMARY_CHARS_CHECK).sum()) if total_rows else 0
    checks.append({
        "name": "summary_min_length",
        "passed": short_summary == 0,
        "detail": f"{short_summary} rows with summary shorter than {_MIN_SUMMARY_CHARS_CHECK} chars",
    })

    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if total_rows else 0
    checks.append({
        "name": "freshness_within_threshold",
        "passed": stale_rows == 0,
        "detail": f"{stale_rows} rows older than {settings.freshness_threshold_days} days",
    })

    overall_status = "PASS" if all(check["passed"] for check in checks) else "FAIL"
    result = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "total_rows": total_rows,
        "overall_status": overall_status,
        "checks": checks,
    }

    report_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(report_path, result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report: latest/oldest published, stale rows, is_fresh."""
    total_rows = len(df)
    if total_rows == 0:
        payload = {
            "generated_at": now_utc().isoformat(),
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": False,
        }
        write_json(report_path, payload)
        return payload

    published_dates = pd.to_datetime(df["published"])
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())

    payload = {
        "generated_at": now_utc().isoformat(),
        "latest_published": published_dates.max().date().isoformat(),
        "oldest_published": published_dates.min().date().isoformat(),
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_rows / total_rows,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": stale_rows == 0,
    }
    write_json(report_path, payload)
    return payload
