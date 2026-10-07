import re

from . import payments
from .db import audit
from .fees import get_fee
from .i18n import LANGS
from .security import hash_national_id, hash_password
from .util import iso, utcnow
from .config import get_settings

PHONE_RE = re.compile(r"^\+2507[2389]\d{7}$")
ID_RE = re.compile(r"^\d{16}$")


class RegistrationError(ValueError):
    pass


def normalize_phone(raw):
    s = re.sub(r"[\s\-()]", "", str(raw or ""))
    if s.startswith("250"):
        s = "+" + s
    elif s.startswith("07"):
        s = "+25" + s
    return s if PHONE_RE.match(s) else None


def get_user(conn, user_id):
    return conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def get_user_by_phone(conn, phone):
    return conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()


def register_user(conn, *, role, name, phone, national_id, location_id=None, language="rw",
                  password=None, consent=True, registered_by=None):
    """Registers a farmer or buyer. Status stays 'pending_payment' until the registration fee is paid."""
    if role not in ("farmer", "buyer"):
        raise RegistrationError("bad_role")
    if not consent:
        raise RegistrationError("no_consent")
    phone_n = normalize_phone(phone)
    if not phone_n:
        raise RegistrationError("bad_phone")
    nid = re.sub(r"\s", "", str(national_id or ""))
    if not ID_RE.match(nid):
        raise RegistrationError("bad_id")
    name = (name or "").strip()
    if not 2 <= len(name) <= 80:
        raise RegistrationError("bad_name")
    if language not in LANGS:
        language = "rw"
    if role == "buyer" and (not password or len(password) < 8):
        raise RegistrationError("weak_password")
    nid_hash = hash_national_id(nid, get_settings().pepper)
    if conn.execute("SELECT 1 FROM users WHERE phone=? OR national_id_hash=?", (phone_n, nid_hash)).fetchone():
        raise RegistrationError("duplicate")
    fee = get_fee(conn, "registration_fee")
    cur = conn.execute(
        "INSERT INTO users(role,name,phone,national_id_hash,national_id_last4,password_hash,language,location_id,"
        "status,consent_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (role, name, phone_n, nid_hash, nid[-4:], hash_password(password) if password else None, language,
         location_id, "pending_payment", iso(utcnow()), iso(utcnow())))
    uid = cur.lastrowid
    out = {"user_id": uid, "fee": fee, "payment_ref": None, "status": "pending_payment"}
    if fee > 0:
        out["payment_ref"] = payments.request_registration_payment(conn, uid, phone_n, fee)
    else:
        payments.activate_user(conn, uid)
        out["status"] = "active"
    audit(conn, registered_by or uid, "user.register", "user", uid, {"role": role})
    return out


def resend_registration_payment(conn, user):
    if user["status"] != "pending_payment":
        raise RegistrationError("not_pending")
    return payments.request_registration_payment(conn, user["id"], user["phone"], get_fee(conn, "registration_fee"))


def create_superadmin(conn, name, phone, password):
    phone_n = normalize_phone(phone)
    if not phone_n or len(password) < 8:
        raise RegistrationError("bad_input")
    cur = conn.execute(
        "INSERT INTO users(role,name,phone,password_hash,language,status,created_at) VALUES('superadmin',?,?,?,'rw','active',?)",
        (name, phone_n, hash_password(password), iso(utcnow())))
    audit(conn, cur.lastrowid, "superadmin.create", "user", cur.lastrowid)
    return cur.lastrowid


def create_staff(conn, actor, *, role, name, phone, password, location_id=None):
    """SuperAdmin creates admin/agent/gate/government. Admin may create only agent/gate."""
    allowed = {"superadmin": ("admin", "agent", "gate", "government"), "admin": ("agent", "gate")}.get(actor["role"], ())
    if role not in allowed:
        raise PermissionError("not_allowed_to_create_" + role)
    phone_n = normalize_phone(phone)
    if not phone_n or not password or len(password) < 8 or len((name or "").strip()) < 2:
        raise RegistrationError("bad_input")
    if get_user_by_phone(conn, phone_n):
        raise RegistrationError("duplicate")
    cur = conn.execute(
        "INSERT INTO users(role,name,phone,password_hash,language,location_id,status,created_at) "
        "VALUES(?,?,?,?,'rw',?,'active',?)",
        (role, name.strip(), phone_n, hash_password(password), location_id, iso(utcnow())))
    audit(conn, actor["id"], "staff.create", "user", cur.lastrowid, {"role": role})
    return cur.lastrowid


def set_user_status(conn, actor, user_id, status):
    if status not in ("active", "suspended"):
        raise ValueError("bad_status")
    target = get_user(conn, user_id)
    if target is None:
        raise ValueError("not_found")
    if target["id"] == actor["id"] or target["role"] == "superadmin":
        raise PermissionError("cannot_change_superadmin_or_self")
    if actor["role"] == "admin" and target["role"] in ("admin",):
        raise PermissionError("admin_cannot_change_admin")
    if actor["role"] not in ("superadmin", "admin"):
        raise PermissionError("forbidden")
    conn.execute("UPDATE users SET status=? WHERE id=?", (status, user_id))
    audit(conn, actor["id"], "user.status", "user", user_id, {"status": status})


def change_password(conn, user, current, new):
    """Staff and buyers change their own password. The current one must be right."""
    from .security import verify_password
    if not user.get("password_hash") and not conn.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()[0]:
        raise ValueError("no_password_account")
    stored = conn.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()[0]
    if not verify_password(current or "", stored):
        raise ValueError("wrong_current_password")
    if not new or len(new) < 8 or new == current:
        raise ValueError("weak_password")
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new), user["id"]))
    audit(conn, user["id"], "user.change_password", "user", user["id"])
