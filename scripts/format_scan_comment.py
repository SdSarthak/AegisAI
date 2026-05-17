"""
format_scan_comment.py — Print a human-readable PR comment from guard-scan-report.json.

Called by the 'Comment scan results on PR' step in .github/workflows/guard-scan.yml.
"""
import json
import sys

REPORT_PATH = "guard-scan-report.json"

try:
    with open(REPORT_PATH, "r", encoding="utf-8") as report_file:
        report = json.load(report_file)
except FileNotFoundError:
    print("Guard scan failed before a report could be written.")
    sys.exit(0)

blocked = report.get("blocked", [])
if not blocked:
    print("Guard scan failed, but no blocked prompt details were captured.")
else:
    lines = ["Guard Scan blocked the following prompt files:"]
    for item in blocked:
        lines.append(f"- `{item['file']}`: {item['patterns']}")
    print("\n".join(lines))
