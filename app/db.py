import json
import sqlite3

from .config import get_settings
from .util import iso, utcnow

SCHEMA = """
CREATE TABLE IF NOT EXISTS locations(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  village TEXT NOT NULL, cell TEXT NOT NULL, sector TEXT NOT NULL, district TEXT NOT NULL,
  lat REAL, lng REAL,
  UNIQUE(village, cell, sector, district)
);
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role TEXT NOT NULL CHECK(role IN ('superadmin','admin','agent','farmer','buyer','gate','government')),
  name TEXT NOT NULL,
  phone TEXT NOT NULL UNIQUE,
  national_id_hash TEXT UNIQUE,
  national_id_last4 TEXT,
  password_hash TEXT,
  language TEXT NOT NULL DEFAULT 'rw',
  location_id INTEGER REFERENCES locations(id),
  status TEXT NOT NULL DEFAULT 'pending_payment'
    CHECK(status IN ('pending_payment','active','suspended')),
  consent_at TEXT,
  must_change_password INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS categories(
  code TEXT PRIMARY KEY,
  grp TEXT NOT NULL CHECK(grp IN ('crop','livestock')),
  prefix TEXT NOT NULL UNIQUE,
  unit TEXT NOT NULL CHECK(unit IN ('sack','bunch','kg','head')),
  name_rw TEXT NOT NULL, name_en TEXT NOT NULL, name_fr TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS products(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  farmer_id INTEGER NOT NULL REFERENCES users(id),
  category TEXT NOT NULL REFERENCES categories(code),
  quantity REAL NOT NULL CHECK(quantity > 0),
  unit TEXT NOT NULL,
  price_per_unit INTEGER NOT NULL CHECK(price_per_unit > 0),
  grade TEXT,
  location_id INTEGER REFERENCES locations(id),
  status TEXT NOT NULL DEFAULT 'Available'
    CHECK(status IN ('Available','Reserved','Sold','Verified','PaidOut','Unsold','Rejected','Expired')),
  created_at TEXT NOT NULL,
  sold_notified_at TEXT,
  tag_number TEXT,
  sex TEXT,
  age_months INTEGER,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL REFERENCES products(id),
  buyer_id INTEGER NOT NULL REFERENCES users(id),
  total_amount INTEGER NOT NULL,
  revised_price INTEGER,
  revised_total INTEGER,
  status TEXT NOT NULL DEFAULT 'awaiting_payment'
    CHECK(status IN ('awaiting_payment','funded','revision_pending','verified','completed','cancelled','refunded')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_order ON orders(product_id)
  WHERE status IN ('awaiting_payment','funded','revision_pending','verified');
CREATE TABLE IF NOT EXISTS transactions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER REFERENCES users(id),
  order_id INTEGER REFERENCES orders(id),
  product_id INTEGER REFERENCES products(id),
  type TEXT NOT NULL CHECK(type IN
    ('registration_fee','escrow_in','payout','commission','listing_fee','clearance_fee','refund')),
  amount INTEGER NOT NULL CHECK(amount >= 0),
  msisdn TEXT,
  provider_ref TEXT,
  status TEXT NOT NULL CHECK(status IN ('pending','succeeded','failed','accrued','settled')),
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tx_ref ON transactions(provider_ref);
CREATE TABLE IF NOT EXISTS clearances(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL UNIQUE REFERENCES products(id),
  code TEXT NOT NULL UNIQUE,
  issued_at TEXT NOT NULL,
  valid_until TEXT NOT NULL,
  used_at TEXT,
  gate_user_id INTEGER REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS verifications(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL REFERENCES products(id),
  agent_id INTEGER NOT NULL REFERENCES users(id),
  result TEXT NOT NULL, grade TEXT, weight REAL, note TEXT, new_price INTEGER,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fee_config(
  key TEXT PRIMARY KEY, value INTEGER NOT NULL, updated_at TEXT NOT NULL, updated_by INTEGER
);
CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_id INTEGER, action TEXT NOT NULL, entity TEXT, entity_id TEXT, detail TEXT,
  created_at TEXT NOT NULL
);
-- Government/authorization rules. New rules are DATA, not code: add them through the admin API.
CREATE TABLE IF NOT EXISTS permit_types(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name_rw TEXT NOT NULL, name_en TEXT NOT NULL, name_fr TEXT NOT NULL,
  issuer TEXT,
  subject TEXT NOT NULL CHECK(subject IN ('user','product')),
  applies_to TEXT NOT NULL DEFAULT 'all',          -- all | crop | livestock | <category code>
  required_at TEXT NOT NULL CHECK(required_at IN ('listing','purchase','handover','market_entry')),
  role_scope TEXT CHECK(role_scope IN ('farmer','buyer')),
  mandatory INTEGER NOT NULL DEFAULT 0,             -- 1 = blocks the action when missing
  active INTEGER NOT NULL DEFAULT 0,                -- 0 = rule not in effect yet
  validity_days INTEGER,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS permits(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  permit_type_id INTEGER NOT NULL REFERENCES permit_types(id),
  user_id INTEGER REFERENCES users(id),
  product_id INTEGER REFERENCES products(id),
  reference TEXT,
  status TEXT NOT NULL DEFAULT 'approved' CHECK(status IN ('approved','revoked')),
  issued_by INTEGER REFERENCES users(id),
  issued_at TEXT NOT NULL,
  valid_until TEXT,
  note TEXT,
  CHECK((user_id IS NULL) != (product_id IS NULL))
);
CREATE TABLE IF NOT EXISTS otp_codes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phone TEXT NOT NULL, code_hash TEXT NOT NULL, expires_at TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0, used INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_otp_phone ON otp_codes(phone);
CREATE TABLE IF NOT EXISTS notifications(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  msisdn TEXT NOT NULL, text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
"""

