import unittest

from app import catalog, checkup, market, payments, permits, reports, ussd, users
from tests.test_core import activate, add_location, new_db, world


def sold_order(c, buyer, product_id):
    o = market.place_order(c, buyer, product_id)
    payments.on_payment_result(c, o["payment_ref"], True)
    return o


class CatalogTests(unittest.TestCase):
    def test_all_common_livestock_and_crops_exist(self):
        c = new_db()
        live = {r["code"]: r for r in catalog.list_categories(c, group="livestock")}
        for sp in ("cattle", "goat", "sheep", "pig", "chicken", "rabbit", "duck", "other_livestock"):
            self.assertIn(sp, live)
            self.assertEqual(live[sp]["unit"], "head")
        crops = {r["code"] for r in catalog.list_categories(c, group="crop")}
        for cp in ("potatoes", "beans", "maize", "banana", "peas", "cassava", "tomato"):
            self.assertIn(cp, crops)

    def test_superadmin_can_add_species_without_code_change(self):
        c, loc, sa, agent, farmer, buyer = world()
        with self.assertRaises(PermissionError):
            catalog.add_category(c, dict(agent), code="bees", grp="livestock", prefix="BEE", unit="head",
                                 name_rw="Inzuki", name_en="Bees", name_fr="Abeilles")
        catalog.add_category(c, dict(sa), code="bees", grp="livestock", prefix="BEE", unit="head",
                             name_rw="Inzuki", name_en="Bees", name_fr="Abeilles")
        p = market.create_product(c, farmer, "bees", 2, 50000)
        self.assertTrue(p["code"].startswith("BEE-"))


class LivestockTests(unittest.TestCase):
    def test_tag_number_rules(self):
        c, loc, sa, agent, farmer, buyer = world()
        a = market.create_product(c, farmer, "cattle", 1, 300000, tag_number="rw-123", sex="female", age_months=30)
        self.assertEqual(c.execute("SELECT tag_number FROM products WHERE id=?", (a["id"],)).fetchone()[0], "RW-123")
        with self.assertRaises(market.MarketError):  # same animal cannot be listed twice
            market.create_product(c, farmer, "cattle", 1, 300000, tag_number="RW-123")
        with self.assertRaises(market.MarketError):  # tags make no sense for crops
            market.create_product(c, farmer, "potatoes", 1, 1000, tag_number="X1")
        with self.assertRaises(market.MarketError):
            market.create_product(c, farmer, "goat", 1, 1000, sex="unknown")


