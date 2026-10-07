"""Password hashing, National-ID hashing and signed tokens - standard library only."""
import base64
import hashlib
import hmac
import json
import os
import time

_ITER = 200_000


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, _ITER)
    return f"pbkdf2${_ITER}${salt.hex()}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, it, salt, h = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(it))
        return hmac.compare_digest(dk.hex(), h)
    except Exception:
        return False


def hash_national_id(nid: str, pepper: str) -> str:
    """We never store the full National ID - only a keyed hash (to detect duplicates) and the last 4 digits."""
    return hmac.new(pepper.encode(), nid.encode(), hashlib.sha256).hexdigest()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(sub: int, role: str, secret: str, ttl: int = 8 * 3600, now=None) -> str:
    now = int(now if now is not None else time.time())
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64(json.dumps({"sub": sub, "role": role, "exp": now + ttl}).encode())
    sig = _b64(hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"


def decode_token(token: str, secret: str, now=None):
    try:
        head, body, sig = token.split(".")
        good = _b64(hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            return None
        claims = json.loads(_unb64(body))
        if claims["exp"] < int(now if now is not None else time.time()):
            return None
        return claims
    except Exception:
        return None
