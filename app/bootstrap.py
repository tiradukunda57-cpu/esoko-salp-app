"""Start-up tasks that replace the terminal on a hosted server (Render has no shell on the free plan)."""
import logging

from .config import get_settings
from .users import RegistrationError, create_superadmin, get_user_by_phone, normalize_phone

log = logging.getLogger("esoko.bootstrap")


def run(conn):
    """Idempotent. Seeds the pilot village and, when no SuperAdmin exists yet, creates one from the environment."""
    if not conn.execute("SELECT 1 FROM locations LIMIT 1").fetchone():
        conn.execute("INSERT INTO locations(village,cell,sector,district) VALUES('Mana','Mugano','Ngororero','Ngororero')")
    s = get_settings()
    created = None
    if s.bootstrap_phone and s.bootstrap_password and not conn.execute("SELECT 1 FROM users WHERE role='superadmin'").fetchone():
        phone = normalize_phone(s.bootstrap_phone)
        if phone and get_user_by_phone(conn, phone):
            log.warning("bootstrap skipped: %s is already used by another account", phone)
        else:
            try:
                created = create_superadmin(conn, s.bootstrap_name or "Owner", s.bootstrap_phone, s.bootstrap_password)
                log.warning("SuperAdmin created for %s. Remove ESOKO_BOOTSTRAP_PASSWORD from the environment now.", phone)
            except RegistrationError as e:
                log.warning("bootstrap SuperAdmin not created: %s (phone must look like 07XXXXXXXX, password 8+ characters)", e)
    conn.commit()
    return created
