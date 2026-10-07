import os
import unittest

from tests import stub_web

stub_web.install()
from app import api  # noqa: E402  (imported with the stand-in web framework)
from app import checkup, market, payments  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.users import get_user  # noqa: E402
from tests.test_core import world  # noqa: E402


def env(**kw):
    class Ctx:
        def __enter__(self):
            self.old = {k: os.environ.get(k) for k in kw}
            os.environ.update({k: v for k, v in kw.items()})

        def __exit__(self, *a):
            for k, v in self.old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    return Ctx()


class ApiLogicTests(unittest.TestCase):
    def setUp(self):
        self.c, self.loc, self.sa, self.agent, self.farmer, self.buyer = world()
        self.sa_d, self.agent_d = dict(self.sa), dict(self.agent)
        api._FAILS.clear()

    def test_db_explorer_hides_secrets_and_is_superadmin_only(self):
        t = api.db_tables(user=self.sa_d, conn=self.c)
        names = {x["name"]: x["rows"] for x in t["tables"]}
        self.assertGreaterEqual(names["users"], 4)
        out = api.db_rows("users", user=self.sa_d, conn=self.c)
        self.assertNotIn("password_hash", out["columns"])
        self.assertNotIn("national_id_hash", out["columns"])
        self.assertIn("password_hash", out["hidden"])
        self.assertIn("national_id_last4", out["columns"])
        self.assertEqual(out["total"], names["users"])
        found = api.db_rows("users", q="Kigali Buyer", user=self.sa_d, conn=self.c)
        self.assertEqual(found["total"], 1)
        with self.assertRaises(stub_web.HTTPException) as cm:
            api.db_rows("sqlite_master; DROP TABLE users", user=self.sa_d, conn=self.c)
        self.assertEqual(cm.exception.status_code, 404)
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM users").fetchone()[0], names["users"])

    def test_db_explorer_csv_blocks_formula_injection_and_is_audited(self):
        self.c.execute("UPDATE users SET name='=HYPERLINK(\"http://x\")' WHERE id=?", (self.farmer,))
        resp = api.db_rows("users", format="csv", user=self.sa_d, conn=self.c)
        text = resp.body
        self.assertIn("'=HYPERLINK", text)
        self.assertNotIn("password_hash", text.splitlines()[0])
        n = self.c.execute("SELECT COUNT(*) FROM audit_log WHERE action IN ('db.export','db.view')").fetchone()[0]
        self.assertGreaterEqual(n, 1)

    def test_test_mode_payment_confirmation(self):
        p = market.create_product(self.c, self.farmer, "potatoes", 5, 12000)
        o = market.place_order(self.c, self.buyer, p["id"])
        pend = api.pending_payments(user=self.sa_d, conn=self.c)
        self.assertEqual([x["provider_ref"] for x in pend], [o["payment_ref"]])
        res = api.confirm_payment(api.DevConfirmIn(provider_ref=o["payment_ref"], success=True), user=self.sa_d, conn=self.c)
        self.assertEqual(res["result"], "ok")
        self.assertEqual(api.pending_payments(user=self.sa_d, conn=self.c), [])
        with env(ESOKO_ENV="prod"):  # the live system never exposes these
            with self.assertRaises(stub_web.HTTPException):
                api.pending_payments(user=self.sa_d, conn=self.c)
            with self.assertRaises(stub_web.HTTPException):
                api.sms_outbox(user=self.sa_d, conn=self.c)

    def test_outbox_shows_login_codes_in_test_mode_only(self):
        from app import portal
        portal.request_otp(self.c, "0788000003")
        rows = api.sms_outbox(user=self.sa_d, conn=self.c)
        self.assertTrue(any("kode" in r["text"] or "code" in r["text"] for r in rows))

    def test_public_config(self):
        cfg = api.public_config(conn=self.c)
        self.assertEqual(cfg["registration_fee"], 500)
        self.assertTrue(cfg["test_payments"] and cfg["ussd_simulator"])
        with env(ESOKO_ENV="prod"):
            cfg = api.public_config(conn=self.c)
            self.assertFalse(cfg["test_payments"] or cfg["ussd_simulator"])
            self.assertEqual(cfg["mode"], "live")

    def test_jobs_need_the_secret(self):
        with self.assertRaises(stub_web.HTTPException):  # no secret configured -> always refused
            api.run_job("checkup", x_job_secret="anything", conn=self.c)
        with env(ESOKO_JOB_SECRET="s3cret-value"):
            with self.assertRaises(stub_web.HTTPException):
                api.run_job("checkup", x_job_secret="wrong", conn=self.c)
            with self.assertRaises(stub_web.HTTPException):
                api.run_job("checkup", x_job_secret=None, conn=self.c)
            market.create_product(self.c, self.farmer, "beans", 3, 1000)
            out = api.run_job("checkup", x_job_secret="s3cret-value", conn=self.c)
            self.assertEqual(out["result"]["unsold_items"], 1)
            again = api.run_job("checkup", x_job_secret="s3cret-value", conn=self.c)
            self.assertEqual(again["result"]["unsold_items"], 0)
            self.assertIn("released_reservations", api.run_job("housekeeping", x_job_secret="s3cret-value", conn=self.c)["result"])
            with self.assertRaises(stub_web.HTTPException):
                api.run_job("drop-everything", x_job_secret="s3cret-value", conn=self.c)

    def test_login_is_throttled(self):
        body = api.LoginIn(phone="0788000002", password="wrong-password")
        for _ in range(8):
            with self.assertRaises(stub_web.HTTPException) as cm:
                api.login(body, conn=self.c)
            self.assertEqual(cm.exception.status_code, 401)
        with self.assertRaises(stub_web.HTTPException) as cm:
            api.login(api.LoginIn(phone="0788000002", password="agentpass1"), conn=self.c)
        self.assertEqual(cm.exception.status_code, 429)

    def test_agent_sees_only_farmers_of_own_sector(self):
        from tests.test_core import activate, add_location
        other = add_location(self.c, "Kabaya", "Kabaya", "Kabaya", "Ngororero")
        activate(self.c, "farmer", "Far Farmer", "0788000009", "1199880099999991", other)
        mine = api.agent_farmers(user=self.agent_d, conn=self.c)
        self.assertEqual([f["name"] for f in mine], ["Jean Claude"])
        self.assertEqual(len(api.agent_farmers(user=self.sa_d, conn=self.c)), 2)
        self.assertEqual(len(api.agent_farmers(q="Far", user=self.sa_d, conn=self.c)), 1)

    def test_login_success_and_me(self):
        out = api.login(api.LoginIn(phone="0788000002", password="agentpass1"), conn=self.c)
        self.assertEqual(out["user"]["role"], "agent")
        self.assertNotIn("password_hash", out["user"])
        self.assertEqual(api.auth_me(user=self.agent_d)["user"]["name"], "Agent One")

    def test_every_page_route_has_a_file(self):
        from pathlib import Path
        pages = {"index.html", "farmer.html", "buyer.html", "agent.html", "admin.html", "dashboard.html", "ussd.html"}
        have = {p.name for p in Path(api.STATIC_DIR).glob("*.html")}
        self.assertTrue(pages <= have, f"missing pages: {pages - have}")


if __name__ == "__main__":
    unittest.main()
