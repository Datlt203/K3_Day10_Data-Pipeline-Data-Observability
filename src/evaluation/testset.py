from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

_MIN_DOCUMENTS = 3
_MAX_PAPERS_SAMPLED = 3

# Cac cau hoi duoc phrase de khop voi pattern detection trong retrieval/qa.py::_extract_answer
# (vd "who authored", "when was", "what categories") va deu wrap title trong dau nhay don
# de kich hoat exact-match lookup (`index.lookup`) trong qa.py.
_QUESTION_BUILDERS = (
    ("summary", lambda title: f"What is the paper titled '{title}' about?", lambda row: first_sentence(row["summary"])),
    ("authors", lambda title: f"Who authored the paper titled '{title}'?", lambda row: row["authors_joined"]),
    ("date", lambda title: f"When was the paper titled '{title}' published?", lambda row: row["published"]),
    ("categories", lambda title: f"What categories does the paper titled '{title}' belong to?", lambda row: row["categories_joined"]),
)


def _select_paper_indices(total: int, sample_size: int) -> list[int]:
    if total <= sample_size:
        return list(range(total))
    step = total / sample_size
    indices = sorted({int(i * step) for i in range(sample_size)})
    while len(indices) < sample_size:
        for candidate in range(total):
            if candidate not in indices:
                indices.append(candidate)
                break
        indices = sorted(set(indices))
    return indices


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao frozen evaluation set tu cleaned dataframe."""
    if df is None or len(df) < _MIN_DOCUMENTS:
        found = 0 if df is None else len(df)
        raise ValueError(
            f"Need at least {_MIN_DOCUMENTS} cleaned papers to build a test set, found {found}."
        )

    sample_size = min(len(df), _MAX_PAPERS_SAMPLED)
    selected_indices = _select_paper_indices(len(df), sample_size)

    samples: list[dict[str, Any]] = []
    next_id = 1
    for idx in selected_indices:
        row = df.iloc[idx]
        title = row["title"]
        for question_type, question_fn, ground_truth_fn in _QUESTION_BUILDERS:
            ground_truth = ground_truth_fn(row)
            if not ground_truth:
                continue
            samples.append(
                {
                    "id": f"q{next_id}",
                    "question_type": question_type,
                    "question": question_fn(title),
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [row["paper_id"]],
                }
            )
            next_id += 1

    write_json(output_path, samples)
    return samples
