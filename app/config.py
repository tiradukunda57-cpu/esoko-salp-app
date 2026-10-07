"""Settings read from environment variables (see .env.example)."""
import os

_DEFAULT = "change-me-in-production"


def _load_dotenv(path=".env"):
    """Tiny .env reader (no extra dependency). Real environment variables always win."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


_load_dotenv()


class Settings:
    def __init__(self):
        g = os.getenv
        self.env = g("ESOKO_ENV", "dev")                  # dev | prod
        self.db_path = g("ESOKO_DB_PATH", "esoko.db")
        self.database_url = g("DATABASE_URL", "")         # postgres://... (Neon). Empty = use the local SQLite file
        self.job_secret = g("ESOKO_JOB_SECRET", "")       # lets the scheduler call /internal/jobs/*
        self.jwt_secret = g("ESOKO_JWT_SECRET", _DEFAULT)
        self.pepper = g("ESOKO_ID_PEPPER", _DEFAULT)      # used to hash National IDs
        self.webhook_secret = g("ESOKO_WEBHOOK_SECRET", _DEFAULT)
        self.ussd_secret = g("ESOKO_USSD_SECRET", "")     # optional ?key= on the USSD callback URL
        self.shortcode = g("ESOKO_SHORTCODE", "*801#")
        self.support_phone = g("ESOKO_SUPPORT_PHONE", "+2507XXXXXXXX")
        self.settlement_msisdn = g("ESOKO_SETTLEMENT_MSISDN", "+2507XXXXXXXX")
        self.sms_provider = g("ESOKO_SMS_PROVIDER", "console")        # console | africastalking
        self.payment_provider = g("ESOKO_PAYMENT_PROVIDER", "mock")   # mock | (momo - to be implemented)
        # First SuperAdmin, created automatically on start-up when none exists (hosting has no terminal).
        self.bootstrap_name = g("ESOKO_BOOTSTRAP_NAME", "Owner")
        self.bootstrap_phone = g("ESOKO_BOOTSTRAP_PHONE", "")
        self.bootstrap_password = g("ESOKO_BOOTSTRAP_PASSWORD", "")
        self.at_username = g("AT_USERNAME", "sandbox")
        self.at_api_key = g("AT_API_KEY", "")
        self.at_sender = g("AT_SENDER_ID", "")
        self.at_sandbox = g("AT_SANDBOX", "1") == "1"

    @property
    def is_live(self):
        """True for the real system. 'demo' is the hosted TEST system (fake payments, SMS shown inside the site)."""
        return self.env == "prod"

    def check_production(self):
        if self.env not in ("prod", "demo"):
            return
        bad = [n for n, v in (("ESOKO_JWT_SECRET", self.jwt_secret),
                              ("ESOKO_ID_PEPPER", self.pepper),
                              ("ESOKO_WEBHOOK_SECRET", self.webhook_secret)) if v == _DEFAULT]
        if self.env == "prod" and self.payment_provider == "mock":
            bad.append("ESOKO_PAYMENT_PROVIDER (still 'mock')")
        if self.env == "prod" and self.sms_provider == "console":
            bad.append("ESOKO_SMS_PROVIDER (still 'console')")
        if not self.database_url and self.env == "prod":
            bad.append("DATABASE_URL (SQLite is not allowed on the live system)")
        if bad:
            raise RuntimeError("Unsafe production config: " + ", ".join(bad))


def get_settings() -> Settings:
    return Settings()
