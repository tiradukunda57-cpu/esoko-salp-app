"""FastAPI layer (thin): authentication, role checks, HTTP <-> domain functions."""
import csv
import hmac
import io
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import bootstrap, catalog, checkup, fees, geo, leads, market, payments, permits, portal, reports, sms, ussd, users
from .scope import check_area
from .config import get_settings
from .db import audit, connect, dialect, init_db, table_names, _id_tables
from .security import decode_token, make_token, verify_password

STATIC_DIR = Path(__file__).parent / "static"
_live = get_settings().is_live
app = FastAPI(title="E-Soko SALP", version="2.1", docs_url=None if _live else "/docs",
              redoc_url=None, openapi_url=None if _live else "/openapi.json")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

CSP = ("default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data:; script-src 'self'; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path not in ("/docs", "/openapi.json"):  # Swagger loads scripts from a CDN
        resp.headers.setdefault("Content-Security-Policy", CSP)
    if request.url.path.startswith("/static/") or request.url.path.endswith(".html"):
        resp.headers["Cache-Control"] = "no-cache"
    elif request.method == "GET" and not resp.headers.get("Cache-Control"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


_FAILS = {}  # in-memory brute-force guard (one server instance): key -> [timestamps]


def _throttle(key, limit=8, window=600, now=None):
    now = now or time.time()
    hits = [t for t in _FAILS.get(key, []) if now - t < window]
    _FAILS[key] = hits
    if len(hits) >= limit:
        raise HTTPException(429, "too many attempts, try again in a few minutes")


def _fail(key, now=None):
    _FAILS.setdefault(key, []).append(now or time.time())



@app.on_event("startup")
def _startup():
    get_settings().check_production()
    conn = connect()
    init_db(conn)
    bootstrap.run(conn)
    conn.close()
    if get_settings().env in ("demo", "prod") and not get_settings().database_url:
        print("WARNING: no DATABASE_URL - data is stored in a temporary SQLite file and will be LOST on restart.")


def get_conn():
    conn = connect()
    try:
        yield conn
        conn.commit()
        sms.flush_outbox(conn)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.exception_handler(ValueError)
async def _value_error(_, exc):
    return JSONResponse({"error": str(exc)}, status_code=400)


@app.exception_handler(PermissionError)
async def _perm_error(_, exc):
    return JSONResponse({"error": str(exc) or "forbidden"}, status_code=403)


_ALLOWED_WHILE_TEMP_PASSWORD = ("/auth/me", "/auth/change-password", "/config/public")


def current_user(request: Request, authorization: Optional[str] = Header(None), conn=Depends(get_conn)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing token")
    claims = decode_token(authorization[7:], get_settings().jwt_secret)
    if not claims:
        raise HTTPException(401, "invalid or expired token")
    row = users.get_user(conn, claims["sub"])
    if not row or row["status"] != "active":
        raise HTTPException(401, "account not active")
    d = dict(row)
    if d.get("must_change_password") and request.url.path not in _ALLOWED_WHILE_TEMP_PASSWORD:
        raise HTTPException(403, "password_change_required")
    return d


def require(*roles):
    def dep(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "forbidden")
        return user
    return dep


def public_user(u):
    u = dict(u)
    return {"id": u["id"], "role": u["role"], "name": u["name"], "phone": u["phone"], "status": u["status"],
            "language": u["language"], "location_id": u["location_id"],
            "national_id_last4": u.get("national_id_last4"), "created_at": u.get("created_at"),
            "must_change_password": bool(u.get("must_change_password"))}


# ------------------------------------------------------------------ models
class LoginIn(BaseModel):
    phone: str
    password: str


class BuyerRegisterIn(BaseModel):
    name: str
    phone: str
    national_id: str
    password: str
    language: str = "en"
    location_id: Optional[int] = None
    consent: bool


class FarmerRegisterIn(BaseModel):
    name: str
    phone: str
    national_id: str
    language: str = "rw"
    location_id: Optional[int] = None
    consent: bool


class StaffIn(BaseModel):
    role: str
    name: str
    phone: str
    password: str
    location_id: Optional[int] = None


class StatusIn(BaseModel):
    status: str


class OrderIn(BaseModel):
    product_id: int


class RevisionIn(BaseModel):
    accept: bool


class VerifyIn(BaseModel):
    product_id: int
    result: str  # approve | downgrade | reject
    grade: Optional[str] = None
    weight: Optional[float] = None
    note: Optional[str] = None
    new_price: Optional[int] = None
    tag_number: Optional[str] = None  # livestock ear-tag / identifier


class HandoverIn(BaseModel):
    order_id: int


class FeeIn(BaseModel):
    key: str
    value: int


class WebhookIn(BaseModel):
    provider_ref: str
    status: str  # succeeded | failed


class DevConfirmIn(BaseModel):
    provider_ref: str
    success: bool = True


# ------------------------------------------------------------------ public
@app.get("/health")
def health():
    return {"ok": True}


@app.get("/locations")
def locations(conn=Depends(get_conn)):
    return [dict(r) for r in conn.execute("SELECT * FROM locations ORDER BY district,sector,cell,village")]


@app.post("/auth/login")
def login(body: LoginIn, conn=Depends(get_conn)):
    phone = users.normalize_phone(body.phone)
    key = "pw:" + (phone or body.phone[:20])
    _throttle(key)
    u = users.get_user_by_phone(conn, phone) if phone else None
    if not u or not u["password_hash"] or not verify_password(body.password, u["password_hash"]):
        _fail(key)
        conn.commit()
        raise HTTPException(401, "wrong phone or password")
    if u["status"] != "active":
        raise HTTPException(403, "account " + u["status"])
    return {"token": make_token(u["id"], u["role"], get_settings().jwt_secret), "user": public_user(u)}


@app.post("/auth/register-buyer")
def register_buyer(body: BuyerRegisterIn, conn=Depends(get_conn)):
    r = users.register_user(conn, role="buyer", name=body.name, phone=body.phone, national_id=body.national_id,
                            location_id=body.location_id, language=body.language, password=body.password,
                            consent=body.consent)
    return {"user_id": r["user_id"], "status": r["status"], "registration_fee": r["fee"],
            "message": "Approve the mobile-money payment prompt on your phone, then log in."}


# ------------------------------------------------------------------ USSD + payment callbacks
@app.post("/ussd", response_class=PlainTextResponse)
async def ussd_callback(request: Request, conn=Depends(get_conn)):
    s = get_settings()
    if s.ussd_secret and request.query_params.get("key") != s.ussd_secret:
        raise HTTPException(403, "forbidden")
    form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
    return ussd.handle(conn, form.get("phoneNumber", ""), form.get("text", ""))


@app.post("/webhooks/payment")
def payment_webhook(body: WebhookIn, x_webhook_secret: Optional[str] = Header(None), conn=Depends(get_conn)):
    # Adapt this to the real provider's signature scheme when you integrate it.
    if not x_webhook_secret or not hmac.compare_digest(x_webhook_secret, get_settings().webhook_secret):
        raise HTTPException(403, "bad secret")
    return {"result": payments.on_payment_result(conn, body.provider_ref, body.status == "succeeded")}


@app.post("/dev/confirm-payment")
def dev_confirm(body: DevConfirmIn, conn=Depends(get_conn)):
    """Development only: pretend the customer approved/declined the mobile-money prompt."""
    if get_settings().env != "dev":
        raise HTTPException(404, "not found")
    return {"result": payments.on_payment_result(conn, body.provider_ref, body.success)}


# ------------------------------------------------------------------ buyers
@app.get("/products")
def products(category: Optional[str] = None, location_id: Optional[int] = None,
             user=Depends(require("buyer", "agent", "admin", "superadmin")), conn=Depends(get_conn)):
    market.release_stale_reservations(conn)  # unpaid reservations older than 30 minutes go back on sale
    return market.list_available(conn, category, location_id)


@app.post("/orders")
def create_order(body: OrderIn, user=Depends(require("buyer")), conn=Depends(get_conn)):
    return market.place_order(conn, user["id"], body.product_id)


@app.post("/orders/{order_id}/revision")
def revision(order_id: int, body: RevisionIn, user=Depends(require("buyer")), conn=Depends(get_conn)):
    market.respond_to_revision(conn, user["id"], order_id, body.accept)
    return {"ok": True}


# ------------------------------------------------------------------ agents
@app.get("/agent/queue")
def agent_queue(user=Depends(require("agent", "admin", "superadmin")), conn=Depends(get_conn)):
    return market.agent_queue(conn, user)


@app.post("/agent/verify")
def agent_verify(body: VerifyIn, user=Depends(require("agent", "admin", "superadmin")), conn=Depends(get_conn)):
    market.agent_verify(conn, user, body.product_id, body.result, body.grade, body.weight, body.note, body.new_price,
                        tag_number=body.tag_number)
    return {"ok": True}


@app.post("/agent/handover")
def agent_handover(body: HandoverIn, user=Depends(require("agent", "admin", "superadmin")), conn=Depends(get_conn)):
    return market.confirm_handover(conn, user, body.order_id)


@app.post("/agent/register-farmer")
def agent_register_farmer(body: FarmerRegisterIn, user=Depends(require("agent", "admin", "superadmin")),
                          conn=Depends(get_conn)):
    r = users.register_user(conn, role="farmer", name=body.name, phone=body.phone, national_id=body.national_id,
                            location_id=body.location_id or user["location_id"], language=body.language,
                            consent=body.consent, registered_by=user["id"])
    return {"user_id": r["user_id"], "status": r["status"], "registration_fee": r["fee"]}


@app.get("/gate/verify/{code}")
def gate_verify(code: str, user=Depends(require("gate", "agent", "admin", "superadmin")), conn=Depends(get_conn)):
    return checkup.verify_clearance(conn, code, gate_user_id=user["id"])


# ------------------------------------------------------------------ admin
@app.post("/admin/users")
def admin_create_user(body: StaffIn, user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    uid = users.create_staff(conn, user, role=body.role, name=body.name, phone=body.phone,
                             password=body.password, location_id=body.location_id)
    return {"user_id": uid}


@app.get("/admin/users")
def admin_list_users(role: Optional[str] = None, q: Optional[str] = None,
                     user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    sql, args = "SELECT * FROM users WHERE 1=1", []
    if role:
        sql += " AND role=?"
        args.append(role)
    if q:
        sql += " AND (name LIKE ? OR phone LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    return [public_user(r) for r in conn.execute(sql + " ORDER BY id DESC LIMIT 200", args)]


@app.get("/admin/leads")
def admin_leads(user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    """People who started to register but did not finish, or did not pay the registration fee yet: Admin can phone and help."""
    return leads.list_open(conn)


@app.post("/admin/users/{user_id}/status")
def admin_user_status(user_id: int, body: StatusIn, user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    users.set_user_status(conn, user, user_id, body.status)
    return {"ok": True}


@app.post("/admin/users/{user_id}/reset-password")
def admin_reset_password(user_id: int, user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    try:
        temp = users.reset_password(conn, user, user_id)
    except ValueError:
        raise HTTPException(404, "not found")
    except PermissionError:
        raise HTTPException(403, "forbidden")
    return {"password": temp}


@app.get("/admin/fees")
def get_fees(user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    return fees.all_fees(conn)


@app.put("/admin/fees")
def put_fee(body: FeeIn, user=Depends(require("superadmin")), conn=Depends(get_conn)):
    fees.set_fee(conn, user, body.key, body.value)
    return fees.all_fees(conn)


@app.get("/admin/summary")
def admin_summary(user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    return reports.summary(conn)


@app.post("/admin/checkup")
def admin_checkup(user=Depends(require("superadmin")), conn=Depends(get_conn)):
    return checkup.run_checkup(conn)


@app.get("/admin/audit")
def admin_audit(limit: int = 100, user=Depends(require("superadmin")), conn=Depends(get_conn)):
    return [dict(r) for r in conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (min(limit, 500),))]


# ------------------------------------------------------------------ categories (all crops + all livestock)
class CategoryIn(BaseModel):
    code: str
    grp: str            # crop | livestock
    prefix: str         # 3 capital letters, used in product IDs
    unit: str           # sack | bunch | kg | head
    name_rw: str
    name_en: str
    name_fr: str


class ActiveIn(BaseModel):
    active: bool


@app.get("/categories")
def list_categories(group: Optional[str] = None, conn=Depends(get_conn)):
    return [dict(r) for r in catalog.list_categories(conn, group=group)]


@app.post("/admin/categories")
def add_category(body: CategoryIn, user=Depends(require("superadmin")), conn=Depends(get_conn)):
    catalog.add_category(conn, user, **body.dict())
    return {"ok": True}


@app.post("/admin/categories/{code}/active")
def category_active(code: str, body: ActiveIn, user=Depends(require("superadmin")), conn=Depends(get_conn)):
    catalog.set_category_active(conn, user, code, body.active)
    return {"ok": True}


# ------------------------------------------------------------------ government requirements (permits) - data, not code
class PermitTypeIn(BaseModel):
    code: str
    name_rw: str
    name_en: str
    name_fr: str
    subject: str                      # user | product
    required_at: str                  # listing | purchase (user)  /  handover | market_entry (product)
    applies_to: str = "all"           # all | crop | livestock | <category code>
    issuer: Optional[str] = None
    role_scope: Optional[str] = None  # farmer | buyer (for user permits)
    mandatory: bool = False           # True = blocks the step when missing
    active: bool = False              # False = rule not in force yet
    validity_days: Optional[int] = None


class GrantIn(BaseModel):
    type_code: str
    user_id: Optional[int] = None
    product_id: Optional[int] = None
    reference: Optional[str] = None
    valid_until: Optional[str] = None  # YYYY-MM-DD
    note: Optional[str] = None


class AgentListIn(BaseModel):
    farmer_id: int
    category: str
    quantity: float
    price_per_unit: int
    tag_number: Optional[str] = None
    sex: Optional[str] = None
    age_months: Optional[int] = None
    notes: Optional[str] = None


@app.get("/admin/permit-types")
def get_permit_types(user=Depends(require("admin", "superadmin", "government")), conn=Depends(get_conn)):
    return permits.list_types(conn)


@app.post("/admin/permit-types")
def create_permit_type(body: PermitTypeIn, user=Depends(require("superadmin")), conn=Depends(get_conn)):
    permits.create_type(conn, user, **body.dict())
    return {"ok": True}


@app.patch("/admin/permit-types/{code}")
def patch_permit_type(code: str, changes: Dict[str, Any], user=Depends(require("superadmin")), conn=Depends(get_conn)):
    """Switch a rule on/off or make it mandatory: {"active": true, "mandatory": true}"""
    permits.update_type(conn, user, code, **changes)
    return {"ok": True}


@app.post("/agent/permits")
def grant_permit(body: GrantIn, user=Depends(require("agent", "admin", "superadmin")), conn=Depends(get_conn)):
    pid = permits.grant_permit(conn, user, body.type_code, user_id=body.user_id, product_id=body.product_id,
                               reference=body.reference, valid_until=body.valid_until, note=body.note)
    return {"permit_id": pid}


@app.post("/admin/permits/{permit_id}/revoke")
def revoke_permit(permit_id: int, user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    permits.revoke_permit(conn, user, permit_id)
    return {"ok": True}


@app.get("/permits")
def get_permits(user_id: Optional[int] = None, product_id: Optional[int] = None,
                user=Depends(require("agent", "admin", "superadmin", "government")), conn=Depends(get_conn)):
    return permits.list_permits(conn, user_id=user_id, product_id=product_id)


@app.post("/agent/list-product")
def agent_list_product(body: AgentListIn, user=Depends(require("agent", "admin", "superadmin")), conn=Depends(get_conn)):
    """Agent lists on behalf of a farmer (adds livestock details such as ear-tag number, sex, age)."""
    farmer = users.get_user(conn, body.farmer_id)
    if not farmer or farmer["role"] != "farmer":
        raise ValueError("farmer_not_found")
    check_area(conn, user, farmer["location_id"])
    return market.create_product(conn, farmer["id"], body.category, body.quantity, body.price_per_unit,
                                 tag_number=body.tag_number, sex=body.sex, age_months=body.age_months,
                                 notes=body.notes, listed_by=user["id"])


# ------------------------------------------------------------------ password, villages, public prices
class PasswordIn(BaseModel):
    current: str
    new: str


class LocationsIn(BaseModel):
    text: str


@app.post("/auth/change-password")
def change_password(body: PasswordIn, user=Depends(current_user), conn=Depends(get_conn)):
    key = "chg:" + str(user["id"])
    _throttle(key, limit=6)
    try:
        users.change_password(conn, user, body.current, body.new)
    except ValueError:
        _fail(key)
        conn.commit()
        raise
    return {"ok": True}


@app.post("/admin/locations")
def admin_add_locations(body: LocationsIn, user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    return geo.add_locations(conn, user, body.text)


@app.get("/public/prices")
def public_prices(conn=Depends(get_conn)):
    """Anonymous price board for the landing page: only averages per product, no names or phone numbers."""
    return [dict(r) for r in conn.execute(
        "SELECT c.code,c.grp,c.unit,c.name_rw,c.name_en,c.name_fr,COUNT(p.id) AS listings,"
        " CAST(AVG(p.price_per_unit) AS INTEGER) AS avg_price, MIN(p.price_per_unit) AS min_price, MAX(p.price_per_unit) AS max_price "
        "FROM products p JOIN categories c ON c.code=p.category WHERE p.status='Available' "
        "GROUP BY c.code,c.grp,c.unit,c.name_rw,c.name_en,c.name_fr,c.sort_order ORDER BY c.grp, c.sort_order LIMIT 12")]


# ------------------------------------------------------------------ dashboard: livestock + crops
@app.get("/dashboard/overview")
def dashboard_overview(group: Optional[str] = None, days: int = 30, sector: Optional[str] = None,
                       district: Optional[str] = None,
                       user=Depends(require("admin", "superadmin", "government")), conn=Depends(get_conn)):
    return reports.dashboard(conn, group=group, days=days, sector=sector, district=district)


def _page(name):
    return FileResponse(STATIC_DIR / name, media_type="text/html; charset=utf-8")


@app.get("/", include_in_schema=False)
def home_page():
    return _page("index.html")


@app.get("/farmer", include_in_schema=False)
def farmer_page():
    return _page("farmer.html")


@app.get("/buyer", include_in_schema=False)
def buyer_page():
    return _page("buyer.html")


@app.get("/agent", include_in_schema=False)
def agent_page():
    return _page("agent.html")


@app.get("/admin", include_in_schema=False)
def admin_page():
    return _page("admin.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard_page():
    """Public shell only - the numbers come from the API after login."""
    return _page("dashboard.html")


@app.get("/ussd-demo", include_in_schema=False)
def ussd_demo_page():
    if get_settings().is_live:
        raise HTTPException(404, "not found")
    return _page("ussd.html")


# ------------------------------------------------------------------ SMS-code login + farmer / buyer portal
class OtpRequestIn(BaseModel):
    phone: str


class OtpVerifyIn(BaseModel):
    phone: str
    code: str


class MyListingIn(BaseModel):
    category: str
    quantity: float
    price_per_unit: int
    tag_number: Optional[str] = None
    sex: Optional[str] = None
    age_months: Optional[int] = None
    notes: Optional[str] = None


@app.post("/auth/request-otp")
def request_otp(body: OtpRequestIn, conn=Depends(get_conn)):
    sent = portal.request_otp(conn, body.phone)  # same answer whether or not the number exists
    out = {"message": "If this number is registered, a code was sent by SMS."}
    if not sent and not get_settings().is_live:
        out["test_hint"] = portal.explain_refusal(conn, body.phone)  # the live system never says why
    return out


@app.post("/auth/verify-otp")
def verify_otp(body: OtpVerifyIn, conn=Depends(get_conn)):
    key = "otp:" + body.phone[:20]
    _throttle(key, limit=10)
    u = portal.verify_otp(conn, body.phone, body.code)
    if not u:  # return (not raise) so the failed-attempt counter is committed
        _fail(key)
        return JSONResponse({"error": "invalid or expired code"}, status_code=401)
    return {"token": make_token(u["id"], u["role"], get_settings().jwt_secret, ttl=4 * 3600), "user": public_user(u)}


@app.get("/portal/farmer")
def portal_farmer(user=Depends(require("farmer")), conn=Depends(get_conn)):
    return portal.farmer_overview(conn, user)


@app.post("/portal/farmer/listings")
def portal_farmer_list(body: MyListingIn, user=Depends(require("farmer")), conn=Depends(get_conn)):
    return market.create_product(conn, user["id"], body.category, body.quantity, body.price_per_unit,
                                 tag_number=body.tag_number, sex=body.sex, age_months=body.age_months, notes=body.notes)


@app.get("/portal/buyer")
def portal_buyer(user=Depends(require("buyer")), conn=Depends(get_conn)):
    return portal.buyer_overview(conn, user)


# ------------------------------------------------------------------ who am I / public settings
@app.get("/auth/me")
def auth_me(user=Depends(current_user)):
    return {"user": public_user(user)}


@app.get("/config/public")
def public_config(conn=Depends(get_conn)):
    s = get_settings()
    return {"mode": "live" if s.is_live else "test", "env": s.env, "shortcode": s.shortcode, "support_phone": s.support_phone,
            "registration_fee": fees.get_fee(conn, "registration_fee"),
            "test_payments": s.payment_provider == "mock" and not s.is_live,
            "test_sms": s.sms_provider == "console" and not s.is_live,
            "ussd_simulator": not s.is_live, "database": dialect(conn)}


# ------------------------------------------------------------------ agents: farmers in my area
@app.get("/agent/farmers")
def agent_farmers(q: Optional[str] = None, user=Depends(require("agent", "admin", "superadmin")), conn=Depends(get_conn)):
    sql = ("SELECT u.id,u.name,u.phone,u.status,u.national_id_last4,COALESCE(l.village,'-') AS village,l.sector,l.district "
           "FROM users u LEFT JOIN locations l ON l.id=u.location_id WHERE u.role='farmer'")
    args = []
    if user["role"] == "agent":
        if user["location_id"] is None:
            return []
        a = conn.execute("SELECT sector,district FROM locations WHERE id=?", (user["location_id"],)).fetchone()
        sql += " AND l.sector=? AND l.district=?"
        args += [a["sector"], a["district"]]
    if q:
        sql += " AND (u.name LIKE ? OR u.phone LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    return [dict(r) for r in conn.execute(sql + " ORDER BY u.id DESC LIMIT 100", args)]


# ------------------------------------------------------------------ test-mode helpers (never available on the live system)
def _test_mode_only():
    s = get_settings()
    if s.is_live:
        raise HTTPException(404, "not found")
    return s


@app.get("/admin/payments/pending")
def pending_payments(user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    s = _test_mode_only()
    if s.payment_provider != "mock":
        raise HTTPException(404, "not found")
    return [dict(r) for r in conn.execute(
        "SELECT t.provider_ref,t.type,t.amount,t.msisdn,t.created_at,u.name FROM transactions t "
        "LEFT JOIN users u ON u.id=t.user_id WHERE t.status='pending' ORDER BY t.id DESC LIMIT 100")]


@app.post("/admin/payments/confirm")
def confirm_payment(body: DevConfirmIn, user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    s = _test_mode_only()
    if s.payment_provider != "mock":
        raise HTTPException(404, "not found")
    audit(conn, user["id"], "test_payment.confirm" if body.success else "test_payment.fail", "transaction", body.provider_ref)
    return {"result": payments.on_payment_result(conn, body.provider_ref, body.success)}


@app.get("/admin/outbox")
def sms_outbox(user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    """Test mode: SMS are not sent to real phones, so the messages are shown here (login codes included)."""
    s = _test_mode_only()
    if s.sms_provider != "console":
        raise HTTPException(404, "not found")
    return [dict(r) for r in conn.execute("SELECT id,msisdn,text,status,created_at FROM notifications ORDER BY id DESC LIMIT 60")]


@app.get("/admin/categories")
def admin_categories(user=Depends(require("admin", "superadmin")), conn=Depends(get_conn)):
    return [dict(r) for r in catalog.list_categories(conn, include_inactive=True)]


@app.get("/agent/permit-types")
def agent_permit_types(user=Depends(require("agent", "admin", "superadmin")), conn=Depends(get_conn)):
    """Rules currently in force, so an Agent knows which documents to ask for."""
    return [t for t in permits.list_types(conn) if t["active"]]


class PhoneIn(BaseModel):
    phone: str


@app.post("/test/approve-registration")
def test_approve_registration(body: PhoneIn, conn=Depends(get_conn)):
    """TEST SYSTEM ONLY: pretends the person approved the registration payment on their phone."""
    s = _test_mode_only()
    if s.payment_provider != "mock":
        raise HTTPException(404, "not found")
    phone = users.normalize_phone(body.phone)
    refs = [r["provider_ref"] for r in conn.execute(
        "SELECT t.provider_ref FROM transactions t JOIN users u ON u.id=t.user_id "
        "WHERE u.phone=? AND t.type='registration_fee' AND t.status='pending'", (phone or "",))]
    for ref in refs:
        payments.on_payment_result(conn, ref, True)
    return {"approved": len(refs)}


@app.post("/test/approve-mine")
def test_approve_mine(user=Depends(current_user), conn=Depends(get_conn)):
    """TEST SYSTEM ONLY: pretends the signed-in buyer approved their pending payments."""
    s = _test_mode_only()
    if s.payment_provider != "mock":
        raise HTTPException(404, "not found")
    refs = [r["provider_ref"] for r in conn.execute(
        "SELECT provider_ref FROM transactions WHERE user_id=? AND status='pending' AND type='escrow_in'", (user["id"],))]
    for ref in refs:
        payments.on_payment_result(conn, ref, True)
    return {"approved": len(refs)}


# ------------------------------------------------------------------ SuperAdmin: read-only database explorer
HIDDEN_COLUMNS = {"password_hash", "national_id_hash", "code_hash"}


def _csv_cell(v):
    v = "" if v is None else str(v)
    return "'" + v if v[:1] in ("=", "+", "-", "@") else v  # stops spreadsheet formula injection


@app.get("/admin/db/tables")
def db_tables(user=Depends(require("superadmin")), conn=Depends(get_conn)):
    audit(conn, user["id"], "db.tables")
    return {"database": dialect(conn),
            "tables": [{"name": t, "rows": conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]} for t in table_names()]}


@app.get("/admin/db/tables/{name}")
def db_rows(name: str, limit: int = 50, offset: int = 0, q: Optional[str] = None, format: str = "json",
            user=Depends(require("superadmin")), conn=Depends(get_conn)):
    if name not in table_names():  # only names from our own schema ever reach the SQL text
        raise HTTPException(404, "unknown table")
    csv_out = format == "csv"
    limit = max(1, min(limit, 50000 if csv_out else 200))
    offset = max(0, offset)
    cols = [d[0] for d in conn.execute(f"SELECT * FROM {name} LIMIT 1").description]
    shown = [c for c in cols if c not in HIDDEN_COLUMNS]
    where, args = "", []
    if q:
        where = " WHERE " + " OR ".join(f"CAST({c} AS TEXT) LIKE ?" for c in shown)
        args = [f"%{q}%"] * len(shown)
    total = conn.execute(f"SELECT COUNT(*) FROM {name}{where}", args).fetchone()[0]
    order = "ORDER BY 1 DESC" if name in _id_tables() else "ORDER BY 1"
    rows = conn.execute(f"SELECT {', '.join(shown)} FROM {name}{where} {order} LIMIT ? OFFSET ?", [*args, limit, offset]).fetchall()
    audit(conn, user["id"], "db.export" if csv_out else "db.view", "table", name, {"q": q, "offset": offset})
    if csv_out:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(shown)
        for r in rows:
            w.writerow([_csv_cell(r[c]) for c in shown])
        return Response(buf.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{name}.csv"'})
    return {"table": name, "columns": shown, "hidden": sorted(set(cols) & HIDDEN_COLUMNS), "total": total,
            "limit": limit, "offset": offset, "rows": [[r[c] for c in shown] for r in rows]}


# ------------------------------------------------------------------ scheduled jobs (called by GitHub Actions / a cron service)
@app.post("/internal/jobs/{name}")
def run_job(name: str, x_job_secret: Optional[str] = Header(None), conn=Depends(get_conn)):
    secret = get_settings().job_secret
    if not secret or not x_job_secret or not hmac.compare_digest(x_job_secret, secret):
        raise HTTPException(403, "forbidden")
    if name == "checkup":  # Tuesday and Friday 19:00 CAT - safe to call twice (it is idempotent)
        out = checkup.run_checkup(conn)["totals"]
    elif name == "housekeeping":
        out = {"released_reservations": market.release_stale_reservations(conn)}
    else:
        raise HTTPException(404, "unknown job")
    audit(conn, None, "job." + name, "system", None, out)
    return {"job": name, "result": out}
