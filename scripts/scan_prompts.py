import glob
import json
import os
import sys

import httpx


def _load_prompt_files() -> list[str]:
    return sorted(glob.glob(".prompts/**/*.txt", recursive=True))


def _scan_prompt_file(client: httpx.Client, base_url: str, headers: dict[str, str], path: str) -> dict:
    with open(path, "r", encoding="utf-8") as prompt_file:
        content = prompt_file.read()

    response = client.post(
        f"{base_url}/api/v1/guard/scan",
        json={"prompt": content},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    return {
        "file": path,
        "decision": result.get("decision", "unknown"),
        "matched_patterns": result.get("matched_patterns", []),
    }


def main() -> int:
    base_url = os.environ["AEGISAI_GUARD_URL"].rstrip("/")
    token = os.environ["AEGISAI_API_TOKEN"]
    report_path = os.environ.get("AEGISAI_GUARD_SCAN_REPORT", "guard-scan-report.json")
    headers = {"Authorization": f"Bearer {token}"}

    prompt_files = _load_prompt_files()
    if not prompt_files:
        print("No .prompts/ files found — skipping.")
        with open(report_path, "w", encoding="utf-8") as report_file:
            json.dump({"status": "skipped", "prompt_files": []}, report_file)
        return 0

    blocked: list[dict] = []
    results: list[dict] = []

    with httpx.Client() as client:
        for path in prompt_files:
            result = _scan_prompt_file(client, base_url, headers, path)
            results.append(result)
            if result["decision"] == "block":
                blocked.append({"file": path, "patterns": result["matched_patterns"]})

    report = {
        "status": "blocked" if blocked else "passed",
        "prompt_files": prompt_files,
        "results": results,
        "blocked": blocked,
    }
    with open(report_path, "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2)

    if blocked:
        print("Guard blocked the following prompt files:")
        for item in blocked:
            print(f"  {item['file']}: {item['patterns']}")
        return 1

    print(f"All {len(prompt_files)} prompt files passed Guard scan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())