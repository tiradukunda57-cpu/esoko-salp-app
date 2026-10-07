"""Payment layer. Business logic never talks to a mobile-money API directly - only through a provider.

MockProvider      : for development/tests. Payments stay 'pending' until you confirm them
                    (POST /dev/confirm-payment or payments.on_payment_result).
A real provider   : to be implemented once you have a contract with a licensed payment partner
                    (MTN MoMo / Airtel Money / aggregator). It must implement the two methods below.
IMPORTANT: buyer money (escrow) must be held by the licensed partner, NOT in a personal wallet."""
import uuid

from . import sms
from .config import get_settings
from .i18n import t
from .util import iso, utcnow


class MockProvider:
    name = "mock"

    def request_collection(self, msisdn, amount, reference):
        return f"MOCKIN-{reference}"

    def send_money(self, msisdn, amount, reference):
        return f"MOCKOUT-{reference}", "succeeded"


def get_provider():
    name = get_settings().payment_provider
    if name == "mock":
        return MockProvider()
    raise NotImplementedError(
        "Implement a real provider class (request_collection / send_money) and return it here.")


def _ref():
    return uuid.uuid4().hex[:12]


def add_tx(conn, *, type, amount, status, user_id=None, order_id=None, product_id=None, msisdn=None, provider_ref=None):
    conn.execute(
        "INSERT INTO transactions(user_id,order_id,product_id,type,amount,msisdn,provider_ref,status,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (user_id, order_id, product_id, type, amount, msisdn, provider_ref, status, iso(utcnow())))


def request_registration_payment(conn, user_id, msisdn, amount):
    ref = get_provider().request_collection(msisdn, amount, _ref())
    add_tx(conn, type="registration_fee", amount=amount, status="pending", user_id=user_id,
           msisdn=msisdn, provider_ref=ref)
    return ref


def request_escrow(conn, *, order_id, buyer_id, product_id, msisdn, amount):
    ref = get_provider().request_collection(msisdn, amount, _ref())
    add_tx(conn, type="escrow_in", amount=amount, status="pending", user_id=buyer_id, order_id=order_id,
           product_id=product_id, msisdn=msisdn, provider_ref=ref)
    return ref


def send_money(conn, *, type, user_id, msisdn, amount, order_id=None, product_id=None):
    ref, status = get_provider().send_money(msisdn, amount, _ref())
    add_tx(conn, type=type, amount=amount, status=status, user_id=user_id, order_id=order_id,
           product_id=product_id, msisdn=msisdn, provider_ref=ref)
    return ref


def activate_user(conn, user_id):
    conn.execute("UPDATE users SET status='active' WHERE id=? AND status='pending_payment'", (user_id,))
    u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    sms.send_sms(conn, u["phone"], t("sms_welcome", u["language"], name=u["name"].split()[0],
                                     shortcode=get_settings().shortcode))


def on_payment_result(conn, provider_ref, success):
    """Called by the provider webhook. Idempotent: a repeated callback does nothing."""
    from . import market  # local import to avoid a cycle
    tx = conn.execute("SELECT * FROM transactions WHERE provider_ref=?", (provider_ref,)).fetchone()
    if tx is None:
        return "unknown"
    if tx["status"] != "pending":
        return "ignored"
    conn.execute("UPDATE transactions SET status=? WHERE id=?", ("succeeded" if success else "failed", tx["id"]))
    if tx["type"] == "registration_fee" and success:
        activate_user(conn, tx["user_id"])
    elif tx["type"] == "escrow_in":
        (market.on_escrow_funded if success else market.on_escrow_failed)(conn, tx["order_id"])
    return "ok"
