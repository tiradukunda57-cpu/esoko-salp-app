"""A stand-in for psycopg2 that runs the *translated PostgreSQL text* on SQLite.
It is not PostgreSQL, but it proves that our SQL translation + the PgConnection wrapper (RETURNING id, ON CONFLICT,
%s placeholders, row access by name and index, script splitting) work through the whole test-suite."""
import re
import sqlite3
import sys
import types

STATEMENTS = []


class _Cursor:
    def __init__(self, raw):
        self._raw = raw
        self._c = None

    def execute(self, sql, params=()):
        STATEMENTS.append(sql)
        assert "?" not in sql.replace("'?'", ""), f"untranslated placeholder: {sql}"
        s = sql.replace("%s", "?")
        s = s.replace("BIGSERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
        s = re.sub(r"\bBIGINT\b", "INTEGER", s)
        s = s.replace("DOUBLE PRECISION", "REAL")
        self._c = self._raw.execute(s, tuple(params))

    @property
    def description(self):
        return self._c.description if self._c else None

    @property
    def rowcount(self):
        return self._c.rowcount

    def fetchone(self):
        return self._c.fetchone()

    def fetchall(self):
        return self._c.fetchall()

    def close(self):
        pass


class _Conn:
    def __init__(self):
        self._raw = sqlite3.connect(":memory:", check_same_thread=False)
        self._raw.execute("PRAGMA foreign_keys=ON")

    def cursor(self):
        return _Cursor(self._raw)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()


def install():
    mod = types.ModuleType("psycopg2")
    mod.connect = lambda url, **kw: _Conn()
    sys.modules["psycopg2"] = mod