class PermitTests(unittest.TestCase):
    def test_placeholder_rules_are_off_by_default(self):
        c, loc, sa, agent, farmer, buyer = world()
        self.assertTrue(all(t["active"] == 0 for t in permits.list_types(c)))
        market.create_product(c, farmer, "goat", 1, 40000)  # nothing blocks while rules are off

    def test_listing_permit_for_livestock_keepers(self):
        c, loc, sa, agent, farmer, buyer = world()
        permits.update_type(c, dict(sa), "livestock_keeper_registration", active=True, mandatory=True)
        with self.assertRaises(permits.PermitRequired):
            market.create_product(c, farmer, "goat", 1, 40000)
        market.create_product(c, farmer, "potatoes", 1, 1000)  # crops are not affected
        permits.grant_permit(c, dict(agent), "livestock_keeper_registration", user_id=farmer, reference="LK-001")
        market.create_product(c, farmer, "goat", 1, 40000)

    def test_handover_blocked_until_movement_permit(self):
        c, loc, sa, agent, farmer, buyer = world()
        permits.update_type(c, dict(sa), "livestock_movement_permit", active=True, mandatory=True)
        p = market.create_product(c, farmer, "goat", 2, 40000)
        o = sold_order(c, buyer, p["id"])
        market.agent_verify(c, dict(agent), p["id"], "approve", grade="A")
        self.assertEqual(market.agent_queue(c, dict(agent))[0]["permits_missing"][0]["code"], "livestock_movement_permit")
        with self.assertRaises(permits.PermitRequired):
            market.confirm_handover(c, dict(agent), o["order_id"])
        permits.grant_permit(c, dict(agent), "livestock_movement_permit", product_id=p["id"], reference="MOV-77")
        self.assertEqual(market.confirm_handover(c, dict(agent), o["order_id"])["total"], 80000)

    def test_new_government_rule_added_as_data_only(self):
        c, loc, sa, agent, farmer, buyer = world()
        permits.create_type(c, dict(sa), code="potato_quality_cert", name_rw="Icyemezo cy'ubwiza", name_en="Quality certificate",
                            name_fr="Certificat de qualite", subject="product", required_at="handover",
                            applies_to="potatoes", issuer="RAB", mandatory=True, active=True, validity_days=30)
        p = market.create_product(c, farmer, "potatoes", 5, 12000)
        o = sold_order(c, buyer, p["id"])
        market.agent_verify(c, dict(agent), p["id"], "approve")
        with self.assertRaises(permits.PermitRequired):
            market.confirm_handover(c, dict(agent), o["order_id"])
        permits.grant_permit(c, dict(agent), "potato_quality_cert", product_id=p["id"], reference="RAB-9")
        market.confirm_handover(c, dict(agent), o["order_id"])
        with self.assertRaises(PermissionError):  # only the SuperAdmin defines rules
            permits.create_type(c, dict(agent), code="x_rule", name_rw="a", name_en="a", name_fr="a",
                                subject="user", required_at="purchase")

    def test_market_entry_checked_at_the_gate(self):
        c, loc, sa, agent, farmer, buyer = world()
        permits.update_type(c, dict(sa), "livestock_market_entry", active=True, mandatory=True)
        p = market.create_product(c, farmer, "cattle", 1, 300000)
        s = checkup.run_checkup(c)
        code = s["unsold"][0]["clearance"]
        self.assertEqual(checkup.verify_clearance(c, code, consume=False)["status"], "permit_missing")
        permits.grant_permit(c, dict(agent), "livestock_market_entry", product_id=p["id"], reference="ME-5")
        self.assertEqual(checkup.verify_clearance(c, code)["status"], "valid")

    def test_agent_cannot_grant_outside_own_sector(self):
        c, loc, sa, agent, farmer, buyer = world()
        permits.update_type(c, dict(sa), "livestock_keeper_registration", active=True, mandatory=True)
        other = add_location(c, "Kabaya", "Kabaya", "Kabaya", "Ngororero")
        far = activate(c, "farmer", "Far Farmer", "0788000009", "1199880099999991", other)
        with self.assertRaises(PermissionError):
            permits.grant_permit(c, dict(agent), "livestock_keeper_registration", user_id=far, reference="X")


class UssdExtendedTests(unittest.TestCase):
    def setUp(self):
        self.c, self.loc, self.sa, self.agent, self.farmer, self.buyer = world()
        self.ph = "+250788000003"

    def test_group_menu_and_livestock_listing(self):
        self.assertIn("Amatungo", ussd.handle(self.c, self.ph, "1"))
        self.assertIn("Ihene", ussd.handle(self.c, self.ph, "1*2"))
        done = ussd.handle(self.c, self.ph, "1*2*2*1*40000*1")  # livestock > goat > 1 head > 40000
        self.assertIn("GOA-", done)
        row = self.c.execute("SELECT quantity,unit FROM products WHERE code LIKE ?", ("GOA-%",)).fetchone()
        self.assertEqual((row["quantity"], row["unit"]), (1, "head"))

    def test_more_crops_on_page_two(self):
        first = ussd.handle(self.c, self.ph, "1*1")
        self.assertIn("9.", first)  # "More" is offered because there are more than 8 crops
        self.assertIn("Inyanya", ussd.handle(self.c, self.ph, "1*1*9"))
        self.assertIn("TOM-", ussd.handle(self.c, self.ph, "1*1*9*1*20*500*1"))

    def test_listing_blocked_message(self):
        permits.update_type(self.c, dict(self.sa), "livestock_keeper_registration", active=True, mandatory=True)
        out = ussd.handle(self.c, self.ph, "1*2*2*1*40000*1")
        self.assertTrue(out.startswith("END "))
        self.assertNotIn("GOA-", out)
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM products").fetchone()[0], 0)


