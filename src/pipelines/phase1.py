from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from core.config import load_settings

logger = logging.getLogger(__name__)


def main() -> None:
    """Baseline pipeline end-to-end: fetch raw → clean → index → evaluate.
    
    Pseudo-code:
    1. Load settings.
    2. Load or fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Create or load evaluation set.
    7. Evaluate.
    8. Run quality checks and freshness report.
    9. Create markdown report.
    10. Demo agent on sample questions.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.info("=" * 80)
    logger.info("PHASE 1: BASELINE PIPELINE")
    logger.info("=" * 80)
    
    # Step 0: Load settings
    logger.info("[Step 0] Loading settings...")
    settings = load_settings()
    logger.info(f"Project dir: {settings.paths.project_dir}")
    logger.info(f"LLM Provider: {settings.llm_provider} / {settings.model_name}")
    
    run_date = datetime.now(UTC)
    logger.info(f"Run date: {run_date.isoformat()}")
    
    # Step 1: Load or fetch raw records
    logger.info("[Step 1] Loading/fetching raw records...")
    try:
        from ingestion.crossref import fetch_source_records, load_raw_records
        
        if settings.refresh_source or not settings.paths.raw_records_json.exists():
            logger.info("Fetching data from Crossref API...")
            raw_records = fetch_source_records(settings)
            logger.info(f"Fetched {len(raw_records)} records from Crossref")
        else:
            logger.info("Loading raw records from cache...")
            raw_records = load_raw_records(settings.paths.raw_records_json)
            logger.info(f"Loaded {len(raw_records)} records from cache")
    except NotImplementedError as e:
        logger.error(f"Crossref ingestion not fully implemented: {e}")
        return
    except Exception as e:
        logger.error(f"Failed to load raw records: {e}")
        return
    
    # Step 2: Clean data
    logger.info("[Step 2] Cleaning data...")
    try:
        from ingestion.cleaning import build_clean_dataframe, save_clean_data
        
        df_clean = build_clean_dataframe(raw_records, run_date)
        logger.info(f"Cleaned data: {len(df_clean)} valid records (from {len(raw_records)} raw)")
        
        if df_clean.empty:
            logger.error("No valid records after cleaning. Stopping.")
            return
        
        # Step 3: Save clean CSV/JSON
        logger.info("[Step 3] Saving cleaned data...")
        save_clean_data(
            df_clean,
            csv_path=settings.paths.clean_csv,
            json_path=settings.paths.clean_json
        )
        logger.info(f"Saved cleaned data to {settings.paths.clean_csv}")
        logger.info(f"Saved cleaned data to {settings.paths.clean_json}")
        
    except NotImplementedError as e:
        logger.error(f"Cleaning module not fully implemented: {e}")
        return
    except Exception as e:
        logger.error(f"Failed to clean data: {e}")
        return
    
    # Step 4: Build Chroma index
    logger.info("[Step 4] Building ChromaDB vector store...")
    try:
        from retrieval.embeddings import compute_embeddings, save_embeddings_manifest
        from retrieval.index import build_index
        
        # Compute embeddings
        logger.info("Computing embeddings (sentence-transformers)...")
        embeddings_dict = compute_embeddings(
            records=df_clean.to_dict("records"),
            collection_name=settings.baseline_collection_name
        )
        
        # Save embeddings manifest
        save_embeddings_manifest(
            embeddings_dict,
            settings.paths.embeddings_json
        )
        logger.info(f"Saved embeddings manifest to {settings.paths.embeddings_json}")
        
        # Build index
        logger.info("Building Chroma index...")
        build_index(
            records=df_clean.to_dict("records"),
            embeddings_dict=embeddings_dict,
            collection_name=settings.baseline_collection_name,
            chroma_dir=settings.paths.chroma_dir,
        )
        logger.info(f"ChromaDB index built at {settings.paths.chroma_dir}")
        
    except NotImplementedError as e:
        logger.warning(f"Retrieval/embedding module not ready: {e}. Skipping indexing for now.")
    except Exception as e:
        logger.warning(f"Failed to build index: {e}. Continuing...")
    
    # Step 5: Create or load evaluation set
    logger.info("[Step 5] Creating/loading evaluation test set...")
    try:
        from evaluation.testset import create_testset
        
        if settings.refresh_test_set or not settings.paths.eval_testset.exists():
            logger.info("Creating new test set...")
            testset = create_testset(
                records=df_clean.to_dict("records"),
                num_questions=min(10, len(df_clean)),
            )
            
            # Save testset
            settings.paths.eval_testset.parent.mkdir(parents=True, exist_ok=True)
            with open(settings.paths.eval_testset, "w", encoding="utf-8") as f:
                json.dump(testset, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Created and saved {len(testset)} test questions to {settings.paths.eval_testset}")
        else:
            logger.info("Loading test set from cache...")
            with open(settings.paths.eval_testset, "r", encoding="utf-8") as f:
                testset = json.load(f)
            logger.info(f"Loaded {len(testset)} test questions")
    except NotImplementedError as e:
        logger.warning(f"Test set creation not ready: {e}. Skipping test set generation.")
        testset = []
    except Exception as e:
        logger.warning(f"Failed to create test set: {e}. Continuing...")
        testset = []
    
    # Step 6: Evaluate (if agent and metrics are ready)
    logger.info("[Step 6] Evaluating RAG agent...")
    try:
        from retrieval.agent import run_agent
        from evaluation.metrics import compute_metrics
        
        logger.info("Running evaluation on test set...")
        answers = []
        for i, test_sample in enumerate(testset):
            try:
                logger.info(f"  Question {i+1}/{len(testset)}: {test_sample.get('question', '')[:50]}...")
                answer = run_agent(
                    question=test_sample["question"],
                    chroma_dir=settings.paths.chroma_dir,
                    collection_name=settings.baseline_collection_name,
                    llm_provider=settings.llm_provider,
                )
                answers.append({
                    "question": test_sample["question"],
                    "answer": answer,
                    "ground_truth": test_sample.get("ground_truth", ""),
                    "ground_truth_doc_ids": test_sample.get("ground_truth_doc_ids", []),
                })
            except Exception as e:
                logger.warning(f"  Failed to process question {i+1}: {e}")
        
        if answers:
            # Save answers
            settings.paths.baseline_answers.parent.mkdir(parents=True, exist_ok=True)
            with open(settings.paths.baseline_answers, "w", encoding="utf-8") as f:
                json.dump(answers, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(answers)} answers to {settings.paths.baseline_answers}")
            
            # Compute metrics
            logger.info("Computing metrics...")
            metrics = compute_metrics(
                test_samples=testset,
                answers=answers
            )
            
            # Save metrics
            settings.paths.baseline_metrics.parent.mkdir(parents=True, exist_ok=True)
            with open(settings.paths.baseline_metrics, "w", encoding="utf-8") as f:
                json.dump(metrics, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved baseline metrics to {settings.paths.baseline_metrics}")
            logger.info(f"Metrics: {metrics}")
        
    except NotImplementedError as e:
        logger.warning(f"Agent/metrics module not ready: {e}. Skipping evaluation.")
    except Exception as e:
        logger.warning(f"Failed to evaluate: {e}. Continuing...")
    
    # Step 7: Data quality checks
    logger.info("[Step 7] Running data quality checks...")
    try:
        from observability.quality import run_data_quality_checks
        
        quality_results = run_data_quality_checks(
            df=df_clean,
            output_dir=settings.paths.quality_dir
        )
        logger.info(f"Quality checks completed. Results: {quality_results}")
        
    except NotImplementedError as e:
        logger.warning(f"Quality module not ready: {e}.")
    except Exception as e:
        logger.warning(f"Failed to run quality checks: {e}.")
    
    # Step 8: Create markdown report
    logger.info("[Step 8] Creating baseline report...")
    try:
        from observability.reporting import create_baseline_report
        
        create_baseline_report(
            df_clean=df_clean,
            metrics_file=settings.paths.baseline_metrics,
            report_path=settings.paths.baseline_report,
        )
        logger.info(f"Baseline report saved to {settings.paths.baseline_report}")
        
    except NotImplementedError as e:
        logger.warning(f"Reporting module not ready: {e}.")
    except Exception as e:
        logger.warning(f"Failed to create report: {e}.")
    
    logger.info("=" * 80)
    logger.info("PHASE 1 COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Clean data: {settings.paths.clean_csv}")
    logger.info(f"Results: {settings.paths.baseline_metrics}")
    logger.info(f"Report: {settings.paths.baseline_report}")

