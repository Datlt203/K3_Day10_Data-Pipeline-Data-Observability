# Data Corruption Impact Report

## RAG Metrics Comparison
| Metric | Baseline | Corrupted | Repaired |
|---|---|---|---|
| retrieval_hit_rate | 1.000 | 0.667 | 1.000 |
| mean_token_f1 | 1.000 | 0.667 | 1.000 |
| judge_accuracy | 1.000 | 0.667 | 1.000 |
| mean_judge_score | 5 | 3.778 | 5 |

## Data Quality Comparison
| State | Overall status |
|---|---|
| Corrupted | FAIL |
| Repaired | PASS |

### Corrupted quality checks
- Overall status: **FAIL**

| Check | Passed | Detail |
|---|---|---|
| row_count_min | ✅ | 24 rows in dataset |
| paper_id_not_null | ✅ | 0 rows with null paper_id |
| paper_id_unique | ❌ | 2 duplicate paper_id rows |
| title_not_null | ✅ | 0 rows with missing title |
| summary_min_length | ❌ | 4 rows with summary shorter than 20 chars |
| freshness_within_threshold | ❌ | 4 rows older than 180 days |

### Repaired quality checks
- Overall status: **PASS**

| Check | Passed | Detail |
|---|---|---|
| row_count_min | ✅ | 24 rows in dataset |
| paper_id_not_null | ✅ | 0 rows with null paper_id |
| paper_id_unique | ✅ | 0 duplicate paper_id rows |
| title_not_null | ✅ | 0 rows with missing title |
| summary_min_length | ✅ | 0 rows with summary shorter than 20 chars |
| freshness_within_threshold | ✅ | 0 rows older than 180 days |

## Freshness Comparison
| State | Stale rows | Total rows | Is fresh |
|---|---|---|---|
| Corrupted | 4 | 24 | ❌ |
| Repaired | 0 | 24 | ✅ |

## Conclusion
- Corruption changed retrieval_hit_rate by -0.333 versus baseline.
- Repair recovered retrieval_hit_rate by 0.333 versus corrupted.

