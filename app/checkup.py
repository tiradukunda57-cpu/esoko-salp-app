"""Tuesday & Friday 19:00 CAT automated checkup (run by cron -> `python -m app.cli run-checkup`)."""
import secrets
from collections import defaultdict
from datetime import datetime, timedelta

from . import payments, permits, sms
from .db import audit
from .fees import get_fee
from .i18n import t
from .util import KIGALI, iso, parse_iso, utcnow


def end_of_next_kigali_day(now):
    k = now.astimezone(KIGALI)
    nxt = (k + timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0)
    return nxt


def _new_code(conn):
    for _ in range(50):
        code = str(secrets.randbelow(900_000) + 100_000)
        if not conn.execute("SELECT 1 FROM clearances WHERE code=?", (code,)).fetchone():
            return code
    raise RuntimeError("could not generate clearance code")


def run_checkup(conn, now=None):
    now = now or utcnow()
    valid_until = end_of_next_kigali_day(now)
    clearance_fee = get_fee(conn, "clearance_fee")
    summary = {"run_at": iso(now), "sold": [], "unsold": [], "by_village": {}}
    by_village = defaultdict(lambda: {"sold_value": 0, "sold_items": 0, "unsold_items": 0})

    # 1) SOLD: congratulate farmers once
    sold = conn.execute(
        "SELECT p.*, u.phone, u.language, u.name AS farmer_name, COALESCE(l.village,'-') AS village, "
        "o.total_amount FROM products p JOIN users u ON u.id=p.farmer_id "
        "LEFT JOIN locations l ON l.id=p.location_id "
        "JOIN orders o ON o.product_id=p.id AND o.status IN ('funded','revision_pending','verified','completed') "
        "WHERE p.status IN ('Sold','Verified','PaidOut') AND p.sold_notified_at IS NULL").fetchall()
    for r in sold:
        sms.send_sms(conn, r["phone"], t("sms_sold", r["language"], code=r["code"]))
        conn.execute("UPDATE products SET sold_notified_at=? WHERE id=?", (iso(now), r["id"]))
        summary["sold"].append({"code": r["code"], "farmer": r["farmer_name"], "village": r["village"], "amount": r["total_amount"]})
        by_village[r["village"]]["sold_value"] += r["total_amount"]
        by_village[r["village"]]["sold_items"] += 1

    # 2) UNSOLD: clearance code per item, one SMS per farmer
    unsold = conn.execute(
        "SELECT p.*, u.phone, u.language, u.name AS farmer_name, COALESCE(l.village,'-') AS village "
        "FROM products p JOIN users u ON u.id=p.farmer_id LEFT JOIN locations l ON l.id=p.location_id "
        "WHERE p.status='Available' ORDER BY p.farmer_id, p.id").fetchall()
    per_farmer = defaultdict(list)
    for r in unsold:
        code = _new_code(conn)
        conn.execute("INSERT INTO clearances(product_id,code,issued_at,valid_until) VALUES(?,?,?,?)",
                     (r["id"], code, iso(now), iso(valid_until)))
        conn.execute("UPDATE products SET status='Unsold' WHERE id=?", (r["id"],))
        if clearance_fee > 0:
            payments.add_tx(conn, type="clearance_fee", amount=clearance_fee, status="accrued",
                            user_id=r["farmer_id"], product_id=r["id"])
        per_farmer[r["farmer_id"]].append((r, code))
        summary["unsold"].append({"code": r["code"], "farmer": r["farmer_name"], "village": r["village"], "clearance": code})
        by_village[r["village"]]["unsold_items"] += 1
    for items in per_farmer.values():
        first = items[0][0]
        text = ", ".join(f"{r['code']}:{c}" for r, c in items)
        sms.send_sms(conn, first["phone"], t("sms_unsold", first["language"], items=text))

    summary["by_village"] = dict(by_village)
    summary["totals"] = {"sold_items": len(summary["sold"]), "unsold_items": len(summary["unsold"]),
                         "sold_value": sum(s["amount"] for s in summary["sold"])}
    audit(conn, None, "checkup.run", "system", None, summary["totals"])
    return summary


def verify_clearance(conn, code, gate_user_id=None, consume=True, now=None):
    now = now or utcnow()
    r = conn.execute(
        "SELECT c.*, p.code AS product_code, p.category, p.quantity, p.unit, u.name AS farmer_name, "
        "COALESCE(l.village,'-') AS village FROM clearances c JOIN products p ON p.id=c.product_id "
        "JOIN users u ON u.id=p.farmer_id LEFT JOIN locations l ON l.id=p.location_id WHERE c.code=?",
        (str(code).strip(),)).fetchone()
    if r is None:
        return {"status": "unknown"}
    info = {"product": r["product_code"], "category": r["category"], "quantity": r["quantity"],
            "unit": r["unit"], "farmer": r["farmer_name"], "village": r["village"], "valid_until": r["valid_until"]}
    if r["used_at"]:
        return {"status": "used", **info}
    if now > parse_iso(r["valid_until"]):
        return {"status": "expired", **info}
    cat = conn.execute("SELECT category FROM products WHERE id=?", (r["product_id"],)).fetchone()["category"]
    miss = permits.missing_types(conn, "market_entry", category_code=cat, product_id=r["product_id"], now=now)
    if miss:  # a government rule requires an extra authorization before this item may enter the market
        return {"status": "permit_missing", "missing": [m["code"] for m in miss], **info}
    if consume:
        conn.execute("UPDATE clearances SET used_at=?, gate_user_id=? WHERE id=?", (iso(now), gate_user_id, r["id"]))
        audit(conn, gate_user_id, "clearance.scan", "clearance", r["id"])
    return {"status": "valid", **info}
