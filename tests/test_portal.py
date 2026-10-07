import re
import unittest
from datetime import timedelta

from app import checkup, market, payments, permits, portal
from app.util import utcnow
from tests.test_core import activate, add_location, new_db, world


def last_code(c):
    text = c.execute("SELECT text FROM notifications ORDER BY id DESC LIMIT 1").fetchone()[0]
    return re.search(r"\b(\d{6})\b", text).group(1)


class OtpTests(unittest.TestCase):
    def test_login_with_sms_code(self):
        c, loc, sa, agent, farmer, buyer = world()
        c.execute("DELETE FROM notifications")
        self.assertTrue(portal.request_otp(c, "0788000003"))
        code = last_code(c)
        self.assertIsNone(portal.verify_otp(c, "0788000003", "000000"))
        u = portal.verify_otp(c, "0788000003", code)
        self.assertEqual(u["id"], farmer)
        self.assertIsNone(portal.verify_otp(c, "0788000003", code))  # a code works only once

    def test_unknown_staff_and_inactive_numbers_get_nothing(self):
        c, loc, sa, agent, farmer, buyer = world()
        c.execute("DELETE FROM notifications")
        self.assertFalse(portal.request_otp(c, "0788999999"))      # unknown
        self.assertFalse(portal.request_otp(c, "0788000002"))      # agent: password only
        self.assertFalse(portal.request_otp(c, "0788000001"))      # superadmin: password only
        self.assertEqual(c.execute("SELECT COUNT(*) FROM notifications").fetchone()[0], 0)

    def test_expiry_attempt_limit_and_rate_limit(self):
        c, loc, sa, agent, farmer, buyer = world()
        now = utcnow()
        portal.request_otp(c, "0788000003", now=now)
        code = last_code(c)
        self.assertIsNone(portal.verify_otp(c, "0788000003", code, now=now + timedelta(minutes=11)))  # expired
        portal.request_otp(c, "0788000003", now=now)
        good = last_code(c)
        for _ in range(5):
            portal.verify_otp(c, "0788000003", "111111", now=now)
        self.assertIsNone(portal.verify_otp(c, "0788000003", good, now=now))  # locked after 5 wrong guesses
        self.assertTrue(portal.request_otp(c, "0788000003", now=now))         # 3rd request is still allowed
        self.assertFalse(portal.request_otp(c, "0788000003", now=now))        # 4th within 10 min is refused


class PortalTests(unittest.TestCase):
    def test_farmer_overview(self):
        c, loc, sa, agent, farmer, buyer = world()
        sold = market.create_product(c, farmer, "potatoes", 5, 12000)
        market.create_product(c, farmer, "goat", 1, 40000)
        o = market.place_order(c, buyer, sold["id"])
        payments.on_payment_result(c, o["payment_ref"], True)
        s = checkup.run_checkup(c)
        d = portal.farmer_overview(c, dict(__import__("app.users", fromlist=["x"]).get_user(c, farmer)))
        self.assertEqual(d["totals"]["waiting_for_payment"], 60000)
        self.assertEqual(len(d["listings"]), 2)
        self.assertEqual(len(d["clearances"]), 1)
        self.assertEqual(d["profile"]["location"]["village"], "Mana")
        market.agent_verify(c, dict(agent), sold["id"], "approve", grade="A")
        market.confirm_handover(c, dict(agent), o["order_id"])
        d = portal.farmer_overview(c, dict(__import__("app.users", fromlist=["x"]).get_user(c, farmer)))
        self.assertEqual(d["totals"]["paid_out"], 60000 - 1200 - 40)
        self.assertEqual(d["totals"]["waiting_for_payment"], 0)
        self.assertEqual(len(d["payouts"]), 1)

    def test_farmer_sees_what_blocks_listing(self):
        c, loc, sa, agent, farmer, buyer = world()
        permits.update_type(c, dict(sa), "livestock_keeper_registration", active=True, mandatory=True)
        from app import users
        d = portal.farmer_overview(c, dict(users.get_user(c, farmer)))
        blocked = {b["category"] for b in d["listing_blocked"]}
        self.assertIn("goat", blocked)
        self.assertNotIn("potatoes", blocked)

    def test_buyer_overview_and_isolation(self):
        c, loc, sa, agent, farmer, buyer = world()
        from app import users
        p = market.create_product(c, farmer, "beans", 10, 1000)
        o = market.place_order(c, buyer, p["id"])
        payments.on_payment_result(c, o["payment_ref"], True)
        market.agent_verify(c, dict(agent), p["id"], "downgrade", grade="B", new_price=800)
        d = portal.buyer_overview(c, dict(users.get_user(c, buyer)))
        self.assertEqual(d["totals"]["needs_your_answer"], 1)
        self.assertEqual(d["orders"][0]["revised_total"], 8000)
        other = activate(c, "buyer", "Other Buyer", "0788000010", "1198070099999999", loc, "buyerpass2")
        self.assertEqual(portal.buyer_overview(c, dict(users.get_user(c, other)))["orders"], [])


if __name__ == "__main__":
    unittest.main()
