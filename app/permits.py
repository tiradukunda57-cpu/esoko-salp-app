"""Government authorisations ("permits") - fully data-driven.

When Government gives a new rule (e.g. "every cow sold at market needs a movement permit"):
  1. SuperAdmin creates a permit TYPE       (POST /admin/permit-types)  - WHAT document, WHO it applies to, WHEN it is checked
  2. Switch it on / make it mandatory       (PATCH /admin/permit-types/{code}  {"active": true, "mandatory": true})
  3. Agents record permits they have seen   (POST /agent/permits)
No code change, no redeploy. Rules that are active but NOT mandatory are shown as advisory only.

Stages:   subject 'user'    -> listing (farmer) | purchase (buyer)
          subject 'product' -> handover (before payout) | market_entry (gate scan)"""
import re
from datetime import datetime, timedelta

from .db import audit
from .scope import check_area
from .util import KIGALI, iso, utcnow

USER_STAGES = {"listing": "farmer", "purchase": "buyer"}
PRODUCT_STAGES = ("handover", "market_entry")
EDITABLE = {"active", "mandatory", "validity_days", "issuer", "applies_to", "name_rw", "name_en", "name_fr"}


class PermitRequired(ValueError):
    def __init__(self, missing):
        self.missing = missing
        super().__init__("permit_required:" + ",".join(m["code"] for m in missing))


def _category(conn, code):
    return conn.execute("SELECT * FROM categories WHERE code=?", (code,)).fetchone()


def _valid_applies_to(conn, applies_to):
    return applies_to in ("all", "crop", "livestock") or _category(conn, applies_to) is not None


# ------------------------------------------------------------------ checking
def missing_types(conn, stage, *, category_code, user=None, product_id=None, now=None, mandatory_only=True):
    """Permit types that are required (active rules) at this stage but not validly present."""
    now_s = iso(now or utcnow())
    cat = _category(conn, category_code)
    if cat is None:
        return []
    out = []
    for pt in conn.execute("SELECT * FROM permit_types WHERE active=1 AND required_at=?", (stage,)).fetchall():
        if mandatory_only and not pt["mandatory"]:
            continue
        if pt["applies_to"] not in ("all", cat["grp"], cat["code"]):
            continue
        if pt["subject"] == "product":
            if product_id is None:
                continue
            q, a = "product_id=?", [product_id]
        else:
            if user is None or (pt["role_scope"] and pt["role_scope"] != user["role"]):
                continue
            q, a = "user_id=?", [user["id"]]
        found = conn.execute(
            f"SELECT 1 FROM permits WHERE permit_type_id=? AND status='approved' AND {q} "
            "AND (valid_until IS NULL OR valid_until>=?)", [pt["id"], *a, now_s]).fetchone()
        if not found:
            out.append(dict(pt))
    return out


def check_stage(conn, stage, *, category_code, user=None, product_id=None, now=None):
    miss = missing_types(conn, stage, category_code=category_code, user=user, product_id=product_id, now=now)
    if miss:
        raise PermitRequired(miss)


# ------------------------------------------------------------------ administration (SuperAdmin)
def list_types(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM permit_types ORDER BY id")]


def create_type(conn, actor, *, code, name_rw, name_en, name_fr, subject, required_at, applies_to="all",
                issuer=None, role_scope=None, mandatory=False, active=False, validity_days=None):
    if actor["role"] != "superadmin":
        raise PermissionError("only_superadmin")
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,50}", code or ""):
        raise ValueError("bad_code")
    if subject == "user":
        if required_at not in USER_STAGES:
            raise ValueError("user_permits_apply_at_listing_or_purchase")
        role_scope = role_scope or USER_STAGES[required_at]
        if role_scope != USER_STAGES[required_at]:
            raise ValueError("role_scope_does_not_match_stage")
    elif subject == "product":
        if required_at not in PRODUCT_STAGES:
            raise ValueError("product_permits_apply_at_handover_or_market_entry")
        role_scope = None
    else:
        raise ValueError("bad_subject")
    if not _valid_applies_to(conn, applies_to):
        raise ValueError("bad_applies_to")
    if validity_days is not None and not (isinstance(validity_days, int) and 1 <= validity_days <= 3650):
        raise ValueError("bad_validity_days")
    if not all((n or "").strip() for n in (name_rw, name_en, name_fr)):
        raise ValueError("names_required")
    if conn.execute("SELECT 1 FROM permit_types WHERE code=?", (code,)).fetchone():
        raise ValueError("duplicate")
    conn.execute(
        "INSERT INTO permit_types(code,name_rw,name_en,name_fr,issuer,subject,applies_to,required_at,role_scope,"
        "mandatory,active,validity_days,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (code, name_rw, name_en, name_fr, issuer, subject, applies_to, required_at, role_scope,
         1 if mandatory else 0, 1 if active else 0, validity_days, iso(utcnow())))
    audit(conn, actor["id"], "permit_type.create", "permit_type", code,
          {"required_at": required_at, "applies_to": applies_to, "mandatory": bool(mandatory), "active": bool(active)})


