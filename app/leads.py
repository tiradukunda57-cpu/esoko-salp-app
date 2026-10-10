"""Unfinished sign-ups. USSD sessions that stop half-way leave a lead so an Admin can phone the person and help."""
from .util import iso, utcnow


def track(conn, phone, step, **fields):
    now = iso(utcnow())
    row = conn.execute("SELECT id FROM signup_leads WHERE phone=?", (phone,)).fetchone()
    cols = {k: v for k, v in fields.items() if k in ("role", "name", "language", "location_id") and v is not None}
    if row is None:
        keys = ["phone", "step", "created_at", "updated_at"] + list(cols)
        conn.execute("INSERT INTO signup_leads(%s) VALUES(%s)" % (",".join(keys), ",".join("?" * len(keys))),
                     [phone, step, now, now] + list(cols.values()))
    else:
        sets = ["step=?", "completed=0", "updated_at=?"] + [k + "=?" for k in cols]
        conn.execute("UPDATE signup_leads SET " + ",".join(sets) + " WHERE id=?", [step, now] + list(cols.values()) + [row["id"]])


def complete(conn, phone):
    conn.execute("UPDATE signup_leads SET completed=1, step='done', updated_at=? WHERE phone=?", (iso(utcnow()), phone))


def list_open(conn):
    """-> {'unfinished': people who stopped half-way, 'unpaid': registered but registration fee not yet paid}"""
    unfinished = [dict(r) for r in conn.execute(
        "SELECT s.phone,s.role,s.name,s.language,s.step,s.created_at,s.updated_at,l.village,l.sector,l.district "
        "FROM signup_leads s LEFT JOIN locations l ON l.id=s.location_id WHERE s.completed=0 "
        "AND NOT EXISTS (SELECT 1 FROM users u WHERE u.phone=s.phone) ORDER BY s.updated_at DESC LIMIT 200")]
    unpaid = [dict(r) for r in conn.execute(
        "SELECT u.phone,u.role,u.name,u.language,u.created_at,l.village,l.sector,l.district FROM users u "
        "LEFT JOIN locations l ON l.id=u.location_id WHERE u.status='pending_payment' ORDER BY u.id DESC LIMIT 200")]
    return {"unfinished": unfinished, "unpaid": unpaid}
