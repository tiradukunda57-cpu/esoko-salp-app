"""Products, orders, agent verification and payouts."""
from . import catalog, payments, permits, sms
from .scope import check_area
from .db import audit
from .fees import commission_for, get_fee
from .config import get_settings
from .i18n import t
from .util import KIGALI, iso, parse_iso, utcnow
from datetime import timedelta

class MarketError(ValueError):
    pass


def _row(conn, table, id_):
    return conn.execute(f"SELECT * FROM {table} WHERE id=?", (id_,)).fetchone()


def _village(conn, location_id):
    if not location_id:
        return "-"
    r = conn.execute("SELECT village FROM locations WHERE id=?", (location_id,)).fetchone()
    return r["village"] if r else "-"


def _gen_code(conn, prefix, now):
    day = now.astimezone(KIGALI).strftime("%Y%m%d")
    n = conn.execute("SELECT COUNT(*) FROM products WHERE code LIKE ?", (f"{prefix}-{day}-%",)).fetchone()[0] + 1
    return f"{prefix}-{day}-{n:04d}"


# ---------------------------------------------------------------- listing
def create_product(conn, farmer_id, category, quantity, price_per_unit, location_id=None, now=None, *,
                   tag_number=None, sex=None, age_months=None, notes=None, listed_by=None):
    now = now or utcnow()
    farmer = _row(conn, "users", farmer_id)
    if not farmer or farmer["role"] != "farmer" or farmer["status"] != "active":
        raise MarketError("farmer_not_active")
    cat = catalog.get_category(conn, category)
    if not cat:
        raise MarketError("bad_category")
    if not (0 < quantity <= 100_000):
        raise MarketError("bad_quantity")
    if not (0 < price_per_unit <= 100_000_000):
        raise MarketError("bad_price")
    if sex not in (None, "male", "female"):
        raise MarketError("bad_sex")
    if age_months is not None and not (isinstance(age_months, int) and 0 <= age_months <= 600):
        raise MarketError("bad_age")
    tag = (tag_number or "").strip().upper() or None
    if (tag or sex or age_months is not None) and cat["grp"] != "livestock":
        raise MarketError("livestock_fields_only_for_livestock")
    if tag and conn.execute("SELECT 1 FROM products WHERE tag_number=? AND status IN "
                            "('Available','Reserved','Sold','Verified','Unsold')", (tag,)).fetchone():
        raise MarketError("tag_already_listed")
    permits.check_stage(conn, "listing", category_code=category, user=dict(farmer), now=now)  # government rules
    loc = location_id or farmer["location_id"]
    code = _gen_code(conn, cat["prefix"], now)
    cur = conn.execute(
        "INSERT INTO products(code,farmer_id,category,quantity,unit,price_per_unit,location_id,status,created_at,"
        "tag_number,sex,age_months,notes) VALUES(?,?,?,?,?,?,?,'Available',?,?,?,?,?)",
        (code, farmer_id, category, quantity, cat["unit"], int(price_per_unit), loc, iso(now), tag, sex, age_months, notes))
    fee = get_fee(conn, "listing_fee")
    if fee > 0:  # accrued now, deducted from the farmer's next payout
        payments.add_tx(conn, type="listing_fee", amount=fee, status="accrued", user_id=farmer_id, product_id=cur.lastrowid)
    if listed_by:
        audit(conn, listed_by, "product.agent_listing", "product", cur.lastrowid, {"farmer": farmer_id})
    return dict(_row(conn, "products", cur.lastrowid))


def list_available(conn, category=None, location_id=None, limit=100, group=None):
    q = ("SELECT p.id,p.code,p.category,c.grp,c.name_rw,c.name_en,c.name_fr,p.quantity,p.unit,p.price_per_unit,p.grade,"
         "p.sex,p.age_months,p.created_at,l.village,l.cell,l.sector,l.district,l.lat,l.lng FROM products p "
         "JOIN categories c ON c.code=p.category LEFT JOIN locations l ON l.id=p.location_id WHERE p.status='Available'")
    args = []
    if category:
        q += " AND p.category=?"
        args.append(category)
    if group:
        q += " AND c.grp=?"
        args.append(group)
    if location_id:
        q += " AND p.location_id=?"
        args.append(location_id)
    q += " ORDER BY p.id DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(q, args)]


