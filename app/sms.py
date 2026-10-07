"""SMS outbox. Messages are first stored as 'queued' (safe with DB rollbacks) and then sent by flush_outbox(),
which is called after each request and by the `flush-sms` CLI command (retry up to 5 times)."""
import json
import logging
import urllib.parse
import urllib.request

from .config import get_settings
from .util import iso, utcnow

log = logging.getLogger("esoko.sms")


def send_sms(conn, msisdn, text):
    conn.execute("INSERT INTO notifications(msisdn,text,status,created_at) VALUES(?,?,'queued',?)",
                 (msisdn, text, iso(utcnow())))


def _send_africastalking(s, msisdn, text):
    # NOT yet verified against a live account - test in the Africa's Talking sandbox first.
    base = "https://api.sandbox.africastalking.com" if s.at_sandbox else "https://api.africastalking.com"
    data = {"username": s.at_username, "to": msisdn, "message": text}
    if s.at_sender:
        data["from"] = s.at_sender
    req = urllib.request.Request(
        base + "/version1/messaging", data=urllib.parse.urlencode(data).encode(),
        headers={"apiKey": s.at_api_key, "Accept": "application/json",
                 "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=10) as r:
        body = json.loads(r.read())
    rec = body.get("SMSMessageData", {}).get("Recipients", [])
    if not rec or rec[0].get("statusCode") not in (100, 101, 102):
        raise RuntimeError(f"SMS rejected: {body}")


def flush_outbox(conn, limit=50):
    s = get_settings()
    rows = conn.execute("SELECT * FROM notifications WHERE status IN ('queued','failed') AND attempts<5 "
                        "ORDER BY id LIMIT ?", (limit,)).fetchall()
    sent = 0
    for r in rows:
        try:
            if s.sms_provider == "console":
                log.info("SMS to %s: %s", r["msisdn"], r["text"])
            elif s.sms_provider == "africastalking":
                _send_africastalking(s, r["msisdn"], r["text"])
            else:
                raise RuntimeError("unknown sms provider")
            status = "sent"
            sent += 1
        except Exception:
            log.exception("SMS failed")
            status = "failed"
        conn.execute("UPDATE notifications SET status=?, attempts=attempts+1 WHERE id=?", (status, r["id"]))
    conn.commit()
    return sent
