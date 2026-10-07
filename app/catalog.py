"""Product categories (all crops and all livestock). Stored in the database so the SuperAdmin can add more
(e.g. milk, honey, coffee) without changing code."""
import re

from .db import audit
from .i18n import LANGS

UNITS = ("sack", "bunch", "kg", "head")


def get_category(conn, code, include_inactive=False):
    q = "SELECT * FROM categories WHERE code=?" + ("" if include_inactive else " AND active=1")
    return conn.execute(q, (code,)).fetchone()


def list_categories(conn, group=None, include_inactive=False):
    q, a = "SELECT * FROM categories WHERE 1=1", []
    if not include_inactive:
        q += " AND active=1"
    if group:
        q += " AND grp=?"
        a.append(group)
    return conn.execute(q + " ORDER BY grp, sort_order, code", a).fetchall()


def label(row, lang):
    return row["name_" + lang] if lang in LANGS else row["name_en"]


def add_category(conn, actor, *, code, grp, prefix, unit, name_rw, name_en, name_fr):
    if actor["role"] != "superadmin":
        raise PermissionError("only_superadmin")
    if not re.fullmatch(r"[a-z_]{3,30}", code or ""):
        raise ValueError("bad_code")
    if grp not in ("crop", "livestock") or unit not in UNITS:
        raise ValueError("bad_group_or_unit")
    if not re.fullmatch(r"[A-Z]{3}", prefix or ""):
        raise ValueError("prefix_must_be_3_capital_letters")
    if conn.execute("SELECT 1 FROM categories WHERE code=? OR prefix=?", (code, prefix)).fetchone():
        raise ValueError("category_exists")
    nxt = conn.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM categories").fetchone()[0]
    conn.execute("INSERT INTO categories(code,grp,prefix,unit,name_rw,name_en,name_fr,sort_order) VALUES(?,?,?,?,?,?,?,?)",
                 (code, grp, prefix, unit, name_rw, name_en, name_fr, nxt))
    audit(conn, actor["id"], "category.add", "category", code)


def set_category_active(conn, actor, code, active):
    if actor["role"] != "superadmin":
        raise PermissionError("only_superadmin")
    if not get_category(conn, code, include_inactive=True):
        raise ValueError("not_found")
    conn.execute("UPDATE categories SET active=? WHERE code=?", (1 if active else 0, code))
    audit(conn, actor["id"], "category.active", "category", code, {"active": bool(active)})
