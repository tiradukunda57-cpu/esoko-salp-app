"""USSD menus (Africa's Talking style: `text` is the full path, e.g. '1*1*5*30000*1').
Returns a string beginning with 'CON ' (continue) or 'END ' (finish)."""
import secrets

from . import catalog, leads, market, permits
from .config import get_settings
from .fees import get_fee
from .i18n import LANGS, t
from .users import ID_RE, RegistrationError, get_user_by_phone, normalize_phone, register_user, resend_registration_payment

CON, END = "CON ", "END "
LANG_CHOICES = {"1": "rw", "2": "en", "3": "fr"}


def _choice(val, n):
    return int(val) if val.isdigit() and 1 <= int(val) <= n else None


def handle(conn, phone, text):
    phone_n = normalize_phone(phone)
    if not phone_n:
        return END + "Invalid phone number"
    parts = [p.strip() for p in text.split("*")] if text else []
    user = get_user_by_phone(conn, phone_n)
    if user is None:
        return _register(conn, phone_n, parts)
    lang = user["language"]
    if user["status"] == "suspended":
        return END + t("suspended", lang, support=get_settings().support_phone)
    if user["status"] == "pending_payment":
        return _pending(conn, user, parts)
    if user["role"] == "buyer":
        return _buyer_menu(conn, user, parts)
    if user["role"] != "farmer":
        return END + t("farmers_only", lang)
    return _menu(conn, user, parts)


def _sectors(conn, where="", args=()):
    rows = conn.execute("SELECT DISTINCT l.district, l.sector FROM locations l " + where + " ORDER BY l.district, l.sector", args).fetchall()
    many = len({r["district"] for r in rows}) > 1
    return [((r["district"], r["sector"]), (r["sector"] + " / " + r["district"]) if many else r["sector"]) for r in rows]


def _pager(items, parts, i, lang, prompt_key):
    """items = [(value, label)]. Eight per screen, 9 = more. -> ('prompt', text) | ('invalid', None) | ('ok', (value, next_i))."""
    page = 0
    while i < len(parts) and parts[i] == "9" and (page + 1) * PAGE < len(items):
        page += 1
        i += 1
    chunk = items[page * PAGE:(page + 1) * PAGE]
    if i >= len(parts):
        lines = [f"{n}. {label}" for n, (_, label) in enumerate(chunk, 1)]
        if (page + 1) * PAGE < len(items):
            lines.append(f"9. {t('more', lang)}")
        return "prompt", t(prompt_key, lang, list="\n".join(lines))
    idx = _choice(parts[i], len(chunk))
    if idx is None:
        return "invalid", None
    return "ok", (chunk[idx - 1][0], i + 1)


def _register(conn, phone, parts):
    if not parts:
        leads.track(conn, phone, "language")
        return CON + t("lang_prompt")
    lang = LANG_CHOICES.get(parts[0])
    if not lang:
        return END + t("invalid", "en")
    if len(parts) == 1:
        leads.track(conn, phone, "role", language=lang)
        return CON + t("ask_role", lang)
    role = {"1": "farmer", "2": "buyer"}.get(parts[1])
    if not role:
        return END + t("invalid", lang)
    parts = [parts[0]] + parts[2:]
    n = len(parts)
    if n == 1:
        leads.track(conn, phone, "id", language=lang, role=role)
        return CON + t("ask_id", lang)
    if not ID_RE.match(parts[1]):
        return END + t("invalid", lang)
    if n == 2:
        leads.track(conn, phone, "name", language=lang, role=role)
        return CON + t("ask_name", lang)
    if not 2 <= len(parts[2]) <= 60:
        return END + t("invalid", lang)
    status, payload = _pager(_sectors(conn), parts, 3, lang, "ask_sector")
    if status == "prompt":
        leads.track(conn, phone, "sector", language=lang, role=role, name=parts[2])
        return CON + payload
    if status == "invalid":
        return END + t("invalid", lang)
    (district, sector), i = payload
    villages = conn.execute("SELECT id, village, cell FROM locations WHERE district=? AND sector=? ORDER BY cell, village",
                            (district, sector)).fetchall()
    status, payload = _pager([(v["id"], v["village"] + " (" + v["cell"] + ")") for v in villages], parts, i, lang, "ask_village")
    if status == "prompt":
        leads.track(conn, phone, "village", language=lang, role=role, name=parts[2])
        return CON + payload
    if status == "invalid":
        return END + t("invalid", lang)
    location_id, i = payload
    fee = get_fee(conn, "registration_fee")
    if n == i:
        leads.track(conn, phone, "confirm", language=lang, role=role, name=parts[2], location_id=location_id)
        return CON + t("confirm_reg", lang, fee=fee)
    if parts[i] != "1":
        return END + t("cancelled", lang)
    try:
        res = register_user(conn, role=role, name=parts[2], phone=phone, national_id=parts[1], location_id=location_id,
                            language=lang, consent=True, password=secrets.token_urlsafe(12) if role == "buyer" else None)
    except RegistrationError as e:
        return END + t("reg_dup" if str(e) == "duplicate" else "invalid", lang)
    leads.complete(conn, phone)
    if res["status"] == "active":
        return END + t("reg_ok", lang, shortcode=get_settings().shortcode)
    return END + t("reg_started", lang, fee=res["fee"])


