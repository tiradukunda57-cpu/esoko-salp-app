import time
import unittest
from datetime import timedelta

from app import checkup, fees, market, payments, reports, security, ussd, users
from app.db import connect, init_db
from app.util import iso, utcnow


def new_db():
    import os
    if os.environ.get("ESOKO_TEST_PG_EMULATION"):  # run the whole suite through the PostgreSQL code path
        from app.db import PgConnection
        from tests import fake_psycopg2
        fake_psycopg2.install()
        c = PgConnection("postgresql://emulated")
    else:
        c = connect(":memory:")
    init_db(c)
    return c


def add_location(c, village="Mana", cell="Mugano", sector="Ngororero", district="Ngororero"):
    return c.execute("INSERT INTO locations(village,cell,sector,district) VALUES(?,?,?,?)",
                     (village, cell, sector, district)).lastrowid


def activate(c, role, name, phone, nid, loc=None, password=None):
    r = users.register_user(c, role=role, name=name, phone=phone, national_id=nid, location_id=loc,
                            password=password)
    payments.on_payment_result(c, r["payment_ref"], True)
    return r["user_id"]


def world():
    c = new_db()
    loc = add_location(c)
    sa = users.get_user(c, users.create_superadmin(c, "Owner", "0788000001", "supersecret1"))
    agent_id = users.create_staff(c, sa, role="agent", name="Agent One", phone="0788000002",
                                  password="agentpass1", location_id=loc)
    farmer = activate(c, "farmer", "Jean Claude", "0788000003", "1199880012345678", loc)
    buyer = activate(c, "buyer", "Kigali Buyer", "0788000004", "1198070012345678", loc, "buyerpass1")
    return c, loc, sa, users.get_user(c, agent_id), farmer, buyer


class SecurityTests(unittest.TestCase):
    def test_password(self):
        h = security.hash_password("abc12345")
        self.assertTrue(security.verify_password("abc12345", h))
        self.assertFalse(security.verify_password("wrong", h))

    def test_token(self):
        tok = security.make_token(5, "agent", "s")
        self.assertEqual(security.decode_token(tok, "s")["sub"], 5)
        self.assertIsNone(security.decode_token(tok, "other"))
        self.assertIsNone(security.decode_token(tok + "x", "s"))
        self.assertIsNone(security.decode_token(tok, "s", now=time.time() + 10 * 3600))


class FeeTests(unittest.TestCase):
    def test_defaults_and_permissions(self):
        c, loc, sa, agent, farmer, buyer = world()
        self.assertEqual(fees.get_fee(c, "registration_fee"), 500)
        with self.assertRaises(PermissionError):
            fees.set_fee(c, dict(agent), "listing_fee", 1)
        fees.set_fee(c, dict(sa), "listing_fee", 30)
        self.assertEqual(fees.get_fee(c, "listing_fee"), 30)
        with self.assertRaises(ValueError):
            fees.set_fee(c, dict(sa), "commission_bps", 5000)
        self.assertEqual(fees.commission_for(60000, 200), 1200)


class RegistrationTests(unittest.TestCase):
    def test_pending_until_paid(self):
        c = new_db()
        r = users.register_user(c, role="farmer", name="Alice U", phone="0788111111", national_id="1199880012345678")
        self.assertEqual(r["fee"], 500)
        self.assertEqual(users.get_user(c, r["user_id"])["status"], "pending_payment")
        self.assertEqual(payments.on_payment_result(c, r["payment_ref"], True), "ok")
        self.assertEqual(users.get_user(c, r["user_id"])["status"], "active")
        self.assertEqual(payments.on_payment_result(c, r["payment_ref"], True), "ignored")  # idempotent
        self.assertEqual(reports.summary(c)["income"]["registration_fees"], 500)

    def test_validation_and_duplicates(self):
        c = new_db()
        base = dict(role="farmer", name="Alice U", phone="0788111111", national_id="1199880012345678")
        users.register_user(c, **base)
        for bad in ({"phone": "123"}, {"national_id": "123"}, {"name": "A"}):
            with self.assertRaises(users.RegistrationError):
                users.register_user(c, **{**base, **bad, "phone": bad.get("phone", "0788222222")})
        with self.assertRaises(users.RegistrationError):
            users.register_user(c, **{**base, "phone": "0788333333"})  # same ID
        with self.assertRaises(users.RegistrationError):
            users.register_user(c, **{**base, "national_id": "1199880099999999"})  # same phone
        row = c.execute("SELECT * FROM users").fetchone()
        self.assertNotIn("1199880012345678", str(dict(row)))  # full ID never stored

    def test_failed_payment_stays_pending(self):
        c = new_db()
        r = users.register_user(c, role="farmer", name="Alice U", phone="0788111111", national_id="1199880012345678")
        payments.on_payment_result(c, r["payment_ref"], False)
        self.assertEqual(users.get_user(c, r["user_id"])["status"], "pending_payment")

    def test_zero_fee_activates_immediately(self):
        c, loc, sa, *_ = world()
        fees.set_fee(c, dict(sa), "registration_fee", 0)
        r = users.register_user(c, role="farmer", name="Bob K", phone="0788555555", national_id="1199880055555555")
        self.assertEqual(r["status"], "active")


