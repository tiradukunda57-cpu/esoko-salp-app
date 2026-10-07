"""Browser smoke test (Playwright): drives the real pages end to end against a running server.
Usage: python3 tests/ui_smoke.py http://127.0.0.1:8765 [screenshot_dir]"""
import json, re, sys, urllib.request
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
problems = []


def api(path, body=None, token=None, method=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 method=method or ("POST" if body is not None else "GET"),
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
    return json.load(urllib.request.urlopen(req))


def shot(page, name):
    if SHOTS:
        page.screenshot(path=f"{SHOTS}/{name}.png", full_page=True)


def login_pw(page, phone, pw):
    page.goto(BASE + "/")
    page.fill("input[autocomplete=username]", phone)
    page.fill("input[type=password]", pw)
    page.click("button:has-text('Injira'), button:has-text('Sign in')")


def tab(page, text):
    page.click(f".tab:has-text('{text}')")
    page.wait_for_timeout(500)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.on("console", lambda m: problems.append("console " + m.type + ": " + m.text) if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: problems.append("pageerror: " + str(e)))

    # 1 landing
    page.goto(BASE + "/"); page.wait_for_timeout(800); shot(page, "01_landing")
    assert page.locator("h1").inner_text(), "no headline"

    # 2 superadmin signs in -> /admin
    login_pw(page, "0788000001", "ChangeMe-12345"); page.wait_for_url("**/admin"); page.wait_for_timeout(800); shot(page, "02_admin_overview")
    st = {"tok": page.evaluate("localStorage.getItem('esoko_token')")}
    tok = st["tok"]

    # 3 villages via UI
    tab(page, "Imidugudu")
    page.fill("textarea", "Kagugu, Kagugu, Mana, Ngororero\nRuhuha, Ruhuha, Mana, Ngororero")
    page.click("button:has-text('Ongeraho')"); page.wait_for_selector(".okmsg"); shot(page, "03_villages")
    locs = api("/locations", token=tok); assert any(l["village"] == "Kagugu" for l in locs), locs

    # 4 create an agent via UI
    tab(page, "Abantu"); page.click("button:has-text('Ongeraho umukozi')")
    page.select_option(".modal select >> nth=0", "agent")
    inputs = page.locator(".modal input")
    inputs.nth(0).fill("Agent Test"); inputs.nth(1).fill("0788000002"); inputs.nth(2).fill("AgentPass-123")
    kag = [l for l in locs if l["village"] == "Kagugu"][0]
    page.select_option(".modal select >> nth=1", str(kag["id"]))
    page.click(".modal button:has-text('Bika')"); page.wait_for_timeout(800); shot(page, "04_people")

    # 5 fees / catalog / rules / tools / data / audit render without errors
    for label, name in [("Amafaranga", "05_fees"), ("Ibicuruzwa", "06_catalog"), ("Amategeko ya Leta", "07_rules"), ("Ibikoresho", "08_tools"), ("Database", "09_data"), ("Ibyakozwe", "10_audit")]:
        tab(page, label); page.wait_for_timeout(300); shot(page, name)
    tab(page, "Database")
    page.click(".tablist button:has-text('users')"); page.wait_for_selector("table"); shot(page, "09b_data_users")
    assert "password_hash" not in page.locator("th").all_inner_texts(), "password hash column visible"
    with page.expect_download() as dl:
        page.click("button:has-text('CSV')")
    assert dl.value.suggested_filename == "users.csv"

    # 6 agent registers a farmer
    ctx2 = b.new_context(viewport={"width": 390, "height": 800}); a = ctx2.new_page()
    a.on("pageerror", lambda e: problems.append("agent pageerror: " + str(e)))
    a.on("console", lambda m: problems.append("agent console: " + m.text) if m.type == "error" else None)
    login_pw(a, "0788000002", "AgentPass-123"); a.wait_for_url("**/agent"); a.wait_for_timeout(600); shot(a, "11_agent_mobile")
    tab(a, "Abahinzi"); a.click("button:has-text('Andika umuhinzi')")
    ins = a.locator(".modal input")
    ins.nth(0).fill("Mukamana Alice"); ins.nth(1).fill("0788111222"); ins.nth(2).fill("1199080012345678"); a.locator(".modal input[type=checkbox]").check()
    a.click(".modal button:has-text('Bika')"); a.wait_for_selector(".modal .okmsg")
    a.click(".modal button:has-text('wigane')"); a.wait_for_timeout(600)
    a.click(".modal button:has-text('Funga')")
    a.wait_for_timeout(500); shot(a, "12_agent_farmers")

    # 7 farmer signs in with SMS code and lists livestock
    page2 = b.new_context().new_page()
    page2.on("pageerror", lambda e: problems.append("farmer pageerror: " + str(e)))
    page2.goto(BASE + "/"); page2.click(".seg button >> nth=1"); page2.fill("input[autocomplete=username]", "0788111222")
    page2.click("button.btn.block"); page2.wait_for_timeout(800)
    sms = api("/admin/outbox", token=tok); code = re.search(r"\b(\d{6})\b", [m for m in sms if m["msisdn"].endswith("788111222") and re.search(r"\d{6}", m["text"])][0]["text"]).group(1)
    page2.fill("input[autocomplete=one-time-code]", code); page2.click("button.btn.block"); page2.wait_for_url("**/farmer"); page2.wait_for_timeout(600)
    tab(page2, "Gurisha")
    page2.select_option("main select >> nth=0", "goat")
    page2.fill("main input[type=number] >> nth=0", "2"); page2.fill("main input[type=number] >> nth=1", "60000")
    page2.fill("main input[maxlength='30']", "RW-GT-001"); page2.select_option("main select >> nth=1", "female")
    page2.click("button:has-text('Andikisha')"); page2.wait_for_selector(".toast"); shot(page2, "13_farmer_sell")
    tab(page2, "Ibyanjye"); assert "RW-GT-001" not in "" ; shot(page2, "14_farmer_items")

    # 8 buyer registers (UI) -> simulates payment -> signs in -> buys
    page3 = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
    page3.on("pageerror", lambda e: problems.append("buyer pageerror: " + str(e)))
    page3.goto(BASE + "/"); page3.click("button:has-text('Fungura konti')")
    bi = page3.locator(".modal input")
    bi.nth(0).fill("Buyer Test"); bi.nth(1).fill("0788333444"); bi.nth(2).fill("1198080012345678"); bi.nth(3).fill("BuyerPass-123"); page3.locator(".modal input[type=checkbox]").check()
    page3.click(".modal button:has-text('Iyandikishe')"); page3.wait_for_selector(".modal .okmsg"); page3.click(".modal button:has-text('wigane')"); page3.wait_for_timeout(500)
    page3.click(".modal button:has-text('Funga')")
    page3.wait_for_timeout(300); page3.goto(BASE + "/")
    page3.wait_for_selector(".board-row"); shot(page3, "15_landing_prices")
    login_pw(page3, "0788333444", "BuyerPass-123"); page3.wait_for_url("**/buyer"); page3.wait_for_selector("tbody tr"); shot(page3, "16_buyer_market")
    page3.click("tbody .btn:has-text('Gura')"); page3.click(".modal .btn:has-text('Gura')"); page3.wait_for_timeout(800)
    page3.click("button:has-text('wigane')"); page3.wait_for_timeout(800); shot(page3, "17_buyer_orders")

    # 9 agent verifies + hands over
    a.reload(); tab(a, "Bipimwa"); a.wait_for_selector(".qcard"); shot(a, "18_agent_queue")
    a.click(".qcard .btn:has-text('Pima')"); a.wait_for_selector(".modal"); a.click(".modal button:has-text('Bika')"); a.wait_for_timeout(800)
    a.click(".qcard .btn:has-text('Tanga')"); a.click(".modal .btn:has-text('Tanga')"); a.wait_for_timeout(800)
    a.wait_for_timeout(500); shot(a, "19_agent_done")

    # 10 USSD simulator + government dashboard
    u = b.new_context().new_page(); u.on("pageerror", lambda e: problems.append("ussd pageerror: " + str(e)))
    u.goto(BASE + "/ussd-demo"); u.click(".phone .btn"); u.wait_for_timeout(500); assert u.locator(".phone-screen").inner_text().strip(), "empty ussd"; shot(u, "20_ussd")
    api("/admin/users", {"role": "government", "name": "Gov User", "phone": "0788000003", "password": "GovPass-12345"}, token=tok)
    g = b.new_context(viewport={"width": 1280, "height": 900}).new_page(); g.on("pageerror", lambda e: problems.append("gov pageerror: " + str(e)))
    login_pw(g, "0788000003", "GovPass-12345"); g.wait_for_url("**/dashboard"); g.wait_for_timeout(1200); shot(g, "21_gov")
    assert "Wrong" not in g.content()

    # dark mode landing, french
    d = b.new_context(color_scheme="dark", viewport={"width": 390, "height": 800}).new_page(); d.goto(BASE + "/"); d.select_option("header select", "fr"); d.wait_for_timeout(600); shot(d, "22_landing_dark_fr_mobile")
    b.close()

print("PROBLEMS:", *problems, sep="\n  " if problems else " none\n")