def update_type(conn, actor, code, **changes):
    if actor["role"] != "superadmin":
        raise PermissionError("only_superadmin")
    if not changes or not set(changes) <= EDITABLE:
        raise ValueError("unknown_or_empty_fields")
    if not conn.execute("SELECT 1 FROM permit_types WHERE code=?", (code,)).fetchone():
        raise ValueError("not_found")
    if "applies_to" in changes and not _valid_applies_to(conn, changes["applies_to"]):
        raise ValueError("bad_applies_to")
    for k in ("active", "mandatory"):
        if k in changes:
            changes[k] = 1 if changes[k] else 0
    sets = ", ".join(f"{k}=?" for k in changes)
    conn.execute(f"UPDATE permit_types SET {sets} WHERE code=?", [*changes.values(), code])
    audit(conn, actor["id"], "permit_type.update", "permit_type", code, changes)


# ------------------------------------------------------------------ recording permits (Agent / Admin)
def grant_permit(conn, actor, type_code, *, user_id=None, product_id=None, reference=None, valid_until=None,
                 note=None, now=None):
    """An Agent/Admin records that they SAW a valid document. Agents only act inside their own sector."""
    now = now or utcnow()
    if actor["role"] not in ("agent", "admin", "superadmin"):
        raise PermissionError("forbidden")
    pt = conn.execute("SELECT * FROM permit_types WHERE code=?", (type_code,)).fetchone()
    if pt is None:
        raise ValueError("unknown_permit_type")
    if (user_id is None) == (product_id is None):
        raise ValueError("give_either_user_id_or_product_id")
    if pt["subject"] == "product":
        if product_id is None:
            raise ValueError("product_id_required")
        p = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if p is None:
            raise ValueError("product_not_found")
        check_area(conn, actor, p["location_id"])
    else:
        if user_id is None:
            raise ValueError("user_id_required")
        u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if u is None or (pt["role_scope"] and u["role"] != pt["role_scope"]):
            raise ValueError("user_not_found_or_wrong_role")
        check_area(conn, actor, u["location_id"])
    expires = None
    if valid_until:
        d = datetime.strptime(valid_until, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=KIGALI)
        expires = iso(d)
    elif pt["validity_days"]:
        expires = iso(now + timedelta(days=pt["validity_days"]))
    cur = conn.execute(
        "INSERT INTO permits(permit_type_id,user_id,product_id,reference,status,issued_by,issued_at,valid_until,note) "
        "VALUES(?,?,?,?,'approved',?,?,?,?)", (pt["id"], user_id, product_id, reference, actor["id"], iso(now), expires, note))
    audit(conn, actor["id"], "permit.grant", "permit", cur.lastrowid, {"type": type_code, "ref": reference})
    return cur.lastrowid


def revoke_permit(conn, actor, permit_id):
    if actor["role"] not in ("admin", "superadmin"):
        raise PermissionError("forbidden")
    cur = conn.execute("UPDATE permits SET status='revoked' WHERE id=?", (permit_id,))
    if cur.rowcount != 1:
        raise ValueError("not_found")
    audit(conn, actor["id"], "permit.revoke", "permit", permit_id)


def list_permits(conn, user_id=None, product_id=None):
    q = ("SELECT pm.*, pt.code AS type_code, pt.name_en FROM permits pm "
         "JOIN permit_types pt ON pt.id=pm.permit_type_id WHERE 1=1")
    a = []
    if user_id:
        q += " AND pm.user_id=?"
        a.append(user_id)
    if product_id:
        q += " AND pm.product_id=?"
        a.append(product_id)
    return [dict(r) for r in conn.execute(q + " ORDER BY pm.id DESC LIMIT 200", a)]
