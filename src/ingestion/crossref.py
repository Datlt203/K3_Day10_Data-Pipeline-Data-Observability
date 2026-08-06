from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.config import Settings


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


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API response items into a list of PaperRecord."""
    message = payload.get("message", {})
    items = message.get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        # Extract title
        title_list = item.get("title", [])
        title = title_list[0].strip() if title_list else ""
        if not title:
            continue
        # Clean XML tags from title if present
        import re
        title = re.sub(r"<[^>]+>", "", title).strip()

        # Extract summary / abstract
        summary = item.get("abstract", "") or ""
        # Clean JATS XML tags if present in Crossref abstract
        summary = re.sub(r"<[^>]+>", "", summary).strip()


        # Extract authors
        authors = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            name = f"{given} {family}".strip() or family or given
            if name:
                authors.append(name)

        # Extract subjects / categories
        categories = item.get("subject", [])
        primary_category = categories[0] if categories else "General CS/AI"

        # Extract publication / updated dates
        published_parts = item.get("published-print", {}).get("date-parts", []) or item.get("published-online", {}).get("date-parts", []) or item.get("created", {}).get("date-parts", [])
        if published_parts and published_parts[0]:
            dp = published_parts[0]
            year = dp[0]
            month = dp[1] if len(dp) > 1 else 1
            day = dp[2] if len(dp) > 2 else 1
            published = f"{year:04d}-{month:02d}-{day:02d}"
        else:
            published = "2024-01-01"

        updated = published

        abs_url = item.get("URL", f"https://doi.org/{doi}")
        pdf_url = ""
        for link in item.get("link", []):
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL", "")
                break

        paper_id = doi.replace("/", "_").replace(".", "_")

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment="",
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch records from Crossref API, save raw response, parse and save records snapshot."""
    import json
    import time
    import requests

    params = {
        "query": settings.source_query,
        "rows": settings.max_results,
    }
    if settings.source_filter:
        params["filter"] = settings.source_filter

    headers = {
        "User-Agent": "DataPipelineLab/1.0 (mailto:student@example.com)"
    }

    url = "https://api.crossref.org/works"
    response_payload = None

    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                response_payload = resp.json()
                break
            elif resp.status_code in (429, 503):
                time.sleep(2 * (attempt + 1))
            else:
                resp.raise_for_status()
        except Exception as e:
            if attempt == 2:
                raise e
            time.sleep(2)

    if not response_payload:
        raise RuntimeError("Failed to fetch data from Crossref API.")

    # Save raw API response
    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
        json.dump(response_payload, f, ensure_ascii=False, indent=2)

    # Parse payload
    records = parse_crossref_payload(response_payload)

    # Save parsed raw records
    settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
    records_dict_list = [
        {
            "paper_id": r.paper_id,
            "title": r.title,
            "summary": r.summary,
            "authors": r.authors,
            "categories": r.categories,
            "primary_category": r.primary_category,
            "published": r.published,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
        }
        for r in records
    ]
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump(records_dict_list, f, ensure_ascii=False, indent=2)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read JSON snapshot and map into list of PaperRecord."""
    import json
    if not path.exists():
        raise FileNotFoundError(f"Raw records file not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = []
    for d in data:
        records.append(
            PaperRecord(
                paper_id=d["paper_id"],
                title=d["title"],
                summary=d["summary"],
                authors=d.get("authors", []),
                categories=d.get("categories", []),
                primary_category=d.get("primary_category", ""),
                published=d.get("published", ""),
                updated=d.get("updated", ""),
                abs_url=d.get("abs_url", ""),
                pdf_url=d.get("pdf_url", ""),
                comment=d.get("comment", ""),
            )
        )
    return records

