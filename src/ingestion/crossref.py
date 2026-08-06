from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import random
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"
_RETRYABLE_STATUS_CODES = {429, 503}
_MAX_RETRIES = 5
_BACKOFF_BASE_SECONDS = 1.5
_USER_AGENT = "day10-data-observability-lab/0.1 (mailto:student@example.com)"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _format_date_parts(parts: list[int] | None) -> str:
    if not parts:
        return ""
    year = parts[0] if len(parts) > 0 else None
    if not year:
        return ""
    month = parts[1] if len(parts) > 1 and parts[1] else 1
    day = parts[2] if len(parts) > 2 and parts[2] else 1
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return date(year, 1, 1).isoformat()


def _extract_date(item: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        block = item.get(key)
        if block and block.get("date-parts"):
            formatted = _format_date_parts(block["date-parts"][0])
            if formatted:
                return formatted
    return ""


def _extract_authors(item: dict) -> list[str]:
    authors: list[str] = []
    for author in item.get("author") or []:
        given = (author.get("given") or "").strip()
        family = (author.get("family") or "").strip()
        name = normalize_whitespace(f"{given} {family}")
        if not name:
            name = normalize_whitespace(author.get("name") or "")
        if name:
            authors.append(name)
    return authors


def _extract_pdf_url(item: dict) -> str:
    for link in item.get("link") or []:
        content_type = (link.get("content-type") or "").lower()
        if "pdf" in content_type:
            return link.get("URL", "") or ""
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref `works` payload thanh list PaperRecord.

    Ghi chu: cac the XML/HTML (vd `<jats:p>`) trong abstract CHUA duoc strip o day.
    Buoc cleaning (`ingestion/cleaning.py`) se chiu trach nhiem strip va chuan hoa text.
    """
    items = ((payload or {}).get("message") or {}).get("items") or []
    records: list[PaperRecord] = []

    for item in items:
        doi = (item.get("DOI") or "").strip()
        titles = item.get("title") or []
        title = normalize_whitespace(titles[0]) if titles else ""
        abstract = item.get("abstract") or ""

        # Loc chi lay ban ghi co day du DOI (paper_id), title va abstract.
        if not doi or not title or not abstract.strip():
            continue

        categories = [normalize_whitespace(c) for c in (item.get("subject") or []) if c]
        primary_category = categories[0] if categories else "uncategorized"

        published = _extract_date(item, ("published-print", "published-online", "published", "issued", "created"))
        updated = _extract_date(item, ("indexed", "deposited")) or published
        if not published:
            continue

        container_titles = item.get("container-title") or []
        comment = normalize_whitespace(container_titles[0]) if container_titles else ""

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=abstract,
                authors=_extract_authors(item),
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=item.get("URL", "") or "",
                pdf_url=_extract_pdf_url(item),
                comment=comment,
            )
        )

    return records


def _get_with_retry(url: str, params: dict) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = requests.get(url, params=params, headers={"User-Agent": _USER_AGENT}, timeout=30)
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(_BACKOFF_BASE_SECONDS * (2**attempt) + random.uniform(0, 0.5))
            continue

        if response.status_code in _RETRYABLE_STATUS_CODES:
            retry_after = response.headers.get("Retry-After")
            wait_seconds = float(retry_after) if retry_after else _BACKOFF_BASE_SECONDS * (2**attempt)
            time.sleep(wait_seconds + random.uniform(0, 0.5))
            continue

        response.raise_for_status()
        return response

    raise RuntimeError(f"Crossref request failed after {_MAX_RETRIES} retries.") from last_exc


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref API, luu raw response + raw records, tra ve list PaperRecord."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    response = _get_with_retry(CROSSREF_API_URL, params)
    payload = response.json()
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot (list[dict]) va map thanh list[PaperRecord]."""
    payload = read_json(path)
    return [PaperRecord(**item) for item in payload]
