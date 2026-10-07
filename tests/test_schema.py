import re
import unittest

from app import db


class SchemaTests(unittest.TestCase):
    def test_references_point_to_tables_created_earlier(self):
        """PostgreSQL (unlike SQLite) refuses a FOREIGN KEY to a table that does not exist yet."""
        created = []
        for m in re.finditer(r"CREATE TABLE IF NOT EXISTS (\w+)\((.*?)\n\);", db.SCHEMA, re.S):
            name, body = m.group(1), m.group(2)
            for ref in re.findall(r"REFERENCES (\w+)\(", body):
                self.assertIn(ref, created, f"{name} references {ref} before it is created")
            created.append(name)
        self.assertGreater(len(created), 10)

    def test_postgres_schema_has_no_sqlite_types(self):
        sql = db.schema_for_postgres()
        for bad in ("AUTOINCREMENT", " REAL", " INTEGER"):
            self.assertNotIn(bad, sql)
        self.assertIn("BIGSERIAL PRIMARY KEY", sql)

    def test_translate_sql(self):
        self.assertEqual(db.translate_sql("SELECT * FROM users WHERE id=?")[0], "SELECT * FROM users WHERE id=%s")
        q, ret = db.translate_sql("INSERT INTO users(name) VALUES(?)")
        self.assertTrue(q.endswith("RETURNING id") and ret)
        q, ret = db.translate_sql("INSERT OR IGNORE INTO fee_config(key,value,updated_at) VALUES(?,?,?)")
        self.assertTrue(q.startswith("INSERT INTO fee_config") and q.endswith("ON CONFLICT DO NOTHING") and not ret)
        q, ret = db.translate_sql("INSERT OR IGNORE INTO locations(village) VALUES(?)")
        self.assertTrue(q.endswith("ON CONFLICT DO NOTHING RETURNING id") and ret)
        with self.assertRaises(ValueError):
            db.translate_sql("SELECT * FROM users WHERE name LIKE 'a%'")

    def test_row_works_by_name_and_index(self):
        r = db.PgRow([("a", 1), ("b", 2)])
        self.assertEqual((r["a"], r[1], dict(r)), (1, 2, {"a": 1, "b": 2}))


if __name__ == "__main__":
    unittest.main()