# Money is stored as integer Frw. commission_bps: 200 = 2.00 %
DEFAULT_FEES = {"registration_fee": 500, "listing_fee": 20, "commission_bps": 200, "clearance_fee": 0}


# code, group, prefix, unit, Kinyarwanda, English, French   (French avoids characters outside GSM-7)
CATEGORIES = [
    ("potatoes", "crop", "POT", "sack", "Ibirayi", "Potatoes", "Pommes de terre"),
    ("beans", "crop", "BEA", "sack", "Ibishyimbo", "Beans", "Haricots"),
    ("maize", "crop", "MAI", "sack", "Ibigori", "Maize", "Mais"),
    ("peas", "crop", "PEA", "sack", "Amashaza", "Peas", "Petits pois"),
    ("banana", "crop", "BAN", "bunch", "Igitoki", "Cooking banana", "Bananes"),
    ("cassava", "crop", "CAS", "sack", "Imyumbati", "Cassava", "Manioc"),
    ("sorghum", "crop", "SOR", "sack", "Amasaka", "Sorghum", "Sorgho"),
    ("wheat", "crop", "WHE", "sack", "Ingano", "Wheat", "Blé"),
    ("tomato", "crop", "TOM", "kg", "Inyanya", "Tomatoes", "Tomates"),
    ("cabbage", "crop", "CAB", "kg", "Amashu", "Cabbage", "Choux"),
    ("carrot", "crop", "CAR", "kg", "Karoti", "Carrots", "Carottes"),
    ("onion", "crop", "ONI", "kg", "Ibitunguru", "Onions", "Oignons"),
    ("other_crop", "crop", "OCR", "sack", "Ibindi bihingwa", "Other crops", "Autres cultures"),
    ("cattle", "livestock", "COW", "head", "Inka", "Cattle", "Bovins"),
    ("goat", "livestock", "GOA", "head", "Ihene", "Goats", "Chèvres"),
    ("sheep", "livestock", "SHE", "head", "Intama", "Sheep", "Moutons"),
    ("pig", "livestock", "PIG", "head", "Ingurube", "Pigs", "Porcs"),
    ("chicken", "livestock", "CHI", "head", "Inkoko", "Chickens", "Poulets"),
    ("rabbit", "livestock", "RAB", "head", "Urukwavu", "Rabbits", "Lapins"),
    ("duck", "livestock", "DUC", "head", "Imbata", "Ducks", "Canards"),
    ("other_livestock", "livestock", "OLS", "head", "Andi matungo", "Other livestock", "Autres animaux"),
]

