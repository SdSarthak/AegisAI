#!/usr/bin/env python3
"""
AegisAI compliance gate.

Reads aegisai.yml, checks each listed AI system's EU AI Act risk_level
via the AegisAI API, and (for systems in AEGISAI_FAIL_ON risk tiers)
verifies every required compliance document exists with status
"generated". Exits non-zero if anything is missing, printing a
GitHub Actions-friendly summary.
"""

import json
import os
import sys

import requests
import yaml

DEFAULT_REQUIRED_DOCS = [
    "technical_documentation",
    "risk_assessment",
    "conformity_declaration",
]


def env(name, default=None, required=False):
    val = os.environ.get(name, default)
    if required and not val:
        print(f"::error::Missing required input/env var: {name}")
        sys.exit(1)
    return val


def load_config(path):
    if not os.path.isfile(path):
        print(f"::error::Config file not found: {path}")
        sys.exit(1)
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    systems = data.get("systems", [])
    if not systems:
        print(f"::error::No `systems` entries found in {path}")
        sys.exit(1)
    return data


def api_get(session, base_url, path, **params):
    resp = session.get(f"{base_url.rstrip('/')}{path}", params=params, timeout=30)
    if resp.status_code == 401:
        print("::error::AegisAI API rejected the token (401). Check the aegisai-token secret.")
        sys.exit(1)
    resp.raise_for_status()
    return resp.json()


def api_get_all(session, base_url, path, **params):
    """Follow cursor-based pagination and return every item across all pages."""
    items = []
    cursor = None
    while True:
        page_params = dict(params)
        if cursor:
            page_params["cursor"] = cursor
        page = api_get(session, base_url, path, **page_params)

        if isinstance(page, list):
            items.extend(page)
            break  # non-paginated endpoint, single page only

        items.extend(page.get("results", page.get("data", [])))
        cursor = page.get("next_cursor")
        if not cursor:
            break
    return items


def main():
    token = env("AEGISAI_TOKEN", required=True)
    base_url = env("AEGISAI_API_URL", "https://api.aegisai.dev/api/v1")
    config_path = env("AEGISAI_CONFIG_PATH", "aegisai.yml")
    fail_on = {t.strip().lower() for t in env("AEGISAI_FAIL_ON", "high,unacceptable").split(",") if t.strip()}

    config = load_config(config_path)
    systems = config["systems"]

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    # Fetch every document once (across all pages), then filter per
    # system in memory (the API lists all documents owned by the token's user).
    all_documents = api_get_all(session, base_url, "/documents")

    results = []
    failures = []

    for entry in systems:
        system_id = entry.get("id")
        label = entry.get("name", f"system {system_id}")
        required_docs = entry.get("required_documents", DEFAULT_REQUIRED_DOCS)

        if system_id is None:
            print(f"::warning::Skipping entry with no `id`: {entry}")
            continue

        system = api_get(session, base_url, f"/ai-systems/{system_id}")
        risk_level = (system.get("risk_level") or "unclassified").lower()

        row = {
            "id": system_id,
            "name": system.get("name", label),
            "risk_level": risk_level,
            "missing_documents": [],
            "status": "ok",
        }

        if risk_level in fail_on:
            existing = {
                d["document_type"]
                for d in all_documents
                if d.get("ai_system_id") == system_id and d.get("status") == "generated"
            }
            missing = [d for d in required_docs if d not in existing]
            if missing:
                row["missing_documents"] = missing
                row["status"] = "fail"
                failures.append(row)

        results.append(row)

    report_path = "aegisai-compliance-report.json"
    with open(report_path, "w") as f:
        json.dump({"fail_on": sorted(fail_on), "results": results}, f, indent=2)

    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"report={report_path}\n")

    print("\nAegisAI Compliance Check")
    print("=" * 40)
    for row in results:
        marker = "FAIL" if row["status"] == "fail" else "OK"
        print(f"[{marker}] {row['name']} (id={row['id']}) - risk_level={row['risk_level']}")
        if row["missing_documents"]:
            print(f"        missing: {', '.join(row['missing_documents'])}")

    if failures:
        print("\n::error::AegisAI compliance check failed for "
              f"{len(failures)} system(s) missing required compliance documents.")
        for row in failures:
            print(f"::error title=AegisAI: {row['name']} is {row['risk_level'].upper()}"
                  f"::Missing documents: {', '.join(row['missing_documents'])}")
        sys.exit(1)

    print("\nAll systems compliant.")


if __name__ == "__main__":
    main()