class MarketTests(unittest.TestCase):
    def test_full_flow_and_money_split(self):
        c, loc, sa, agent, farmer, buyer = world()
        p = market.create_product(c, farmer, "potatoes", 5, 12000)  # total 60000
        self.assertTrue(p["code"].startswith("POT-"))
        order = market.place_order(c, buyer, p["id"])
        self.assertEqual(order["total"], 60000)
        with self.assertRaises(market.MarketError):  # no double buying
            market.place_order(c, buyer, p["id"])
        payments.on_payment_result(c, order["payment_ref"], True)
        self.assertEqual(c.execute("SELECT status FROM products WHERE id=?", (p["id"],)).fetchone()[0], "Sold")
        self.assertEqual(market.list_available(c), [])
        self.assertEqual(len(market.agent_queue(c, dict(agent))), 1)
        market.agent_verify(c, dict(agent), p["id"], "approve", grade="A")
        res = market.confirm_handover(c, dict(agent), order["order_id"])
        self.assertEqual(res["commission"], 1200)
        self.assertEqual(res["fees_deducted"], 20)
        self.assertEqual(res["payout"], 60000 - 1200 - 20)
        self.assertEqual(res["payout"] + res["commission"] + res["fees_deducted"], 60000)
        s = reports.summary(c)
        self.assertEqual(s["gmv_completed"], 60000)
        self.assertEqual(s["income"]["commission"], 1200)
        with self.assertRaises(market.MarketError):  # cannot be paid twice
            market.confirm_handover(c, dict(agent), order["order_id"])

    def test_downgrade_accept_refunds_difference(self):
        c, loc, sa, agent, farmer, buyer = world()
        p = market.create_product(c, farmer, "beans", 10, 1000)  # 10000
        o = market.place_order(c, buyer, p["id"])
        payments.on_payment_result(c, o["payment_ref"], True)
        with self.assertRaises(market.MarketError):
            market.agent_verify(c, dict(agent), p["id"], "downgrade", grade="B", new_price=1500)
        market.agent_verify(c, dict(agent), p["id"], "downgrade", grade="B", new_price=800)
        market.respond_to_revision(c, buyer, o["order_id"], True)
        refund = c.execute("SELECT amount FROM transactions WHERE type='refund'").fetchone()[0]
        self.assertEqual(refund, 2000)
        res = market.confirm_handover(c, dict(agent), o["order_id"])
        self.assertEqual(res["commission"], 160)  # 2% of 8000

    def test_downgrade_decline_relists(self):
        c, loc, sa, agent, farmer, buyer = world()
        p = market.create_product(c, farmer, "beans", 10, 1000)
        o = market.place_order(c, buyer, p["id"])
        payments.on_payment_result(c, o["payment_ref"], True)
        market.agent_verify(c, dict(agent), p["id"], "downgrade", grade="B", new_price=500)
        market.respond_to_revision(c, buyer, o["order_id"], False)
        self.assertEqual(c.execute("SELECT amount FROM transactions WHERE type='refund'").fetchone()[0], 10000)
        self.assertEqual(len(market.list_available(c)), 1)

    def test_reject_refunds_all(self):
        c, loc, sa, agent, farmer, buyer = world()
        p = market.create_product(c, farmer, "beans", 2, 1000)
        o = market.place_order(c, buyer, p["id"])
        payments.on_payment_result(c, o["payment_ref"], True)
        market.agent_verify(c, dict(agent), p["id"], "reject", note="rotten")
        self.assertEqual(c.execute("SELECT amount FROM transactions WHERE type='refund'").fetchone()[0], 2000)

    def test_agent_outside_area_blocked(self):
        c, loc, sa, agent, farmer, buyer = world()
        other = add_location(c, "Kabaya", "Kabaya", "Kabaya", "Ngororero")
        far_farmer = activate(c, "farmer", "Far Farmer", "0788000009", "1199880099999991", other)
        p = market.create_product(c, far_farmer, "beans", 2, 1000)
        o = market.place_order(c, buyer, p["id"])
        payments.on_payment_result(c, o["payment_ref"], True)
        with self.assertRaises(PermissionError):
            market.agent_verify(c, dict(agent), p["id"], "approve")

    def test_unpaid_reservation_released(self):
        c, loc, sa, agent, farmer, buyer = world()
        p = market.create_product(c, farmer, "peas", 1, 5000)
        market.place_order(c, buyer, p["id"])
        self.assertEqual(market.list_available(c), [])
        self.assertEqual(market.release_stale_reservations(c, now=utcnow() + timedelta(minutes=31)), 1)
        self.assertEqual(len(market.list_available(c)), 1)

    def test_failed_escrow_relists(self):
        c, loc, sa, agent, farmer, buyer = world()
        p = market.create_product(c, farmer, "peas", 1, 5000)
        o = market.place_order(c, buyer, p["id"])
        payments.on_payment_result(c, o["payment_ref"], False)
        self.assertEqual(len(market.list_available(c)), 1)

    def test_inactive_farmer_cannot_list(self):
        c = new_db()
        r = users.register_user(c, role="farmer", name="Alice U", phone="0788111111", national_id="1199880012345678")
        with self.assertRaises(market.MarketError):
            market.create_product(c, r["user_id"], "beans", 1, 100)