# ---------------------------------------------------------------- ordering
def place_order(conn, buyer_id, product_id, now=None):
    now = now or utcnow()
    buyer = _row(conn, "users", buyer_id)
    if not buyer or buyer["role"] != "buyer" or buyer["status"] != "active":
        raise MarketError("buyer_not_active")
    p = _row(conn, "products", product_id)
    if not p:
        raise MarketError("not_found")
    permits.check_stage(conn, "purchase", category_code=p["category"], user=dict(buyer), now=now)  # government rules
    # atomic reservation: only one buyer can move Available -> Reserved
    cur = conn.execute("UPDATE products SET status='Reserved' WHERE id=? AND status='Available'", (product_id,))
    if cur.rowcount != 1:
        raise MarketError("not_available")
    total = int(round(p["quantity"] * p["price_per_unit"]))
    o = conn.execute("INSERT INTO orders(product_id,buyer_id,total_amount,status,created_at,updated_at) "
                     "VALUES(?,?,?,'awaiting_payment',?,?)", (product_id, buyer_id, total, iso(now), iso(now)))
    ref = payments.request_escrow(conn, order_id=o.lastrowid, buyer_id=buyer_id, product_id=product_id,
                                  msisdn=buyer["phone"], amount=total)
    audit(conn, buyer_id, "order.create", "order", o.lastrowid, {"product": p["code"], "total": total})
    return {"order_id": o.lastrowid, "payment_ref": ref, "total": total}


def on_escrow_funded(conn, order_id):
    o = _row(conn, "orders", order_id)
    if not o or o["status"] != "awaiting_payment":
        return
    conn.execute("UPDATE orders SET status='funded', updated_at=? WHERE id=?", (iso(utcnow()), order_id))
    conn.execute("UPDATE products SET status='Sold' WHERE id=?", (o["product_id"],))
    p = _row(conn, "products", o["product_id"])
    f = _row(conn, "users", p["farmer_id"])
    sms.send_sms(conn, f["phone"], t("sms_selected", f["language"], code=p["code"], village=_village(conn, p["location_id"])))


def on_escrow_failed(conn, order_id):
    o = _row(conn, "orders", order_id)
    if not o or o["status"] != "awaiting_payment":
        return
    conn.execute("UPDATE orders SET status='cancelled', updated_at=? WHERE id=?", (iso(utcnow()), order_id))
    conn.execute("UPDATE products SET status='Available' WHERE id=? AND status='Reserved'", (o["product_id"],))


def release_stale_reservations(conn, now=None, minutes=30):
    """Unpaid orders older than `minutes` are cancelled and the product goes back on sale."""
    now = now or utcnow()
    limit = iso(now - timedelta(minutes=minutes))
    rows = conn.execute("SELECT id FROM orders WHERE status='awaiting_payment' AND created_at<=?", (limit,)).fetchall()
    for r in rows:
        conn.execute("UPDATE transactions SET status='failed' WHERE order_id=? AND type='escrow_in' AND status='pending'", (r["id"],))
        on_escrow_failed(conn, r["id"])
    return len(rows)


# ---------------------------------------------------------------- agent work
def _check_scope(conn, actor, product):
    check_area(conn, actor, product["location_id"])