# PLACEHOLDER rules, all switched OFF. They show how a government requirement is modelled.
# Do NOT enable them until the real requirement is confirmed with the district / ministry.
# code, rw, en, fr, issuer, subject, applies_to, required_at, role_scope
PERMIT_TYPES = [
    ("livestock_keeper_registration", "Kwiyandikisha nk'umworozi", "Livestock keeper registration",
     "Enregistrement eleveur", "Sector veterinary / local authority", "user", "livestock", "listing", "farmer"),
    ("livestock_movement_permit", "Uruhushya rwo gutwara itungo", "Livestock movement permit",
     "Permis de deplacement du betail", "Sector veterinary officer", "product", "livestock", "handover", None),
    ("livestock_market_entry", "Icyemezo cyo kwinjiza itungo mu isoko", "Livestock market-entry authorization",
     "Autorisation d'entree au marche (betail)", "Sector veterinary officer", "product", "livestock", "market_entry", None),
    ("buyer_trade_licence", "Uruhushya rw'ubucuruzi bw'umuguzi", "Buyer trade licence",
     "Licence commerciale de l'acheteur", "District / RDB", "user", "all", "purchase", "buyer"),
]


# --------------------------------------------------------------------------- database connection
# SQLite (local, tests) and PostgreSQL (Neon, hosting) share the same SQL. The few differences are handled here:
#   ?  -> %s          INSERT OR IGNORE -> ON CONFLICT DO NOTHING          cursor.lastrowid -> INSERT ... RETURNING id
#   INTEGER -> BIGINT  AUTOINCREMENT -> BIGSERIAL                         REAL -> DOUBLE PRECISION
import re
from decimal import Decimal

_ID_TABLES = None