class DashboardTests(unittest.TestCase):
    def test_numbers_and_filters(self):
        c, loc, sa, agent, farmer, buyer = world()
        pot = market.create_product(c, farmer, "potatoes", 5, 12000)
        market.create_product(c, farmer, "cattle", 2, 300000, sex="male")
        goat = market.create_product(c, farmer, "goat", 3, 40000, sex="female")
        sold_order(c, buyer, pot["id"])
        sold_order(c, buyer, goat["id"])
        other = add_location(c, "Kabaya", "Kabaya", "Kabaya", "Ngororero")
        far = activate(c, "farmer", "Far Farmer", "0788000009", "1199880099999991", other)
        market.create_product(c, far, "sheep", 4, 30000)

        d = reports.dashboard(c)
        live, crop = d["totals"]["livestock"], d["totals"]["crop"]
        self.assertEqual(live["heads_listed"], 9)        # 2 cattle + 3 goats + 4 sheep
        self.assertEqual(live["heads_available"], 6)     # cattle 2 + sheep 4
        self.assertEqual(live["heads_sold"], 3)
        self.assertEqual(live["sold_value"], 120000)
        self.assertEqual(live["active_farmers"], 2)
        self.assertEqual(crop["listed_items"], 1)
        self.assertEqual(crop["sold_value"], 60000)
        self.assertEqual(d["livestock_by_sex"], {"male": 2, "female": 3})

        only_mana = reports.dashboard(c, sector="Ngororero", district="Ngororero")["totals"]["livestock"]
        self.assertEqual(only_mana["heads_listed"], 5)
        only_kabaya = reports.dashboard(c, group="livestock", sector="Kabaya")
        self.assertEqual(only_kabaya["totals"]["livestock"]["heads_listed"], 4)
        self.assertNotIn("crop", only_kabaya["totals"])
        self.assertNotIn("Far Farmer", str(d))            # aggregated only: no personal data
        names = {x["code"] for x in d["categories"]}
        self.assertTrue({"cattle", "goat", "sheep", "pig", "chicken", "rabbit"} <= names)


class AgentSaleSmsTests(unittest.TestCase):
    def test_agent_of_the_area_is_told_when_a_product_is_bought(self):
        c, loc, sa, agent, farmer, buyer = world()
        p = market.create_product(c, farmer, "potatoes", 3, 500)
        c.execute("DELETE FROM notifications")
        sold_order(c, buyer, p["id"])
        rows = c.execute("SELECT msisdn,text FROM notifications").fetchall()
        to_agent = [r["text"] for r in rows if r["msisdn"] == agent["phone"]]
        to_farmer = [r["text"] for r in rows if r["msisdn"] != agent["phone"]]
        self.assertEqual(len(to_agent), 1)
        self.assertIn(p["code"], to_agent[0])
        self.assertIn("Jean", to_agent[0])
        self.assertTrue(any(p["code"] in x for x in to_farmer))


class BuyerUssdTests(unittest.TestCase):
    def test_buyer_browses_by_sector_sees_farmer_phone_and_buys(self):
        c, loc, sa, agent, farmer, buyer = world()
        p = market.create_product(c, farmer, "potatoes", 3, 500)
        ph, farmer_phone = users.get_user(c, buyer)["phone"], users.get_user(c, farmer)["phone"]
        self.assertIn("Reba", ussd.handle(c, ph, ""))
        self.assertIn("Ibihingwa", ussd.handle(c, ph, "1"))
        sectors = ussd.handle(c, ph, "1*1")
        self.assertIn("Ngororero", sectors)
        items = ussd.handle(c, ph, "1*1*1")
        self.assertIn("Ibirayi", items)
        detail = ussd.handle(c, ph, "1*1*1*1")
        self.assertIn(farmer_phone, detail)
        self.assertIn("1500", detail)
        done = ussd.handle(c, ph, "1*1*1*1*1")
        self.assertTrue(done.startswith("END "))
        self.assertEqual(c.execute("SELECT status FROM products WHERE id=?", (p["id"],)).fetchone()[0], "Reserved")
        self.assertIn(p["code"], ussd.handle(c, ph, "2"))
        again = ussd.handle(c, ph, "1*1*1")
        self.assertTrue(again.startswith("END "))

    def test_buyer_can_register_on_ussd(self):
        c, loc, sa, agent, farmer, buyer = world()
        ph = "+250788555111"
        out = ussd.handle(c, ph, "1*2*1199880099999999*Nice Buyer*1*1*1")
        self.assertTrue(out.startswith("END "))
        u = users.get_user_by_phone(c, ph)
        self.assertEqual(u["role"], "buyer")
        self.assertTrue(u["password_hash"])