def agent_queue(conn, actor):
    q = ("SELECT p.id product_id,p.code,p.category,p.quantity,p.unit,p.price_per_unit,p.status product_status,"
         "o.id order_id,o.status order_status,o.total_amount,f.name farmer_name,f.phone farmer_phone,"
         "b.name buyer_name,l.village,l.sector,l.district,p.category,p.tag_number,p.sex,p.age_months FROM products p "
         "JOIN orders o ON o.product_id=p.id AND o.status IN ('funded','revision_pending','verified') "
         "JOIN users f ON f.id=p.farmer_id JOIN users b ON b.id=o.buyer_id "
         "LEFT JOIN locations l ON l.id=p.location_id WHERE p.status IN ('Sold','Verified')")
    args = []
    if actor["role"] == "agent":
        if actor["location_id"] is None:
            return []
        a = conn.execute("SELECT sector,district FROM locations WHERE id=?", (actor["location_id"],)).fetchone()
        q += " AND l.sector=? AND l.district=?"
        args += [a["sector"], a["district"]]
    rows = [dict(r) for r in conn.execute(q + " ORDER BY p.id", args)]
    for r in rows:  # show the agent which authorizations are still missing (blocking or advisory)
        r["permits_missing"] = [{"code": m["code"], "name": m["name_en"], "mandatory": bool(m["mandatory"])}
                                for m in permits.missing_types(conn, "handover", category_code=r["category"],
                                                               product_id=r["product_id"], mandatory_only=False)]
    return rows


def agent_verify(conn, actor, product_id, result, grade=None, weight=None, note=None, new_price=None, now=None,
                 tag_number=None):
    now = now or utcnow()
    p = _row(conn, "products", product_id)
    if not p:
        raise MarketError("not_found")
    _check_scope(conn, actor, p)
    o = conn.execute("SELECT * FROM orders WHERE product_id=? AND status='funded'", (product_id,)).fetchone()
    if p["status"] != "Sold" or not o:
        raise MarketError("not_ready_for_verification")
    if grade not in (None, "A", "B"):
        raise MarketError("bad_grade")
    farmer = _row(conn, "users", p["farmer_id"])
    buyer = _row(conn, "users", o["buyer_id"])
    tag = (tag_number or "").strip().upper() or None
    if tag:
        cat = catalog.get_category(conn, p["category"], include_inactive=True)
        if cat["grp"] != "livestock":
            raise MarketError("livestock_fields_only_for_livestock")
        if conn.execute("SELECT 1 FROM products WHERE tag_number=? AND id<>? AND status IN "
                        "('Available','Reserved','Sold','Verified','Unsold')", (tag, product_id)).fetchone():
            raise MarketError("tag_already_listed")
        conn.execute("UPDATE products SET tag_number=? WHERE id=?", (tag, product_id))
    if result == "approve":
        conn.execute("UPDATE products SET status='Verified', grade=? WHERE id=?", (grade, product_id))
        conn.execute("UPDATE orders SET status='verified', updated_at=? WHERE id=?", (iso(now), o["id"]))
    elif result == "downgrade":
        if not isinstance(new_price, int) or not 0 < new_price < p["price_per_unit"]:
            raise MarketError("new_price_must_be_lower")
        revised_total = int(round(p["quantity"] * new_price))
        conn.execute("UPDATE orders SET status='revision_pending', revised_price=?, revised_total=?, updated_at=? WHERE id=?",
                     (new_price, revised_total, iso(now), o["id"]))
        conn.execute("UPDATE products SET grade=? WHERE id=?", (grade, product_id))
        sms.send_sms(conn, buyer["phone"], t("sms_revision", buyer["language"], code=p["code"], grade=grade or "B",
                                             total=revised_total, old=o["total_amount"]))
    elif result == "reject":
        _refund(conn, o, o["total_amount"], buyer)
        conn.execute("UPDATE orders SET status='refunded', updated_at=? WHERE id=?", (iso(now), o["id"]))
        conn.execute("UPDATE products SET status='Rejected' WHERE id=?", (product_id,))
        sms.send_sms(conn, farmer["phone"], t("sms_rejected", farmer["language"], code=p["code"]))
    else:
        raise MarketError("bad_result")
    conn.execute("INSERT INTO verifications(product_id,agent_id,result,grade,weight,note,new_price,created_at) "
                 "VALUES(?,?,?,?,?,?,?,?)", (product_id, actor["id"], result, grade, weight, note, new_price, iso(now)))
    audit(conn, actor["id"], f"verify.{result}", "product", product_id, {"order": o["id"]})


