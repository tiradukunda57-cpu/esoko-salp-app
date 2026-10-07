"""Self-service data for farmers and buyers (web portal) + SMS one-time-code (OTP) login.
Farmers register on USSD and have no password, so they sign in with a 6-digit code sent by SMS."""
import hmac
import hashlib
import secrets
from datetime import timedelta

from . import permits, sms
from .config import get_settings
from .i18n import t
from .users import get_user_by_phone, normalize_phone
from .util import iso, utcnow

OTP_TTL_MIN = 10
MAX_REQUESTS = 3      # per phone per 10 minutes
MAX_ATTEMPTS = 5      # wrong guesses per code


def _hash(code, phone):
    return hmac.new(get_settings().pepper.encode(), f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def request_otp(conn, phone, now=None):
    """Silently does nothing for unknown / inactive / staff numbers (so nobody can probe which numbers exist)."""
    now = now or utcnow()
    p = normalize_phone(phone)
    user = get_user_by_phone(conn, p) if p else None
    if not user or user["status"] != "active" or user["role"] not in ("farmer", "buyer"):
        return False
    since = iso(now - timedelta(minutes=OTP_TTL_MIN))
    if conn.execute("SELECT COUNT(*) FROM otp_codes WHERE phone=? AND created_at>=?", (p, since)).fetchone()[0] >= MAX_REQUESTS:
        return False
    code = str(secrets.randbelow(900_000) + 100_000)
    conn.execute("INSERT INTO otp_codes(phone,code_hash,expires_at,created_at) VALUES(?,?,?,?)",
                 (p, _hash(code, p), iso(now + timedelta(minutes=OTP_TTL_MIN)), iso(now)))
    sms.send_sms(conn, p, t("sms_otp", user["language"], code=code))
    return True


def verify_otp(conn, phone, code, now=None):
    """Returns the user row, or None. The caller must COMMIT even on failure so the attempt counter is kept."""
    now = now or utcnow()
    p = normalize_phone(phone)
    if not p:
        return None
    row = conn.execute("SELECT * FROM otp_codes WHERE phone=? AND used=0 AND expires_at>=? ORDER BY id DESC LIMIT 1",
                       (p, iso(now))).fetchone()
    if row is None or row["attempts"] >= MAX_ATTEMPTS:
        return None
    conn.execute("UPDATE otp_codes SET attempts=attempts+1 WHERE id=?", (row["id"],))
    if not hmac.compare_digest(_hash(str(code).strip(), p), row["code_hash"]):
        return None
    conn.execute("UPDATE otp_codes SET used=1 WHERE id=?", (row["id"],))
    user = get_user_by_phone(conn, p)
    return user if user and user["status"] == "active" else None


def farmer_overview(conn, user, now=None):
    now_s = iso(now or utcnow())
    uid = user["id"]
    loc = conn.execute("SELECT village,cell,sector,district FROM locations WHERE id=?", (user["location_id"],)).fetchone() \
        if user["location_id"] else None
    listings = [dict(r) for r in conn.execute(
        "SELECT p.code,p.category,c.grp,c.name_rw,c.name_en,c.name_fr,p.quantity,p.unit,p.price_per_unit,p.status,"
        "p.created_at,o.total_amount AS order_total FROM products p JOIN categories c ON c.code=p.category "
        "LEFT JOIN orders o ON o.product_id=p.id AND o.status IN ('funded','revision_pending','verified','completed') "
        "WHERE p.farmer_id=? ORDER BY p.id DESC LIMIT 50", (uid,))]
    by_status = {r["status"]: r["n"] for r in conn.execute(
        "SELECT status,COUNT(*) n FROM products WHERE farmer_id=? GROUP BY status", (uid,))}

    def one(q, *a):
        return conn.execute(q, a).fetchone()[0] or 0
    totals = {
        "by_status": by_status,
        "paid_out": one("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='payout' AND status='succeeded'", uid),
        "waiting_for_payment": one(
            "SELECT SUM(o.total_amount) FROM orders o JOIN products p ON p.id=o.product_id "
            "WHERE p.farmer_id=? AND o.status IN ('funded','revision_pending','verified')", uid),
        "fees_to_be_deducted": one("SELECT SUM(amount) FROM transactions WHERE user_id=? AND status='accrued'", uid),
    }
    clearances = [dict(r) for r in conn.execute(
        "SELECT p.code AS product, c.code, c.valid_until FROM clearances c JOIN products p ON p.id=c.product_id "
        "WHERE p.farmer_id=? AND c.used_at IS NULL AND c.valid_until>=? ORDER BY c.id DESC LIMIT 20", (uid, now_s))]
    payouts = [dict(r) for r in conn.execute(
        "SELECT t.amount, substr(t.created_at,1,10) AS date, p.code AS product FROM transactions t "
        "LEFT JOIN products p ON p.id=t.product_id WHERE t.user_id=? AND t.type='payout' ORDER BY t.id DESC LIMIT 20", (uid,))]
    my_permits = [dict(r) for r in conn.execute(
        "SELECT pt.code,pt.name_rw,pt.name_en,pt.name_fr,pm.reference,pm.valid_until,p.code AS product "
        "FROM permits pm JOIN permit_types pt ON pt.id=pm.permit_type_id LEFT JOIN products p ON p.id=pm.product_id "
        "WHERE pm.status='approved' AND (pm.user_id=? OR p.farmer_id=?) ORDER BY pm.id DESC LIMIT 30", (uid, uid))]
    blocked = []
    for c in conn.execute("SELECT code,name_rw,name_en,name_fr FROM categories WHERE active=1 ORDER BY sort_order"):
        miss = permits.missing_types(conn, "listing", category_code=c["code"], user=dict(user), now=now)
        if miss:
            blocked.append({"category": c["code"], "names": {"rw": c["name_rw"], "en": c["name_en"], "fr": c["name_fr"]},
                            "missing": [m["name_en"] for m in miss]})
    return {"profile": {"name": user["name"], "phone": user["phone"], "language": user["language"],
                        "location": dict(loc) if loc else None},
            "totals": totals, "listings": listings, "clearances": clearances, "payouts": payouts,
            "permits": my_permits, "listing_blocked": blocked}


def buyer_overview(conn, user):
    uid = user["id"]
    orders = [dict(r) for r in conn.execute(
        "SELECT o.id AS order_id,o.status,o.total_amount,o.revised_total,o.revised_price,o.created_at,"
        "p.code AS product,p.quantity,p.unit,c.name_rw,c.name_en,c.name_fr,COALESCE(l.village,'-') AS village "
        "FROM orders o JOIN products p ON p.id=o.product_id JOIN categories c ON c.code=p.category "
        "LEFT JOIN locations l ON l.id=p.location_id WHERE o.buyer_id=? ORDER BY o.id DESC LIMIT 50", (uid,))]

    def one(q, *a):
        return conn.execute(q, a).fetchone()[0] or 0
    return {"profile": {"name": user["name"], "phone": user["phone"]},
            "totals": {"spent": one("SELECT SUM(total_amount) FROM orders WHERE buyer_id=? AND status='completed'", uid),
                       "in_progress": one("SELECT COUNT(*) FROM orders WHERE buyer_id=? AND status IN "
                                          "('awaiting_payment','funded','revision_pending','verified')", uid),
                       "needs_your_answer": one("SELECT COUNT(*) FROM orders WHERE buyer_id=? AND status='revision_pending'", uid)},
            "orders": orders}
