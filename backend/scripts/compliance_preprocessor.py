import json


def preprocess_compliance_records(records):
    cleaned_records = []

    for record in records:
        text = record.get("text", "").strip().lower()

        if not text:
            continue

        cleaned_record = {
            "id": record.get("id"),
            "text": text,
            "risk_level": record.get("risk_level", "unknown")
        }

        cleaned_records.append(cleaned_record)

    return cleaned_records


if __name__ == "__main__":
    sample_records = [
        {"id": 1, "text": "  High Risk AI System  ", "risk_level": "high"},
        {"id": 2, "text": " ", "risk_level": "low"},
        {"id": 3, "text": "Biometric Surveillance", "risk_level": "critical"},
    ]

    processed = preprocess_compliance_records(sample_records)

    print(json.dumps(processed, indent=2))