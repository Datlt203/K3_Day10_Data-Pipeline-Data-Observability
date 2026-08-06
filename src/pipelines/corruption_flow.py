from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    settings = load_settings()
    run_date = now_utc()
    paths = settings.paths

    if not paths.clean_json.exists() or not paths.baseline_metrics.exists() or not paths.raw_records_json.exists():
        raise RuntimeError(
            "Baseline artifacts missing. Run `script/run_phase1.py` (Phase 1) before the corruption flow."
        )

    # 1. Doc baseline metrics + cleaned baseline dataset.
    baseline_metrics = read_json(paths.baseline_metrics)
    baseline_df = pd.DataFrame(read_json(paths.clean_json))
    print(f"[corruption_flow] Baseline rows: {len(baseline_df)}, "
          f"baseline retrieval_hit_rate={baseline_metrics.get('retrieval_hit_rate')}")

    # 2-3. Tao corrupted dataset va luu artifacts.
    corrupted_df = corrupt_clean_dataframe(baseline_df, paths.corruption_log)
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"[corruption_flow] Corrupted rows: {len(corrupted_df)} -> {paths.corrupted_clean_csv}")

    # 4. Rebuild index tren du lieu loi va evaluate tren test set frozen.
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, embeddings_output_path=paths.corrupted_embeddings_json
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.corrupted_metrics,
        answers_output_path=paths.corrupted_answers,
    )
    print(f"[corruption_flow] Corrupted retrieval_hit_rate={corrupted_bundle.summary['retrieval_hit_rate']:.3f}")

    # 5. Quality checks + freshness tren du lieu loi.
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.quality_dir / "corrupted_freshness_report.json"
    )
    print(f"[corruption_flow] Corrupted quality={corrupted_quality['overall_status']} "
          f"is_fresh={corrupted_freshness['is_fresh']}")

    # 6. Repair: rebuild lai tu raw records da luu (khong fetch lai API).
    raw_records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date)
    write_csv(repaired_df, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f"[corruption_flow] Repaired rows: {len(repaired_df)} -> {paths.repaired_clean_csv}")

    # 7. Rebuild index tren du lieu da sua va evaluate lai.
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, embeddings_output_path=paths.repaired_embeddings_json
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.repaired_metrics,
        answers_output_path=paths.repaired_answers,
    )
    print(f"[corruption_flow] Repaired retrieval_hit_rate={repaired_bundle.summary['retrieval_hit_rate']:.3f}")

    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.quality_dir / "repaired_freshness_report.json"
    )
    print(f"[corruption_flow] Repaired quality={repaired_quality['overall_status']} "
          f"is_fresh={repaired_freshness['is_fresh']}")

    # 9. Bao cao so sanh 3 trang thai.
    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    print(f"[corruption_flow] Comparison report written to {paths.comparison_report}")
    print("[corruption_flow] Done. baseline -> corrupted -> repaired retrieval_hit_rate: "
          f"{baseline_metrics.get('retrieval_hit_rate')} -> "
          f"{corrupted_bundle.summary['retrieval_hit_rate']:.3f} -> "
          f"{repaired_bundle.summary['retrieval_hit_rate']:.3f}")


if __name__ == "__main__":
    main()
