def summary(conn):
    def one(q, *a):
        return conn.execute(q, a).fetchone()[0] or 0
    return {
        "users": {f"{r['role']}:{r['status']}": r["n"] for r in conn.execute(
            "SELECT role,status,COUNT(*) n FROM users GROUP BY role,status")},
        "products": {r["status"]: r["n"] for r in conn.execute("SELECT status,COUNT(*) n FROM products GROUP BY status")},
        "gmv_completed": one("SELECT SUM(total_amount) FROM orders WHERE status='completed'"),
        "income": {
            "registration_fees": one("SELECT SUM(amount) FROM transactions WHERE type='registration_fee' AND status='succeeded'"),
            "commission": one("SELECT SUM(amount) FROM transactions WHERE type='commission' AND status='settled'"),
            "listing_and_clearance_fees_settled": one(
                "SELECT SUM(amount) FROM transactions WHERE type IN ('listing_fee','clearance_fee') AND status='settled'"),
            "fees_accrued_not_yet_collected": one(
                "SELECT SUM(amount) FROM transactions WHERE type IN ('listing_fee','clearance_fee') AND status='accrued'"),
        },
        "failed_payments": one("SELECT COUNT(*) FROM transactions WHERE status='failed'"),
    }


# ---------------------------------------------------------------- dashboard (crops + livestock)
from datetime import timedelta

from .util import iso, utcnow

_SOLD = "('Sold','Verified','PaidOut')"


def _loc(col, sector, district):
    sql, args = "", []
    if sector or district:
        sql = f" AND {col} IN (SELECT id FROM locations WHERE 1=1"
        if sector:
            sql += " AND sector=?"
            args.append(sector)
        if district:
            sql += " AND district=?"
            args.append(district)
        sql += ")"
    return sql, args


def dashboard(conn, group=None, days=30, sector=None, district=None, now=None):
    """Aggregated (no personal data) view of everything listed in the last `days` days.
    group: None = crops + livestock, 'crop' or 'livestock'."""
    now = now or utcnow()
    days = max(1, min(int(days), 365))
    since = iso(now - timedelta(days=days))
    group = group if group in ("crop", "livestock") else None
    loc, largs = _loc("p.location_id", sector, district)
    gsql, gargs = (" AND c.grp=?", [group]) if group else ("", [])

    cats = [dict(r) for r in conn.execute(
        "SELECT c.code,c.grp,c.unit,c.name_rw,c.name_en,c.name_fr,"
        " COUNT(p.id) AS listed_items, COALESCE(SUM(p.quantity),0) AS listed_qty,"
        f" SUM(CASE WHEN p.status='Available' THEN 1 ELSE 0 END) AS available_items,"
        " COALESCE(SUM(CASE WHEN p.status='Available' THEN p.quantity END),0) AS available_qty,"
        f" SUM(CASE WHEN p.status IN {_SOLD} THEN 1 ELSE 0 END) AS sold_items,"
        f" COALESCE(SUM(CASE WHEN p.status IN {_SOLD} THEN p.quantity END),0) AS sold_qty,"
        " SUM(CASE WHEN p.status='Unsold' THEN 1 ELSE 0 END) AS unsold_items,"
        " CAST(AVG(p.price_per_unit) AS INTEGER) AS avg_price "
        f"FROM categories c LEFT JOIN products p ON p.category=c.code AND p.created_at>=?{loc} "
        f"WHERE c.active=1{gsql} GROUP BY c.code ORDER BY c.grp, c.sort_order, c.code",
        [since, *largs, *gargs])]

    value = {r["category"]: r["v"] for r in conn.execute(
        "SELECT p.category, COALESCE(SUM(o.total_amount),0) AS v FROM orders o JOIN products p ON p.id=o.product_id "
        f"WHERE o.status IN ('funded','revision_pending','verified','completed') AND p.created_at>=?{loc} "
        "GROUP BY p.category", [since, *largs])}
    for c in cats:
        c["sold_value"] = value.get(c["code"], 0)

    totals = {}
    for g in ("crop", "livestock"):
        if group and g != group:
            continue
        rows = [c for c in cats if c["grp"] == g]
        farmers = conn.execute(
            "SELECT COUNT(DISTINCT p.farmer_id) FROM products p JOIN categories c ON c.code=p.category "
            f"WHERE c.grp=? AND p.created_at>=?{loc}", [g, since, *largs]).fetchone()[0]
        totals[g] = {
            "listed_items": sum(c["listed_items"] for c in rows),
            "available_items": sum(c["available_items"] for c in rows),
            "sold_items": sum(c["sold_items"] for c in rows),
            "unsold_items": sum(c["unsold_items"] for c in rows),
            "sold_value": sum(c["sold_value"] for c in rows),
            "active_farmers": farmers,
        }
        if g == "livestock":  # animals are counted in heads, so these numbers can be added up
            totals[g]["heads_listed"] = sum(c["listed_qty"] for c in rows)
            totals[g]["heads_available"] = sum(c["available_qty"] for c in rows)
            totals[g]["heads_sold"] = sum(c["sold_qty"] for c in rows)

    by_sex = {r["sex"]: r["n"] for r in conn.execute(
        "SELECT p.sex, COALESCE(SUM(p.quantity),0) AS n FROM products p JOIN categories c ON c.code=p.category "
        f"WHERE c.grp='livestock' AND p.sex IS NOT NULL AND p.created_at>=?{loc} GROUP BY p.sex", [since, *largs])}

    by_village = [dict(r) for r in conn.execute(
        "SELECT COALESCE(l.village,'-') AS village, c.grp, COUNT(*) AS items, COALESCE(SUM(p.quantity),0) AS qty "
        "FROM products p JOIN categories c ON c.code=p.category LEFT JOIN locations l ON l.id=p.location_id "
        f"WHERE p.created_at>=?{loc}{gsql} GROUP BY l.village, c.grp ORDER BY items DESC LIMIT 50",
        [since, *largs, *gargs])]

    daily = [dict(r) for r in conn.execute(
        "SELECT substr(p.created_at,1,10) AS day, c.grp, COUNT(*) AS items FROM products p "
        f"JOIN categories c ON c.code=p.category WHERE p.created_at>=?{loc}{gsql} "
        "GROUP BY day, c.grp ORDER BY day", [since, *largs, *gargs])]

    return {"generated_at": iso(now), "days": days, "group": group, "sector": sector, "district": district,
            "totals": totals, "livestock_by_sex": by_sex, "categories": cats, "by_village": by_village,
            "daily": daily}