def _pending(conn, user, parts):
    lang = user["language"]
    fee = get_fee(conn, "registration_fee")
    if not parts:
        return CON + t("pending_menu", lang, fee=fee)
    if parts[0] == "1":
        resend_registration_payment(conn, user)
        return END + t("pending_resent", lang)
    return END + t("bye", lang)


def _menu(conn, user, parts):
    lang, s = user["language"], get_settings()
    if not parts:
        return CON + t("main_menu", lang)
    c = parts[0]
    if c == "1":
        return _list_flow(conn, user, parts)
    if c == "2":
        rows = conn.execute("SELECT code,status FROM products WHERE farmer_id=? ORDER BY id DESC LIMIT 5", (user["id"],)).fetchall()
        if not rows:
            return END + t("no_items", lang)
        return END + t("items_header", lang, list="\n".join(f"{r['code']} {t('status_' + r['status'], lang)}" for r in rows))
    if c == "3":
        rows = conn.execute("SELECT c.name_rw,c.name_en,c.name_fr, CAST(AVG(p.price_per_unit) AS INTEGER) AS avg "
                            "FROM products p JOIN categories c ON c.code=p.category WHERE p.status='Available' "
                            "GROUP BY c.code ORDER BY c.grp, c.sort_order").fetchall()
        if not rows:
            return END + t("no_prices", lang)
        return END + t("prices_header", lang, list="\n".join(f"{catalog.label(r, lang)}: {r['avg']} Frw" for r in rows))
    if c == "4":
        from .util import iso, utcnow
        rows = conn.execute("SELECT p.code, c.code AS cc FROM clearances c JOIN products p ON p.id=c.product_id "
                            "WHERE p.farmer_id=? AND c.used_at IS NULL AND c.valid_until>=? ORDER BY c.id DESC LIMIT 5",
                            (user["id"], iso(utcnow()))).fetchall()
        if not rows:
            return END + t("no_clearance", lang)
        return END + t("clearance_header", lang, list="\n".join(f"{r['code']}:{r['cc']}" for r in rows))
    if c == "5":
        rows = conn.execute("SELECT amount, substr(created_at,1,10) AS d FROM transactions WHERE user_id=? AND type='payout' "
                            "ORDER BY id DESC LIMIT 3", (user["id"],)).fetchall()
        if not rows:
            return END + t("no_payments", lang)
        return END + t("payments_header", lang, list="\n".join(f"{r['d']} {r['amount']} Frw" for r in rows))
    if c == "6":
        return END + t("help", lang, support=s.support_phone)
    return END + t("invalid", lang)


PAGE = 8  # categories per USSD screen; item 9 = "More"


def _category_step(conn, lang, group, parts, i):
    """Walks the category pages. Returns ('prompt', text) | ('invalid', None) | ('ok', (category_row, next_index))."""
    cats = catalog.list_categories(conn, group=group)
    return _pager([(c, catalog.label(c, lang)) for c in cats], parts, i, lang, "ask_category")


