#!/usr/bin/env python3
"""Build the RD (Real Data) Mark 1 World Bank project sample.

The script intentionally uses only Python's standard library so the data spike is
easy to rerun on a clean machine.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECTS_API = "https://search.worldbank.org/api/v2/projects"
COUNTRIES_API = "https://api.worldbank.org/v2/country"
WORLD_BANK_COORDS = [-77.0369, 38.9072]
COUNTRY_CODE_ALIASES = {"ZR": "CD"}  # Legacy World Bank code for DR Congo.

SECTOR_KEYWORDS = {
    "Energy & Extractives": (
        "energy", "electric", "power", "grid", "renewable", "solar",
        "wind farm", "hydro", "geothermal", "battery", "transmission",
        "natural gas", "oil and gas", "mining", "extractive",
    ),
    "Transport Infrastructure": (
        "transport", "road", "railway", "railroad", "metro", "port",
        "airport", "highway", "freight", "logistics", "mobility", "bridge",
    ),
    "Water Infrastructure": (
        "water", "sanitation", "irrigation", "wastewater", "sewer",
        "drainage", "flood", "hydraulic",
    ),
    "Urban Development": (
        "urban", "city", "cities", "municipal", "housing", "settlement",
        "metropolitan",
    ),
}


def fetch_json(url: str, attempts: int = 3) -> Any:
    """Fetch JSON with a small retry budget for transient public-API failures."""
    request = Request(url, headers={"User-Agent": "capex-map-rd-mark-1/1.0"})
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=45) as response:
                return json.load(response)
        except Exception as error:  # Network and malformed-response errors.
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not fetch {url}: {last_error}") from last_error


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def clean_text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("cdata!", "")
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_amount(record: dict[str, Any]) -> tuple[int, str]:
    """Return the best available project amount in USD and its source field."""
    for field in ("totalamt", "totalcommamt", "lendprojectcost"):
        raw = record.get(field)
        if raw not in (None, ""):
            try:
                amount = int(round(float(str(raw).replace(",", ""))))
                if amount > 0:
                    return amount, field
            except ValueError:
                pass

    # The API documents current commitment in USD millions.
    raw_millions = record.get("curr_total_commitment")
    try:
        amount = int(round(float(str(raw_millions).replace(",", "")) * 1_000_000))
        if amount > 0:
            return amount, "curr_total_commitment_usd_millions"
    except (TypeError, ValueError):
        pass
    return 0, "unavailable"


def contains_keyword(text: str, keyword: str) -> bool:
    """Match complete words/phrases, avoiding city/capacity and port/support."""
    phrase = re.escape(keyword.strip()).replace(r"\ ", r"\s+")
    return re.search(rf"(?<![a-z]){phrase}(?![a-z])", text) is not None


def classify_sector(record: dict[str, Any]) -> tuple[str | None, str]:
    explicit_names: list[str] = []
    for field in ("sector1", "sector2", "sector3", "sector4", "sector5"):
        sector = record.get(field)
        if isinstance(sector, dict):
            name = clean_text(sector.get("Name"))
            if name:
                explicit_names.append(name)

    explicit_text = " ".join(explicit_names).lower()
    project_name = clean_text(record.get("project_name")).lower()

    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(contains_keyword(explicit_text, keyword) for keyword in keywords):
            return sector, "world_bank_sector"
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(contains_keyword(project_name, keyword) for keyword in keywords):
            return sector, "project_name_inference"
    return None, "unclassified"


def country_lookup(payload: Any | None = None) -> tuple[dict[str, dict[str, Any]], Any]:
    if payload is None:
        payload = fetch_json(
            f"{COUNTRIES_API}?{urlencode({'format': 'json', 'per_page': 400})}"
        )
    rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = clean_text(row.get("iso2Code")).upper()
        try:
            coords = [float(row["longitude"]), float(row["latitude"])]
        except (KeyError, TypeError, ValueError):
            coords = None
        if code:
            lookup[code] = {"name": clean_text(row.get("name")), "coords": coords}
    return lookup, payload


def project_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    projects = payload.get("projects", {})
    if isinstance(projects, dict):
        return [row for row in projects.values() if isinstance(row, dict)]
    if isinstance(projects, list):
        return [row for row in projects if isinstance(row, dict)]
    return []


def fetch_project_pages(
    base_params: dict[str, Any], row_limit: int
) -> tuple[dict[str, Any], str]:
    """Fetch all requested rows despite the API's effective 1,000-row page cap."""
    page_size = 1_000
    offset = 0
    total = 0
    projects: dict[str, dict[str, Any]] = {}
    source_url = f"{PROJECTS_API}?{urlencode(base_params)}"

    while offset < row_limit:
        params = {**base_params, "rows": min(page_size, row_limit - offset), "os": offset}
        payload = fetch_json(f"{PROJECTS_API}?{urlencode(params)}")
        rows = project_rows(payload)
        try:
            total = int(payload.get("total", len(rows)))
        except (TypeError, ValueError):
            total = len(rows)
        for row in rows:
            project_id = clean_text(row.get("id"))
            if project_id:
                projects[project_id] = row
        if not rows or len(projects) >= total:
            break
        offset += len(rows)

    raw_payload = {
        "retrieval": {
            "source_url": source_url,
            "reported_total": total,
            "retrieved": len(projects),
            "page_size": page_size,
        },
        "projects": projects,
    }
    return raw_payload, source_url


