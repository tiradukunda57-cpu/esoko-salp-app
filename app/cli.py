"""Command line: python -m app.cli <command>"""
import argparse
import csv
import getpass
import logging

from . import checkup, market, payments, sms, users
from .config import get_settings
from .db import connect, init_db


def check_db(conn):
    """Exercises schema, inserts and the aggregate queries, then rolls everything back. Safe on a live database."""
    from . import portal, reports
    from .db import dialect, table_names
    print("Database type :", dialect(conn))
    for t in table_names():
        print(f"  {t:<18} rows: {conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
    cur = conn.execute("INSERT INTO locations(village,cell,sector,district) VALUES('__selftest__','c','s','d')")
    print("Insert + new id :", cur.lastrowid)
    ghost = {"id": -1, "role": "farmer", "name": "x", "phone": "x", "language": "rw", "location_id": None}
    reports.summary(conn)
    reports.dashboard(conn)
    reports.dashboard(conn, group="livestock", sector="s", district="d")
    portal.farmer_overview(conn, ghost)
    portal.buyer_overview(conn, {**ghost, "role": "buyer"})
    checkup.run_checkup(conn)
    conn.rollback()
    print("All queries ran. Self-test data was rolled back. OK")


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(prog="esoko")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    sa = sub.add_parser("create-superadmin")
    sa.add_argument("--name", required=True)
    sa.add_argument("--phone", required=True)
    sub.add_parser("seed-locations")
    imp = sub.add_parser("import-locations")
    imp.add_argument("csv_file", help="columns: village,cell,sector,district,lat,lng")
    sub.add_parser("run-checkup")
    sub.add_parser("release-stale")
    sub.add_parser("flush-sms")
    sub.add_parser("check-db", help="connect to the configured database (DATABASE_URL) and run a safe self-test")
    sub.add_parser("show-sms", help="dev: print the last 15 SMS messages (e.g. login codes)")
    sub.add_parser("pending-payments", help="dev: list payments waiting for confirmation")
    cp = sub.add_parser("confirm-payment", help="dev: pretend a customer approved a payment")
    cp.add_argument("provider_ref")
    args = ap.parse_args()

    get_settings().check_production()
    conn = connect()
    init_db(conn)

    if args.cmd == "init-db":
        print("Database ready:", get_settings().db_path)
    elif args.cmd == "create-superadmin":
        pw = getpass.getpass("Password (min 8 chars): ")
        if pw != getpass.getpass("Repeat password: "):
            raise SystemExit("Passwords do not match")
        uid = users.create_superadmin(conn, args.name, args.phone, pw)
        conn.commit()
        print("SuperAdmin created, id =", uid)
    elif args.cmd == "seed-locations":
        conn.execute("INSERT OR IGNORE INTO locations(village,cell,sector,district) VALUES('Mana','Mugano','Ngororero','Ngororero')")
        conn.commit()
        print("Seeded Mana / Mugano / Ngororero / Ngororero. Add the other real villages with import-locations.")
    elif args.cmd == "import-locations":
        n = 0
        with open(args.csv_file, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                conn.execute("INSERT OR IGNORE INTO locations(village,cell,sector,district,lat,lng) VALUES(?,?,?,?,?,?)",
                             (r["village"], r["cell"], r["sector"], r["district"],
                              float(r["lat"]) if r.get("lat") else None, float(r["lng"]) if r.get("lng") else None))
                n += 1
        conn.commit()
        print("Imported rows:", n)
    elif args.cmd == "run-checkup":
        s = checkup.run_checkup(conn)
        conn.commit()
        sms.flush_outbox(conn)
        print("Checkup done:", s["totals"])
    elif args.cmd == "release-stale":
        n = market.release_stale_reservations(conn)
        conn.commit()
        print("Released reservations:", n)
    elif args.cmd == "flush-sms":
        print("SMS sent:", sms.flush_outbox(conn))
    elif args.cmd == "check-db":
        check_db(conn)
    elif args.cmd == "show-sms":
        for r in conn.execute("SELECT created_at,msisdn,status,text FROM notifications ORDER BY id DESC LIMIT 15"):
            print(f"{r['created_at']}  {r['msisdn']}  [{r['status']}]\n    {r['text']}")
    elif args.cmd == "pending-payments":
        for r in conn.execute("SELECT provider_ref,type,amount,msisdn FROM transactions WHERE status='pending'"):
            print(f"{r['provider_ref']}  {r['type']:<17} {r['amount']:>8} Frw  {r['msisdn']}")
    elif args.cmd == "confirm-payment":
        if get_settings().env != "dev":
            raise SystemExit("Only allowed in dev")
        print(payments.on_payment_result(conn, args.provider_ref, True))
        conn.commit()
        sms.flush_outbox(conn)


if __name__ == "__main__":
    main()