def _refund(conn, order, amount, buyer):
    if amount <= 0:
        return
    payments.send_money(conn, type="refund", user_id=buyer["id"], msisdn=buyer["phone"], amount=amount,
                        order_id=order["id"], product_id=order["product_id"])
    sms.send_sms(conn, buyer["phone"], t("sms_refund", buyer["language"], amount=amount, order=order["id"]))


def respond_to_revision(conn, buyer_id, order_id, accept, now=None):
    now = now or utcnow()
    o = _row(conn, "orders", order_id)
    if not o or o["buyer_id"] != buyer_id:
        raise MarketError("not_found")
    if o["status"] != "revision_pending":
        raise MarketError("no_revision_pending")
    buyer = _row(conn, "users", buyer_id)
    if accept:
        _refund(conn, o, o["total_amount"] - o["revised_total"], buyer)
        conn.execute("UPDATE orders SET total_amount=?, status='verified', updated_at=? WHERE id=?",
                     (o["revised_total"], iso(now), order_id))
        conn.execute("UPDATE products SET status='Verified', price_per_unit=? WHERE id=?", (o["revised_price"], o["product_id"]))
    else:
        _refund(conn, o, o["total_amount"], buyer)
        conn.execute("UPDATE orders SET status='refunded', updated_at=? WHERE id=?", (iso(now), order_id))
        conn.execute("UPDATE products SET status='Available' WHERE id=?", (o["product_id"],))
    audit(conn, buyer_id, "order.revision_accept" if accept else "order.revision_decline", "order", order_id)


def confirm_handover(conn, actor, order_id, now=None):
    """Agent confirms the buyer collected a verified item -> farmer is paid, commission recorded."""
    now = now or utcnow()
    o = _row(conn, "orders", order_id)
    if not o or o["status"] != "verified":
        raise MarketError("order_not_verified")
    p = _row(conn, "products", o["product_id"])
    _check_scope(conn, actor, p)
    permits.check_stage(conn, "handover", category_code=p["category"], product_id=p["id"], now=now)  # government rules
    farmer = _row(conn, "users", p["farmer_id"])
    total = o["total_amount"]
    commission = commission_for(total, get_fee(conn, "commission_bps"))
    available = total - commission
    deducted, ids = 0, []
    for r in conn.execute("SELECT id,amount FROM transactions WHERE user_id=? AND status='accrued' ORDER BY id",
                          (farmer["id"],)).fetchall():
        if deducted + r["amount"] <= available:
            deducted += r["amount"]
            ids.append(r["id"])
    for i in ids:
        conn.execute("UPDATE transactions SET status='settled' WHERE id=?", (i,))
    payout = available - deducted
    if payout > 0:
        payments.send_money(conn, type="payout", user_id=farmer["id"], msisdn=farmer["phone"], amount=payout,
                            order_id=order_id, product_id=p["id"])
    payments.add_tx(conn, type="commission", amount=commission, status="settled", order_id=order_id,
                    product_id=p["id"], user_id=farmer["id"], msisdn=get_settings().settlement_msisdn)
    conn.execute("UPDATE orders SET status='completed', updated_at=? WHERE id=?", (iso(now), order_id))
    conn.execute("UPDATE products SET status='PaidOut' WHERE id=?", (p["id"],))
    sms.send_sms(conn, farmer["phone"], t("sms_payout", farmer["language"], amount=payout, code=p["code"],
                                          fee=commission + deducted))
    audit(conn, actor["id"], "order.complete", "order", order_id,
          {"total": total, "commission": commission, "fees": deducted, "payout": payout})
    return {"total": total, "commission": commission, "fees_deducted": deducted, "payout": payout}
