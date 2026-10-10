"""Simulates one full market week in memory, so you can SEE the whole flow:  python -m app.demo"""
import logging

from . import checkup, market, payments, ussd, users
from .db import connect, init_db


def show_sms(conn, title):
    print(f"\n--- SMS sent ({title}) ---")
    for r in conn.execute("SELECT msisdn,text FROM notifications ORDER BY id"):
        print(f"[{r['msisdn']}] {r['text']}")
    conn.execute("DELETE FROM notifications")


def main():
    logging.disable(logging.CRITICAL)
    c = connect(":memory:")
    init_db(c)
    loc = c.execute("INSERT INTO locations(village,cell,sector,district) VALUES('Mana','Mugano','Ngororero','Ngororero')").lastrowid
    sa = users.get_user(c, users.create_superadmin(c, "Owner", "0788000001", "supersecret1"))
    agent = users.get_user(c, users.create_staff(c, sa, role="agent", name="Agent Mana", phone="0788000002",
                                                 password="agentpass1", location_id=loc))
    print("1) Farmer registers on a feature phone (USSD) - registration fee 500 Frw")
    ph = "+250788000003"
    print(ussd.handle(c, ph, "1*1*1199880012345678*Jean Claude*1*1*1"))
    ref = c.execute("SELECT provider_ref FROM transactions WHERE type='registration_fee'").fetchone()[0]
    payments.on_payment_result(c, ref, True)
    farmer = users.get_user_by_phone(c, ph)
    show_sms(c, "registration confirmed")

    print("\n2) Farmer lists 5 sacks of potatoes @ 12,000, 3 sacks of beans @ 1,000 and 1 goat @ 40,000 (USSD)")
    print(ussd.handle(c, ph, "1*1*1*5*12000*1"))
    print(ussd.handle(c, ph, "1*1*2*3*1000*1"))
    print(ussd.handle(c, ph, "1*2*2*1*40000*1"))

    print("\n3) Buyer registers (500 Frw), browses and buys the potatoes (escrow)")
    r = users.register_user(c, role="buyer", name="Kigali Buyer", phone="0788000004",
                            national_id="1198070012345678", password="buyerpass1")
    payments.on_payment_result(c, r["payment_ref"], True)
    potatoes = market.list_available(c, category="potatoes")[0]
    o = market.place_order(c, r["user_id"], potatoes["id"])
    payments.on_payment_result(c, o["payment_ref"], True)
    show_sms(c, "buyer found")

    print("\n4) Tuesday 19:00 automated checkup")
    s = checkup.run_checkup(c)
    print("Report:", s["totals"])
    show_sms(c, "checkup")

    print("\n5) Wednesday morning: agent verifies and hands over, farmer is paid")
    market.agent_verify(c, dict(agent), potatoes["id"], "approve", grade="A")
    print("Money split:", market.confirm_handover(c, dict(agent), o["order_id"]))
    show_sms(c, "payout")

    print("\n6) Dashboard (crops + livestock, aggregated)")
    from . import reports
    d = reports.dashboard(c)
    print("Livestock:", d["totals"]["livestock"])
    print("Crops    :", d["totals"]["crop"])

    print("\n7) Gate officer checks an unsold item's clearance code")
    code = s["unsold"][0]["clearance"]
    print(checkup.verify_clearance(c, code)["status"], "->", checkup.verify_clearance(c, code)["status"])


if __name__ == "__main__":
    main()
