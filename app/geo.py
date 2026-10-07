"""Villages / cells / sectors / districts. The SuperAdmin or an Admin pastes them in; no terminal needed."""
import re

from .db import audit

MAX_LINES = 3000


def add_locations(conn, actor, text):
    """text: one village per line, 'village, cell, sector, district' (comma, semicolon or tab separated; a header line
    starting with 'village' is skipped). Existing rows are left alone. Returns {added, skipped, errors}."""
    if actor["role"] not in ("superadmin", "admin"):
        raise PermissionError("forbidden")
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        raise ValueError("nothing_to_add")
    if len(lines) > MAX_LINES:
        raise ValueError("too_many_lines")
    added, skipped, errors = 0, 0, []
    for n, ln in enumerate(lines, 1):
        parts = [p.strip() for p in re.split(r"[,;\t]", ln)]
        if n == 1 and parts[0].lower() in ("village", "umudugudu"):
            continue
        if len(parts) < 4 or not all(1 <= len(p) <= 60 for p in parts[:4]):
            errors.append(f"line {n}: need village, cell, sector, district")
            continue
        village, cell, sector, district = parts[:4]
        if conn.execute("SELECT 1 FROM locations WHERE village=? AND cell=? AND sector=? AND district=?",
                        (village, cell, sector, district)).fetchone():
            skipped += 1
            continue
        conn.execute("INSERT INTO locations(village,cell,sector,district) VALUES(?,?,?,?)", (village, cell, sector, district))
        added += 1
    audit(conn, actor["id"], "locations.add", "locations", None, {"added": added, "skipped": skipped, "errors": len(errors)})
    return {"added": added, "skipped": skipped, "errors": errors[:20]}
