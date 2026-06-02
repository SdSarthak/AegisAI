def sanitize_csv_field(value: str) -> str:
    if value and value[0] in ('=', '+', '-', '@'):
        return "'" + value
    return value
