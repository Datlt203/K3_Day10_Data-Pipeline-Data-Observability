from __future__ import annotations

from typing import Any

from core.utils import write_text


def _fmt(value: Any, digits: int = 3) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _quality_lines(quality: dict[str, Any]) -> list[str]:
    lines = [f"- Overall status: **{quality.get('overall_status', 'UNKNOWN')}**", ""]
    lines.append("| Check | Passed | Detail |")
    lines.append("|---|---|---|")
    for check in quality.get("checks", []):
        passed = "✅" if check.get("passed") else "❌"
        lines.append(f"| {check.get('name')} | {passed} | {check.get('detail')} |")
    return lines


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase (data source, RAG metrics, quality, freshness)."""
    lines: list[str] = []
    lines.append("# Phase 1 Baseline Report")
    lines.append("")
    lines.append("## Data Source")
    lines.append(f"- Source: {source_summary.get('source_api')}")
    lines.append(f"- Query: `{source_summary.get('query')}`")
    lines.append(f"- Filter: `{source_summary.get('filter')}`")
    lines.append(f"- Records fetched: {source_summary.get('records_fetched')}")
    lines.append(f"- Records after cleaning: {source_summary.get('records_after_cleaning')}")
    lines.append("")

    lines.append("## RAG Evaluation Metrics")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    for key in ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        if key in metrics:
            lines.append(f"| {key} | {_fmt(metrics[key])} |")
    lines.append("")
    lines.append(f"- Ragas: `{metrics.get('ragas')}`")
    lines.append("")

    lines.append("## Data Quality")
    lines.extend(_quality_lines(quality))
    lines.append("")

    lines.append("## Freshness")
    lines.append(f"- Latest published: {freshness.get('latest_published')}")
    lines.append(f"- Oldest published: {freshness.get('oldest_published')}")
    lines.append(f"- Stale rows: {freshness.get('stale_rows')} / {freshness.get('total_rows')}")
    lines.append(f"- Is fresh: {'✅' if freshness.get('is_fresh') else '❌'}")
    lines.append("")

    write_text(report_path, "\n".join(lines) + "\n")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Viet markdown report so sanh baseline / corrupted / repaired."""
    lines: list[str] = []
    lines.append("# Data Corruption Impact Report")
    lines.append("")
    lines.append("## RAG Metrics Comparison")
    lines.append("| Metric | Baseline | Corrupted | Repaired |")
    lines.append("|---|---|---|---|")
    for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        lines.append(
            f"| {key} | {_fmt(baseline_metrics.get(key))} | {_fmt(corrupted_metrics.get(key))} | "
            f"{_fmt(repaired_metrics.get(key))} |"
        )
    lines.append("")

    lines.append("## Data Quality Comparison")
    lines.append("| State | Overall status |")
    lines.append("|---|---|")
    lines.append(f"| Corrupted | {corrupted_quality.get('overall_status')} |")
    lines.append(f"| Repaired | {repaired_quality.get('overall_status')} |")
    lines.append("")
    lines.append("### Corrupted quality checks")
    lines.extend(_quality_lines(corrupted_quality))
    lines.append("")
    lines.append("### Repaired quality checks")
    lines.extend(_quality_lines(repaired_quality))
    lines.append("")

    lines.append("## Freshness Comparison")
    lines.append("| State | Stale rows | Total rows | Is fresh |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| Corrupted | {corrupted_freshness.get('stale_rows')} | {corrupted_freshness.get('total_rows')} | "
        f"{'✅' if corrupted_freshness.get('is_fresh') else '❌'} |"
    )
    lines.append(
        f"| Repaired | {repaired_freshness.get('stale_rows')} | {repaired_freshness.get('total_rows')} | "
        f"{'✅' if repaired_freshness.get('is_fresh') else '❌'} |"
    )
    lines.append("")

    lines.append("## Conclusion")
    hit_drop = (baseline_metrics.get("retrieval_hit_rate", 0) or 0) - (corrupted_metrics.get("retrieval_hit_rate", 0) or 0)
    hit_recovery = (repaired_metrics.get("retrieval_hit_rate", 0) or 0) - (corrupted_metrics.get("retrieval_hit_rate", 0) or 0)
    lines.append(f"- Corruption changed retrieval_hit_rate by {_fmt(-hit_drop)} versus baseline.")
    lines.append(f"- Repair recovered retrieval_hit_rate by {_fmt(hit_recovery)} versus corrupted.")
    lines.append("")

    write_text(report_path, "\n".join(lines) + "\n")
