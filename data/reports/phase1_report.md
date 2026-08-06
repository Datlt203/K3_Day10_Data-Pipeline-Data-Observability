# Phase 1 Baseline Report

## Data Source
- Source: Crossref REST API
- Query: `agentic retrieval augmented generation large language model`
- Filter: `from-pub-date:2026-02-07,has-abstract:true`
- Records fetched: 24
- Records after cleaning: 24

## RAG Evaluation Metrics
| Metric | Value |
|---|---|
| samples | 9 |
| retrieval_hit_rate | 1.000 |
| mean_token_f1 | 1.000 |
| judge_accuracy | 1.000 |
| mean_judge_score | 5 |

- Ragas: `{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}`

## Data Quality
- Overall status: **PASS**

| Check | Passed | Detail |
|---|---|---|
| row_count_min | ✅ | 24 rows in dataset |
| paper_id_not_null | ✅ | 0 rows with null paper_id |
| paper_id_unique | ✅ | 0 duplicate paper_id rows |
| title_not_null | ✅ | 0 rows with missing title |
| summary_min_length | ✅ | 0 rows with summary shorter than 20 chars |
| freshness_within_threshold | ✅ | 0 rows older than 180 days |

## Freshness
- Latest published: 2026-08-01
- Oldest published: 2026-02-12
- Stale rows: 0 / 24
- Is fresh: ✅