class RoleTests(unittest.TestCase):
    def test_government_user_creation(self):
        c, loc, sa, agent, farmer, buyer = world()
        uid = users.create_staff(c, dict(sa), role="government", name="District Vet", phone="0788000050", password="govpass123")
        self.assertEqual(users.get_user(c, uid)["role"], "government")
        admin = users.get_user(c, users.create_staff(c, dict(sa), role="admin", name="Admin Two", phone="0788000051", password="adminpass1"))
        with self.assertRaises(PermissionError):
            users.create_staff(c, dict(admin), role="government", name="X Y", phone="0788000052", password="govpass123")

    def test_password_reset_only_superadmin_and_hash_stays_hashed(self):
        from app.security import verify_password
        c, loc, sa, agent, farmer, buyer = world()
        temp = users.reset_password(c, dict(sa), agent["id"])
        row = users.get_user(c, agent["id"])
        self.assertGreaterEqual(len(temp), 10)
        self.assertNotEqual(row["password_hash"], temp)
        self.assertTrue(verify_password(temp, row["password_hash"]))
        with self.assertRaises(PermissionError):
            users.reset_password(c, dict(agent), buyer)
        with self.assertRaises(PermissionError):
            users.reset_password(c, dict(sa), sa["id"])
        admin = users.get_user(c, users.create_staff(c, dict(sa), role="admin", name="Admin Two", phone="0788000061", password="adminpass1"))
        users.reset_password(c, dict(admin), buyer)
        with self.assertRaises(PermissionError):
            users.reset_password(c, dict(admin), admin["id"])
        with self.assertRaises(PermissionError):
            users.reset_password(c, dict(admin), sa["id"])

    def test_temp_password_must_be_changed_and_old_db_is_migrated(self):
        import sqlite3
        from app import db
        c, loc, sa, agent, farmer, buyer = world()
        self.assertFalse(users.get_user(c, agent["id"])["must_change_password"])
        temp = users.reset_password(c, dict(sa), agent["id"])
        self.assertTrue(users.get_user(c, agent["id"])["must_change_password"])
        users.change_password(c, dict(users.get_user(c, agent["id"])), temp, "brand-new-pass1")
        self.assertFalse(users.get_user(c, agent["id"])["must_change_password"])
        old = sqlite3.connect(":memory:")
        old.row_factory = sqlite3.Row
        old.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, role TEXT, name TEXT, phone TEXT)")
        self.assertFalse(db._has_column(old, "users", "must_change_password"))
        db.migrate(old)
        self.assertTrue(db._has_column(old, "users", "must_change_password"))
        db.migrate(old)


if __name__ == "__main__":
    unittest.main()


class SignupLeadTests(unittest.TestCase):
    def test_half_finished_ussd_signup_is_visible_to_admin(self):
        from app import leads
        c = new_db()
        add_location(c, "Mana")
        ph = "+250788555111"
        ussd.handle(c, ph, "")
        ussd.handle(c, ph, "1*1")
        ussd.handle(c, ph, "1*1*1199880012345678*Marie Claire")
        open_ = leads.list_open(c)["unfinished"]
        self.assertEqual([r["phone"] for r in open_], [ph])
        self.assertEqual(open_[0]["step"], "sector")
        self.assertEqual(open_[0]["name"], "Marie Claire")
        self.assertEqual(open_[0]["role"], "farmer")
        self.assertNotIn("1199880012345678", str(open_))   # the National ID is never kept
        ussd.handle(c, ph, "1*1*1199880012345678*Marie Claire*1*1*1")
        both = leads.list_open(c)
        self.assertEqual(both["unfinished"], [])
        self.assertEqual([r["phone"] for r in both["unpaid"]], [ph])   # registered but fee not paid

    def test_buyer_on_basic_phone_sees_sellers_phone(self):
        c, loc, sa, agent, farmer, buyer = world()
        market.create_product(c, farmer, "potatoes", 10, 500)
        b = c.execute("SELECT phone FROM users WHERE id=?", (buyer,)).fetchone()[0]
        f = c.execute("SELECT phone FROM users WHERE id=?", (farmer,)).fetchone()[0]
        self.assertTrue(ussd.handle(c, b, "").startswith("CON "))
        self.assertTrue(ussd.handle(c, b, "1").startswith("CON "))
        self.assertTrue(ussd.handle(c, b, "1*1").startswith("CON "))
        sector = ussd.handle(c, b, "1*1")
        self.assertIn("1.", sector)
        items = ussd.handle(c, b, "1*1*1")
        self.assertTrue(items.startswith("CON "))
        detail = ussd.handle(c, b, "1*1*1*1")
        self.assertIn(f.lstrip("+"), detail.replace("+", ""))
