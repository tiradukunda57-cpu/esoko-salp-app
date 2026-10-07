from .db import audit

LIMITS = {
    "registration_fee": (0, 100_000),
    "listing_fee": (0, 10_000),
    "commission_bps": (0, 2_000),   # max 20 %
    "clearance_fee": (0, 10_000),
}


def get_fee(conn, key):
    row = conn.execute("SELECT value FROM fee_config WHERE key=?", (key,)).fetchone()
    if row is None:
        raise KeyError(key)
    return row["value"]


def all_fees(conn):
    return {r["key"]: r["value"] for r in conn.execute("SELECT key,value FROM fee_config")}


def set_fee(conn, actor, key, value):
    """Only the SuperAdmin may change fees. Every change is audited."""
    from .util import iso, utcnow
    if actor["role"] != "superadmin":
        raise PermissionError("only_superadmin")
    if key not in LIMITS:
        raise ValueError("unknown_fee")
    lo, hi = LIMITS[key]
    if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
        raise ValueError("out_of_range")
    old = get_fee(conn, key)
    conn.execute("UPDATE fee_config SET value=?, updated_at=?, updated_by=? WHERE key=?",
                 (value, iso(utcnow()), actor["id"], key))
    audit(conn, actor["id"], "fee.update", "fee_config", key, {"old": old, "new": value})


def commission_for(total: int, bps: int) -> int:
    return (total * bps + 5000) // 10000  # round half up
