import json

with open('guard-scan-report.json', 'r', encoding='utf-8') as f:
    report = json.load(f)

blocked = report.get('blocked', [])
if not blocked:
    print('Guard scan failed, but no blocked prompt details were captured.')
else:
    lines = ['Guard Scan blocked the following prompt files:']
    for item in blocked:
        lines.append(f"- `{item['file']}`: {item['patterns']}")
    print('\n'.join(lines))