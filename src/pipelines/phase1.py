from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    settings = load_settings()
    run_date = now_utc()
    paths = settings.paths

    # 1-2. Load hoac fetch raw records.
    if paths.raw_records_json.exists() and not settings.refresh_source:
        print(f"[phase1] Loading raw records from {paths.raw_records_json}")
        records = load_raw_records(paths.raw_records_json)
    else:
        print("[phase1] Fetching raw records from Crossref API")
        records = fetch_source_records(settings)
    print(f"[phase1] Raw records: {len(records)}")

    # 3-4. Clean data va luu.
    df = build_clean_dataframe(records, run_date)
    if df.empty:
        raise RuntimeError("Cleaning produced an empty dataframe. Check source filters / cleaning thresholds.")
    write_csv(df, paths.clean_csv)
    write_json(paths.clean_json, df.to_dict(orient="records"))
    print(f"[phase1] Cleaned records: {len(df)} -> {paths.clean_csv}")

    # 5. Build Chroma index.
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=paths.embeddings_json)
    print(f"[phase1] Built index collection '{index.collection_name}' with {len(index.documents)} documents")

    # 6. Tao hoac load frozen evaluation set.
    if paths.eval_testset.exists() and not settings.refresh_test_set:
        print(f"[phase1] Loading existing test set from {paths.eval_testset}")
        test_set = read_json(paths.eval_testset)
    else:
        print("[phase1] Building new frozen test set")
        test_set = build_test_set(df, paths.eval_testset)
    print(f"[phase1] Test set size: {len(test_set)}")

    # 7. Evaluate.
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    print(f"[phase1] retrieval_hit_rate={bundle.summary['retrieval_hit_rate']:.3f} "
          f"mean_token_f1={bundle.summary['mean_token_f1']:.3f}")

    # 8. Data quality + freshness.
    quality = run_data_quality_checks(df, settings, "baseline_quality")
    freshness = build_freshness_report(df, settings, paths.freshness_report)
    print(f"[phase1] quality={quality['overall_status']} is_fresh={freshness['is_fresh']}")

    # 9. Markdown report.
    source_summary = {
        "source_api": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "records_fetched": len(records),
        "records_after_cleaning": len(df),
    }
    generate_phase1_report(paths.baseline_report, source_summary, bundle.summary, quality, freshness)
    print(f"[phase1] Report written to {paths.baseline_report}")

    # 10. Demo agent tren vai sample question (best-effort, khong lam fail pipeline).
    try:
        agent = build_agent(settings, index)
        demo_questions = [item["question"] for item in test_set[:3]]
        demo_answers = [
            {"question": question, "answer": run_agent_question(agent, question)}
            for question in demo_questions
        ]
        write_json(paths.demo_answers, demo_answers)
        print(f"[phase1] Agent demo answers written to {paths.demo_answers}")
    except Exception as exc:  # pragma: no cover
        write_json(paths.demo_answers, {"error": str(exc)})
        print(f"[phase1] Agent demo skipped: {exc}")

    print("[phase1] Baseline pipeline complete.")


if __name__ == "__main__":
    main()