def project_year(record: dict[str, Any]) -> int | None:
    match = re.search(r"(19|20)\d{2}", clean_text(record.get("boardapprovaldate")))
    return int(match.group(0)) if match else None


def normalize_project(
    record: dict[str, Any], countries: dict[str, dict[str, Any]], generated_at: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    amount, amount_source = parse_amount(record)
    sector, sector_source = classify_sector(record)
    codes = [clean_text(code).upper() for code in as_list(record.get("countrycode"))]
    codes = [code for code in codes if code]
    country_names = [clean_text(name) for name in as_list(record.get("countryname"))]
    country_names = [name for name in country_names if name]

    primary_code = next((code for code in codes if code in countries), codes[0] if codes else "")
    lookup_code = COUNTRY_CODE_ALIASES.get(primary_code, primary_code)
    country = countries.get(lookup_code, {})
    primary_name = clean_text(record.get("countryshortname")) or country.get("name", "")
    if not primary_name and country_names:
        primary_name = country_names[0]

    sources = [clean_text(source) for source in as_list(record.get("source"))]
    sources = [source for source in sources if source]
    project_id = clean_text(record.get("id"))
    source_url = clean_text(record.get("url")) or (
        f"https://projects.worldbank.org/en/projects-operations/project-detail/{project_id}"
    )
    year = project_year(record)

    normalized = {
        "id": project_id,
        "name": clean_text(record.get("project_name")),
        "sector": sector,
        "sector_classification": sector_source,
        "amount_usd": amount,
        "amount_usd_b": round(amount / 1_000_000_000, 3),
        "amount_source": amount_source,
        "year": year,
        "approval_date": clean_text(record.get("boardapprovaldate")),
        "status": clean_text(record.get("status") or record.get("projectstatusdisplay")),
        "lending_instrument": clean_text(record.get("lendinginstr")),
        "recipient": {
            "country": primary_name,
            "country_code": primary_code,
            "coords": country.get("coords"),
            "all_country_codes": codes,
            "all_country_names": country_names,
        },
        "funders": [
            {
                "entity": "World Bank Group",
                "instruments": sources,
                "coords": WORLD_BANK_COORDS,
                "amount_usd_b": round(amount / 1_000_000_000, 3),
            }
        ],
        "source": {
            "provider": "World Bank Projects & Operations",
            "project_id": project_id,
            "url": source_url,
        },
        "last_updated": clean_text(record.get("p2a_updated_date")),
        "observed_at": generated_at,
    }
    audit = {
        "has_amount": amount > 0,
        "has_sector": sector is not None,
        "has_coords": country.get("coords") is not None,
        "multi_country": len(codes) > 1,
        "policy_financing": any(
            phrase in (
                clean_text(record.get("lendinginstr")) + " "
                + clean_text(record.get("project_name"))
            ).lower()
            for phrase in (
                "development policy",
                "policy financing",
                "policy loan",
                "policy operation",
                " dpl",
                " dpf",
                " dpo",
            )
        ),
        "year": year,
    }
    return normalized, audit


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def audit_markdown(metadata: dict[str, Any], projects: list[dict[str, Any]]) -> str:
    sector_counts = Counter(project["sector"] for project in projects)
    country_counts = Counter(project["recipient"]["country"] or "Unknown" for project in projects)
    lines = [
        "# RD (Real Data) — Mark 1 audit",
        "",
        f"Generated: `{metadata['generated_at']}`",
        "",
        "## Scope",
        "",
        "This is a data spike, not a production dataset. It tests whether public World Bank project data can be converted into map-ready capital-flow records without changing the dashboard UI.",
        "",
        "## Filters",
        "",
        f"- Status: `{metadata['filters']['status']}`",
        f"- Approval years: `{metadata['filters']['from_year']}–{metadata['filters']['to_year']}`",
        f"- Minimum project amount: `${metadata['filters']['min_amount_usd']:,}`",
        "- Target sectors: energy, transport, water, and urban development",
        "",
        "## Quality checks",
        "",
        f"- API projects fetched: **{metadata['counts']['fetched']:,}**",
        f"- Projects with no usable amount: **{metadata['counts']['missing_amount']:,}**",
        f"- Projects below the amount threshold: **{metadata['counts']['below_amount_threshold']:,}**",
        f"- Projects not classified into a target sector: **{metadata['counts']['unclassified_sector']:,}**",
        f"- Selected projects: **{metadata['counts']['selected']:,}**",
        f"- Selected projects missing recipient coordinates: **{metadata['counts']['selected_missing_coords']:,}**",
        f"- Selected multi-country projects: **{metadata['counts']['selected_multi_country']:,}**",
        f"- Selected projects classified from project-name keywords: **{metadata['counts']['selected_name_inference']:,}**",
        f"- Selected policy-financing operations (not necessarily physical assets): **{metadata['counts']['selected_policy_financing']:,}**",
        "",
        "## Selected sample",
        "",
        f"Total represented amount: **${metadata['selected_amount_usd'] / 1_000_000_000:,.1f}B**",
        "",
        "### By sector",
        "",
    ]
    for sector, count in sector_counts.most_common():
        lines.append(f"- {sector}: **{count}**")
    lines.extend(("", "### Top recipient countries", ""))
    for country, count in country_counts.most_common(10):
        lines.append(f"- {country}: **{count}**")
    lines.extend(("", "### Largest projects", ""))
    for project in projects[:10]:
        lines.append(
            f"- **{project['name']}** — {project['recipient']['country'] or 'Unknown'}, "
            f"{project['sector']}, ${project['amount_usd_b']:.3f}B "
            f"([{project['id']}]({project['source']['url']}))"
        )
    lines.extend(
        (
            "",
            "## Known limitations",
            "",
            "- The Projects API frequently leaves its explicit sector fields blank. RD Mark 1 therefore uses transparent whole-word rules on project names when necessary; abstracts do not control classification.",
            "- Project amount fields describe project financing or commitments; they are not equivalent to actual year-by-year cash disbursements.",
            "- The World Bank country endpoint supplies a representative country point, not a project-site location.",
            "- Multi-country projects retain all recipient codes but use one primary coordinate for this first map-ready schema.",
            "- This source covers World Bank projects only; it does not represent all global infrastructure investment.",
            "",
            "## Mark 2 decision gate",
            "",
            "Use these records in the dashboard only after reviewing the keyword classifications and deciding how the UI should disclose estimated sectors, amounts, and country-level coordinates.",
            "",
        )
    )
    return "\n".join(lines)


def main() -> int:
    now_year = datetime.now(timezone.utc).year
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-year", type=int, default=now_year - 5)
    parser.add_argument("--to-year", type=int, default=now_year)
    parser.add_argument("--min-amount-usd", type=int, default=500_000_000)
    parser.add_argument("--rows", type=int, default=10_000)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Rebuild normalized files from data/raw/worldbank-projects.json without network access.",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    query_params = {
        "format": "json",
        "status_exact": "Active",
        "frmYear": args.from_year,
        "toYear": args.to_year,
    }
    raw_path = root / "data" / "raw" / "worldbank-projects.json"
    countries_path = root / "data" / "raw" / "worldbank-countries.json"
    if args.use_cache:
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        countries_payload = json.loads(countries_path.read_text(encoding="utf-8"))
        source_url = payload.get("retrieval", {}).get(
            "source_url", f"{PROJECTS_API}?{urlencode(query_params)}"
        )
    else:
        payload, source_url = fetch_project_pages(query_params, args.rows)
        countries_payload = None
    rows = project_rows(payload)
    countries, countries_payload = country_lookup(countries_payload)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    normalized_rows: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    for row in rows:
        normalized, audit = normalize_project(row, countries, generated_at)
        normalized_rows.append(normalized)
        audits.append(audit)

    selected = [
        project
        for project in normalized_rows
        if project["amount_usd"] >= args.min_amount_usd and project["sector"] is not None
    ]
    selected.sort(key=lambda project: (-project["amount_usd"], project["id"]))
    selected_ids = {project["id"] for project in selected}
    selected_audits = [
        audit for project, audit in zip(normalized_rows, audits) if project["id"] in selected_ids
    ]

    counts = {
        "fetched": len(rows),
        "missing_amount": sum(not audit["has_amount"] for audit in audits),
        "below_amount_threshold": sum(
            project["amount_usd"] < args.min_amount_usd for project in normalized_rows
        ),
        "unclassified_sector": sum(not audit["has_sector"] for audit in audits),
        "selected": len(selected),
        "selected_missing_coords": sum(not audit["has_coords"] for audit in selected_audits),
        "selected_multi_country": sum(audit["multi_country"] for audit in selected_audits),
        "selected_name_inference": sum(
            project["sector_classification"] == "project_name_inference" for project in selected
        ),
        "selected_policy_financing": sum(audit["policy_financing"] for audit in selected_audits),
    }
    metadata = {
        "schema_version": "rd-mark-1",
        "generated_at": generated_at,
        "source_url": source_url,
        "filters": {
            "status": "Active",
            "from_year": args.from_year,
            "to_year": args.to_year,
            "min_amount_usd": args.min_amount_usd,
            "target_sectors": list(SECTOR_KEYWORDS),
        },
        "counts": counts,
        "selected_amount_usd": sum(project["amount_usd"] for project in selected),
    }

    write_json(root / "data" / "raw" / "worldbank-projects.json", payload)
    write_json(root / "data" / "raw" / "worldbank-countries.json", countries_payload)
    write_json(root / "data" / "projects.json", selected)
    write_json(root / "data" / "rd-mark-1-metadata.json", metadata)
    report_path = root / "reports" / "rd-mark-1-audit.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(audit_markdown(metadata, selected), encoding="utf-8")

    print(json.dumps(metadata, indent=2))
    if not selected:
        print("No projects passed the current filters.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
