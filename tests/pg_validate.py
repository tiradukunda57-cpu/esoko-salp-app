"""Validate every SQL statement the test-suite runs against REAL PostgreSQL.
1. Runs all unit tests while recording each SQL text sent through the app's connection.
2. Translates them exactly as the Neon adapter does, creates the translated schema in the given database,
   and PREPAREs each statement (PostgreSQL parses and type-checks it without needing data).
Usage: python3 tests/pg_validate.py "postgresql://user@host:port/db"   (an empty scratch database)"""
import re, sqlite3, subprocess, sys, unittest
sys.path.insert(0, ".")

SEEN = {}
class Rec(sqlite3.Connection):
    def execute(self, sql, *a):
        SEEN.setdefault(sql, 0); SEEN[sql] += 1
        return super().execute(sql, *a)
_orig = sqlite3.connect
sqlite3.connect = lambda *a, **k: _orig(*a, **{**k, "factory": Rec})

import json, os
suite = unittest.defaultTestLoader.discover("tests")
res = unittest.TextTestRunner(stream=open("/dev/null", "w")).run(suite)
print("tests run:", res.testsRun, "failures:", len(res.failures) + len(res.errors))

if os.path.exists("/var/tmp/ui_sql.json"):  # SQL seen while the real pages were driven in a browser
    for q in json.load(open("/var/tmp/ui_sql.json")): SEEN.setdefault(q, 0)
from app import db
url = sys.argv[1]
def psql(sql):
    return subprocess.run(["psql", url, "-v", "ON_ERROR_STOP=1", "-X", "-q"], input=sql, text=True, capture_output=True)
r = psql(db.schema_for_postgres())
if r.returncode:
    print("SCHEMA FAILED:", r.stderr); sys.exit(1)
print("schema ok:", len(db.table_names()), "tables")

bad, n = [], 0
for raw in SEEN:
    if not raw.strip().upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")):
        continue
    try:
        pg, _ = db.translate_sql(raw)
    except ValueError as e:
        bad.append((raw, str(e))); continue
    cnt = [0]
    def num(_):
        cnt[0] += 1; return f"${cnt[0]}"
    body = re.sub(r"%s", num, pg)
    r = psql(f"PREPARE s{n} AS {body};\nDEALLOCATE s{n};")
    n += 1
    if r.returncode:
        bad.append((pg, r.stderr.strip().splitlines()[0] if r.stderr else "?"))
print("statements checked:", n, "problems:", len(bad))
for sql, err in bad:
    print("\n--", err, "\n", sql[:400])
sys.exit(1 if bad else 0)
