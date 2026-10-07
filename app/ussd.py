"""USSD menus (Africa's Talking style: `text` is the full path, e.g. '1*1*5*30000*1').
Returns a string beginning with 'CON ' (continue) or 'END ' (finish)."""
from . import catalog, market, permits
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
    if user["role"] != "farmer":
        return END + t("farmers_only", lang)
    return _menu(conn, user, parts)


def _register(conn, phone, parts):
    if not parts:
        return CON + t("lang_prompt")
    lang = LANG_CHOICES.get(parts[0])
    if not lang:
        return END + t("invalid", "en")
    n = len(parts)
    if n == 1:
        return CON + t("ask_id", lang)
    if not ID_RE.match(parts[1]):
        return END + t("invalid", lang)
    if n == 2:
        return CON + t("ask_name", lang)
    if not 2 <= len(parts[2]) <= 60:
        return END + t("invalid", lang)
    villages = conn.execute("SELECT id, village FROM locations ORDER BY village LIMIT 9").fetchall()
    if n == 3:
        listing = "\n".join(f"{i}. {v['village']}" for i, v in enumerate(villages, 1))
        return CON + t("ask_village", lang, list=listing)
    idx = _choice(parts[3], len(villages))
    if idx is None:
        return END + t("invalid", lang)
    fee = get_fee(conn, "registration_fee")
    if n == 4:
        return CON + t("confirm_reg", lang, fee=fee)
    if parts[4] != "1":
        return END + t("cancelled", lang)
    try:
        res = register_user(conn, role="farmer", name=parts[2], phone=phone, national_id=parts[1],
                            location_id=villages[idx - 1]["id"], language=lang, consent=True)
    except RegistrationError as e:
        return END + t("reg_dup" if str(e) == "duplicate" else "invalid", lang)
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
    page = 0
    while i < len(parts) and parts[i] == "9" and (page + 1) * PAGE < len(cats):
        page += 1
        i += 1
    chunk = cats[page * PAGE:(page + 1) * PAGE]
    if i >= len(parts):
        lines = [f"{n}. {catalog.label(c, lang)}" for n, c in enumerate(chunk, 1)]
        if (page + 1) * PAGE < len(cats):
            lines.append(f"9. {t('more', lang)}")
        return "prompt", t("ask_category", lang, list="\n".join(lines))
    idx = _choice(parts[i], len(chunk))
    if idx is None:
        return "invalid", None
    return "ok", (chunk[idx - 1], i + 1)


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
