import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv(BASE_DIR / ".env.example")


class Settings:
    # Environment Management: development | test | staging | production
    ENV: str = os.getenv("OPENSEO_ENV", os.getenv("APP_ENV", "development")).lower()

    # Database Configuration (PostgreSQL / SQLite)
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'affiliate.db'}")

    # Cryptographic & Auth Master Secrets
    OPENSEO_ENCRYPTION_KEY: str = os.getenv("OPENSEO_ENCRYPTION_KEY", "")
    OPENSEO_JWT_SECRET: str = os.getenv("OPENSEO_JWT_SECRET", os.getenv("JWT_SECRET_KEY", ""))

    # Publishing Safe Gate
    AUTO_PUBLISH: bool = os.getenv("AUTO_PUBLISH", "false").lower() == "true"

    # Production Integrity & Anti-Hallucination Flags
    FAIL_ON_UNSUPPORTED_CRITICAL_CLAIM: bool = os.getenv("FAIL_ON_UNSUPPORTED_CRITICAL_CLAIM", "true").lower() == "true"
    FAIL_ON_UNRESOLVED_DATA_CONFLICT: bool = os.getenv("FAIL_ON_UNRESOLVED_DATA_CONFLICT", "true").lower() == "true"
    REQUIRE_PRIMARY_EVIDENCE: bool = os.getenv("REQUIRE_PRIMARY_EVIDENCE", "true").lower() == "true"
    ALLOW_FAKE_TESTING_CLAIMS: bool = os.getenv("ALLOW_FAKE_TESTING_CLAIMS", "false").lower() == "true"
    ALLOW_FAKE_FALLBACK_DATA: bool = os.getenv("ALLOW_FAKE_FALLBACK_DATA", "false").lower() == "true"

    # WordPress
    WP_URL: str = os.getenv("WP_URL", "").rstrip("/")
    WP_USERNAME: str = os.getenv("WP_USERNAME", "")
    WP_APP_PASSWORD: str = os.getenv("WP_APP_PASSWORD", "")
    WP_POST_STATUS: str = "draft" if not (os.getenv("AUTO_PUBLISH", "false").lower() == "true") else os.getenv("WP_POST_STATUS", "draft")
    WP_DEFAULT_AUTHOR_ID: int = int(os.getenv("WP_DEFAULT_AUTHOR_ID", "1"))

    # Amazon Affiliate
    AMAZON_TAG: str = os.getenv("AMAZON_TAG", "")
    AMAZON_ACCESS_KEY: str = os.getenv("AMAZON_ACCESS_KEY", "")
    AMAZON_SECRET_KEY: str = os.getenv("AMAZON_SECRET_KEY", "")
    AMAZON_HOST: str = os.getenv("AMAZON_HOST", "webservices.amazon.com")
    AMAZON_REGION: str = os.getenv("AMAZON_REGION", "us-east-1")

    # eBay
    EBAY_CAMPAIGN_ID: str = os.getenv("EBAY_CAMPAIGN_ID", "")
    EBAY_CUSTOM_ID: str = os.getenv("EBAY_CUSTOM_ID", "")

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")

    # DataForSEO / SERP Providers
    DATAFORSEO_LOGIN: str = os.getenv("DATAFORSEO_LOGIN", "")
    DATAFORSEO_PASSWORD: str = os.getenv("DATAFORSEO_PASSWORD", "")
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
    VALUESERP_API_KEY: str = os.getenv("VALUESERP_API_KEY", "")

    # Branding & Legal
    SITE_NAME: str = os.getenv("SITE_NAME", "TopPicks Advisor")
    AFFILIATE_DISCLOSURE: str = os.getenv(
        "AFFILIATE_DISCLOSURE",
        "As an Amazon Associate and affiliate partner, we earn from qualifying purchases at no additional cost to you."
    )

    def validate_production_staging_environment(self):
        """
        Enforces strict environment separation.
        In STAGING or PRODUCTION, startup strictly FAILS if attempting to use SQLite,
        missing encryption master key, or missing JWT secret.
        """
        if self.ENV in ("staging", "production"):
            if self.DATABASE_URL.startswith("sqlite"):
                raise RuntimeError(
                    f"CRITICAL BOOT FAILURE: Environment '{self.ENV}' cannot run on SQLite. "
                    "A real PostgreSQL 16 database connection string is strictly required."
                )
            if not self.OPENSEO_ENCRYPTION_KEY or len(self.OPENSEO_ENCRYPTION_KEY.strip()) < 32:
                raise RuntimeError(
                    f"CRITICAL BOOT FAILURE: Environment '{self.ENV}' requires a secure 256-bit "
                    "OPENSEO_ENCRYPTION_KEY (at least 32 bytes)."
                )
            if not self.OPENSEO_JWT_SECRET or len(self.OPENSEO_JWT_SECRET.strip()) < 32:
                raise RuntimeError(
                    f"CRITICAL BOOT FAILURE: Environment '{self.ENV}' requires a secure "
                    "OPENSEO_JWT_SECRET (at least 32 bytes)."
                )


settings = Settings()
