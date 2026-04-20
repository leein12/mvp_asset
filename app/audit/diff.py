def diff_fields(before: dict, after: dict) -> list[str]:
    changed: list[str] = []
    keys = set(before.keys()) | set(after.keys())
    for key in sorted(keys):
        if before.get(key) != after.get(key):
            changed.append(key)
    return changed