class CheckupTests(unittest.TestCase):
    def test_checkup_sold_unsold_clearance(self):
        c, loc, sa, agent, farmer, buyer = world()
        sold = market.create_product(c, farmer, "potatoes", 5, 12000)
        unsold1 = market.create_product(c, farmer, "beans", 3, 1000)
        unsold2 = market.create_product(c, farmer, "goat", 1, 40000)
        o = market.place_order(c, buyer, sold["id"])
        payments.on_payment_result(c, o["payment_ref"], True)
        c.execute("DELETE FROM notifications")
        now = utcnow()
        s = checkup.run_checkup(c, now=now)
        self.assertEqual(s["totals"]["sold_items"], 1)
        self.assertEqual(s["totals"]["unsold_items"], 2)
        msgs = [r["text"] for r in c.execute("SELECT text FROM notifications")]
        self.assertEqual(len(msgs), 2)  # 1 congratulations + 1 aggregated unsold SMS
        self.assertTrue(any("Turakwishimiye" in m for m in msgs))
        again = checkup.run_checkup(c, now=now)  # idempotent
        self.assertEqual(again["totals"]["sold_items"], 0)
        self.assertEqual(again["totals"]["unsold_items"], 0)
        code = s["unsold"][0]["clearance"]
        self.assertEqual(checkup.verify_clearance(c, code, consume=False, now=now)["status"], "valid")
        self.assertEqual(checkup.verify_clearance(c, code, now=now)["status"], "valid")
        self.assertEqual(checkup.verify_clearance(c, code, now=now)["status"], "used")  # single use
        code2 = s["unsold"][1]["clearance"]
        self.assertEqual(checkup.verify_clearance(c, code2, now=now + timedelta(days=3))["status"], "expired")
        self.assertEqual(checkup.verify_clearance(c, "000000", now=now)["status"], "unknown")


class UssdTests(unittest.TestCase):
    def test_register_via_ussd_then_list(self):
        c = new_db()
        add_location(c, "Mana")
        ph = "+250788777777"
        self.assertTrue(ussd.handle(c, ph, "").startswith("CON "))
        self.assertIn("Umuguzi", ussd.handle(c, ph, "1"))
        self.assertIn("16", ussd.handle(c, ph, "1*1"))
        self.assertTrue(ussd.handle(c, ph, "1*1*1199880012345678").startswith("CON "))
        self.assertIn("Ngororero", ussd.handle(c, ph, "1*1*1199880012345678*Jean Claude"))
        self.assertIn("Mana", ussd.handle(c, ph, "1*1*1199880012345678*Jean Claude*1"))
        self.assertIn("500", ussd.handle(c, ph, "1*1*1199880012345678*Jean Claude*1*1"))
        end = ussd.handle(c, ph, "1*1*1199880012345678*Jean Claude*1*1*1")
        self.assertTrue(end.startswith("END "))
        u = users.get_user_by_phone(c, ph)
        self.assertEqual(u["status"], "pending_payment")
        self.assertTrue(ussd.handle(c, ph, "").startswith("CON "))  # pending menu
        ref = c.execute("SELECT provider_ref FROM transactions WHERE user_id=?", (u["id"],)).fetchone()[0]
        payments.on_payment_result(c, ref, True)
        self.assertIn("Ibihingwa", ussd.handle(c, ph, "1"))
        self.assertIn("Ibirayi", ussd.handle(c, ph, "1*1"))
        self.assertTrue(ussd.handle(c, ph, "1*1*1*5*30000").startswith("CON "))
        done = ussd.handle(c, ph, "1*1*1*5*30000*1")
        self.assertIn("POT-", done)
        self.assertIn("POT-", ussd.handle(c, ph, "2"))
        self.assertIn("30000", ussd.handle(c, ph, "3"))
        self.assertTrue(ussd.handle(c, ph, "9").startswith("END "))

    def test_duplicate_and_bad_input(self):
        c = new_db()
        add_location(c, "Mana")
        activate(c, "farmer", "Existing F", "0788777777", "1199880012345678")
        self.assertTrue(ussd.handle(c, "+250788999999", "2*1*123").startswith("END "))
        dup = ussd.handle(c, "+250788999999", "2*1*1199880012345678*Someone Else*1*1*1")
        self.assertTrue(dup.startswith("END "))

    def test_staff_blocked_on_ussd(self):
        c, loc, sa, agent, farmer, buyer = world()
        self.assertTrue(ussd.handle(c, "+250788000002", "").startswith("END "))


if __name__ == "__main__":
    unittest.main()