def _id_tables():
    global _ID_TABLES
    if _ID_TABLES is None:
        _ID_TABLES = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)\(\s*id INTEGER PRIMARY KEY AUTOINCREMENT", SCHEMA))
    return _ID_TABLES


def table_names():
    """Every table, read from the schema. The database explorer only ever touches names from this list."""
    return re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)\(", SCHEMA)


def schema_for_postgres(schema=None):
    sql = re.sub(r"--[^\n]*", "", schema or SCHEMA)
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
    sql = re.sub(r"\bINTEGER\b", "BIGINT", sql)
    sql = re.sub(r"\bREAL\b", "DOUBLE PRECISION", sql)
    return sql


def translate_sql(sql):
    """SQLite-style SQL -> PostgreSQL. Returns (sql, wants_returning_id)."""
    if "%" in sql:
        raise ValueError("a literal % is not allowed in SQL text; pass LIKE patterns as parameters")
    s = sql.strip().rstrip(";")
    upper = s.upper()
    ignore = upper.startswith("INSERT OR IGNORE INTO")
    if ignore:
        s = "INSERT INTO" + s[len("INSERT OR IGNORE INTO"):]
    s = s.replace("?", "%s")
    s = re.sub(r"\bLIKE\b", "ILIKE", s)  # SQLite LIKE ignores case; PostgreSQL needs ILIKE for the same behaviour
    returning = False
    m = re.match(r"INSERT\s+INTO\s+(\w+)", s, re.I)
    if ignore:
        s += " ON CONFLICT DO NOTHING"
    if m and m.group(1) in _id_tables() and "RETURNING" not in upper:
        s += " RETURNING id"
        returning = True
    return s, returning


class PgRow(dict):
    """Row that works like sqlite3.Row: row['name'] and row[0]."""
    __slots__ = ()

    def __getitem__(self, k):
        if isinstance(k, int):
            return list(self.values())[k]
        return super().__getitem__(k)


def _plain(v):
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    return v


class PgCursor:
    def __init__(self, cur, lastrowid=None):
        self._cur = cur
        self.lastrowid = lastrowid
        self.rowcount = cur.rowcount
        self.description = cur.description

    def _row(self, r):
        return PgRow(zip([d[0] for d in self._cur.description], [_plain(v) for v in r]))

    def fetchone(self):
        if self._cur.description is None:
            return None
        r = self._cur.fetchone()
        return None if r is None else self._row(r)

    def fetchall(self):
        if self._cur.description is None:
            return []
        return [self._row(r) for r in self._cur.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


class PgConnection:
    dialect = "postgres"

    def __init__(self, url):
        import psycopg2  # installed from requirements.txt
        self._raw = psycopg2.connect(url, connect_timeout=10)

    def execute(self, sql, params=()):
        q, returning = translate_sql(sql)
        cur = self._raw.cursor()
        cur.execute(q, tuple(params))
        lastid = None
        if returning:
            row = cur.fetchone()
            lastid = row[0] if row else None
        return PgCursor(cur, lastid)

    def executescript(self, script):
        for stmt in schema_for_postgres(script).split(";"):
            if stmt.strip():
                cur = self._raw.cursor()
                cur.execute(stmt)
                cur.close()

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        try:
            self._raw.close()
        except Exception:
            pass


def dialect(conn):
    return getattr(conn, "dialect", "sqlite")


def connect(path=None):
    s = get_settings()
    if path is None and s.database_url:
        return PgConnection(s.database_url)
    path = path or s.db_path
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _has_column(conn, table, column):
    if dialect(conn) == "postgres":
        return conn.execute("SELECT 1 FROM information_schema.columns WHERE table_name=? AND column_name=?",
                            (table, column)).fetchone() is not None
    return any(r[1] == column for r in conn.execute("PRAGMA table_info(%s)" % table))


def migrate(conn):
    """Small, safe upgrades for databases created by an older version (hosting has no terminal)."""
    if not _has_column(conn, "users", "must_change_password"):
        conn.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")
        conn.commit()


def init_db(conn):
    conn.executescript(SCHEMA)
    migrate(conn)
    now = iso(utcnow())
    for k, v in DEFAULT_FEES.items():
        conn.execute("INSERT OR IGNORE INTO fee_config(key,value,updated_at) VALUES(?,?,?)", (k, v, now))
    for i, (code, grp, prefix, unit, rw, en, fr) in enumerate(CATEGORIES, 1):
        conn.execute("INSERT OR IGNORE INTO categories(code,grp,prefix,unit,name_rw,name_en,name_fr,sort_order) "
                     "VALUES(?,?,?,?,?,?,?,?)", (code, grp, prefix, unit, rw, en, fr, i))
    for code, rw, en, fr, issuer, subject, applies, stage, scope in PERMIT_TYPES:
        conn.execute("INSERT OR IGNORE INTO permit_types(code,name_rw,name_en,name_fr,issuer,subject,applies_to,"
                     "required_at,role_scope,mandatory,active,created_at) VALUES(?,?,?,?,?,?,?,?,?,0,0,?)",
                     (code, rw, en, fr, issuer, subject, applies, stage, scope, now))
    conn.commit()


def audit(conn, actor_id, action, entity=None, entity_id=None, detail=None):
    conn.execute(
        "INSERT INTO audit_log(actor_id,action,entity,entity_id,detail,created_at) VALUES(?,?,?,?,?,?)",
        (actor_id, action, entity, None if entity_id is None else str(entity_id),
         json.dumps(detail or {}, ensure_ascii=False), iso(utcnow())))
