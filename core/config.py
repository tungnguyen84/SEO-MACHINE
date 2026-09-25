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
    # Database Configuration (PostgreSQL / SQLite)
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'affiliate.db'}")

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

    # DataForSEO
    DATAFORSEO_LOGIN: str = os.getenv("DATAFORSEO_LOGIN", "")
    DATAFORSEO_PASSWORD: str = os.getenv("DATAFORSEO_PASSWORD", "")

    # Branding & Legal
    SITE_NAME: str = os.getenv("SITE_NAME", "TopPicks Advisor")
    AFFILIATE_DISCLOSURE: str = os.getenv(
        "AFFILIATE_DISCLOSURE",
        "As an Amazon Associate and affiliate partner, we earn from qualifying purchases at no additional cost to you."
    )

settings = Settings()