def _list_flow(conn, user, parts):
    lang, n = user["language"], len(parts)
    if n == 1:
        return CON + t("ask_group", lang)
    group = {"1": "crop", "2": "livestock"}.get(parts[1])
    if not group:
        return END + t("invalid", lang)
    status, payload = _category_step(conn, lang, group, parts, 2)
    if status == "prompt":
        return CON + payload
    if status == "invalid":
        return END + t("invalid", lang)
    cat, i = payload
    unit = t("unit_" + cat["unit"], lang)
    if n == i:
        return CON + t("ask_qty", lang, unit=unit)
    if not (parts[i].isdigit() and 0 < int(parts[i]) <= 100_000):
        return END + t("invalid", lang)
    qty = parts[i]
    if n == i + 1:
        return CON + t("ask_price", lang)
    if not (parts[i + 1].isdigit() and 0 < int(parts[i + 1]) <= 100_000_000):
        return END + t("invalid", lang)
    price = parts[i + 1]
    if n == i + 2:
        return CON + t("confirm_listing", lang, cat=catalog.label(cat, lang), qty=qty, unit=unit, price=price)
    if parts[i + 2] != "1":
        return END + t("cancelled", lang)
    try:
        p = market.create_product(conn, user["id"], cat["code"], int(qty), int(price))
    except permits.PermitRequired:
        return END + t("listing_blocked", lang)
    except market.MarketError:
        return END + t("invalid", lang)
    return END + t("listing_done", lang, code=p["code"])


# ---------------------------------------------------------------- buyers on a basic phone
def _buyer_menu(conn, user, parts):
    lang, n = user["language"], len(parts)
    if not parts:
        return CON + t("buyer_menu", lang)
    c = parts[0]
    if c == "1":
        return _browse(conn, user, parts)
    if c == "2":
        rows = conn.execute("SELECT p.code, o.status FROM orders o JOIN products p ON p.id=o.product_id "
                            "WHERE o.buyer_id=? ORDER BY o.id DESC LIMIT 5", (user["id"],)).fetchall()
        if not rows:
            return END + t("no_orders", lang)
        return END + t("orders_header", lang, list="\n".join(f"{r['code']} {t('ostat_' + r['status'], lang)}" for r in rows))
    if c == "3":
        return END + t("help", lang, support=get_settings().support_phone)
    return END + t("invalid", lang)


def _browse(conn, user, parts):
    """1 > type > sector > item > (1 = buy). The farmer's phone is shown once an item is chosen."""
    lang = user["language"]
    if len(parts) == 1:
        return CON + t("ask_group", lang)
    group = {"1": "crop", "2": "livestock"}.get(parts[1])
    if not group:
        return END + t("invalid", lang)
    market.release_stale_reservations(conn)
    where = ("JOIN products p ON p.location_id=l.id AND p.status='Available' JOIN categories c ON c.code=p.category "
             "WHERE c.grp=?")
    status, payload = _pager(_sectors(conn, where, (group,)), parts, 2, lang, "ask_sector")
    if status == "prompt":
        return CON + payload
    if status == "invalid":
        return END + t("invalid", lang)
    (district, sector), i = payload
    rows = conn.execute(
        "SELECT p.id, p.code, p.quantity, p.unit, p.price_per_unit, c.name_rw, c.name_en, c.name_fr, l.village, "
        "u.name AS farmer, u.phone FROM products p JOIN categories c ON c.code=p.category "
        "JOIN locations l ON l.id=p.location_id JOIN users u ON u.id=p.farmer_id "
        "WHERE p.status='Available' AND c.grp=? AND l.district=? AND l.sector=? ORDER BY p.id DESC LIMIT 40",
        (group, district, sector)).fetchall()
    if not rows:
        return END + t("no_listings", lang)
    items = [(r, f"{catalog.label(r, lang)} {r['quantity']}{t('unit_' + r['unit'], lang)} {r['price_per_unit']}Frw") for r in rows]
    status, payload = _pager(items, parts, i, lang, "ask_item")
    if status == "prompt":
        return CON + payload
    if status == "invalid":
        return END + t("invalid", lang)
    r, i = payload
    total = int(round(r["quantity"] * r["price_per_unit"]))
    if len(parts) == i:
        return CON + t("item_detail", lang, cat=catalog.label(r, lang), qty=r["quantity"], unit=t("unit_" + r["unit"], lang),
                       price=r["price_per_unit"], total=total, village=r["village"], farmer=r["farmer"], phone=r["phone"])
    if parts[i] != "1":
        return END + t("bye", lang)
    try:
        market.place_order(conn, user["id"], r["id"])
    except permits.PermitRequired:
        return END + t("purchase_blocked", lang, support=get_settings().support_phone)
    except market.MarketError:
        return END + t("not_available", lang)
    return END + t("order_started", lang, total=total)
