"""
Production Authentication & Token Management Subsystem
Provides cryptographically signed JWT authentication, timing-safe validation,
token revocation checks, and strict credential boundary enforcement.
Zero dev-backdoor bypasses permitted.
"""

import os
import time
import json
import base64
import hmac
import hashlib
import uuid
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends
from core.niche_builder.schema import PermissionRole


class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Invalid authentication credentials"):
        super().__init__(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


class TokenManager:
    """
    Manages production JWT tokens with HMAC-SHA256 signatures.
    Includes tenant_id, role, unique jti, and expiration.
    """

    _REVOKED_TOKENS = set()  # set of revoked jti tokens

    @classmethod
    def get_secret(cls) -> str:
        key = os.getenv("OPENSEO_JWT_SECRET") or os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
        env = os.getenv("APP_ENV") or os.getenv("ENV") or "development"
        if env.lower() == "production":
            if not key or key == "openseo-dev-key-change-in-prod" or len(key) < 32:
                raise RuntimeError("Production security error: Strong OPENSEO_JWT_SECRET required in production.")
        return key or "openseo-production-grade-jwt-secret-key-32bytes-min"

    @classmethod
    def create_access_token(
        cls,
        user_id: Any,
        email: str,
        tenant_id: str = "tenant_default",
        role: str = "ADMIN",
        plan_tier: str = "agency",
        expires_in_seconds: int = 86400  # 24 hours
    ) -> str:
        """Creates a signed JWT with user identity, tenant isolation scope, and role."""
        now = int(time.time())
        token_id = str(uuid.uuid4())
        payload = {
            "sub": str(user_id),
            "email": email,
            "tenant_id": str(tenant_id),
            "role": str(role).upper(),
            "plan": plan_tier,
            "iat": now,
            "exp": now + expires_in_seconds,
            "jti": token_id
        }

        header = {"alg": "HS256", "typ": "JWT"}
        b64_header = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("ascii").rstrip("=")
        b64_payload = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
        signing_input = f"{b64_header}.{b64_payload}"

        secret = cls.get_secret().encode("utf-8")
        signature = hmac.new(secret, signing_input.encode("utf-8"), hashlib.sha256).digest()
        b64_sig = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")

        return f"{signing_input}.{b64_sig}"

    @classmethod
    def verify_token(cls, token: str) -> Dict[str, Any]:
        """
        Cryptographically validates token signature, expiration, and revocation status.
        Raises AuthenticationError on any tampering or expiration.
        """
        if not token or not isinstance(token, str):
            raise AuthenticationError("Missing token")

        parts = token.strip().split(".")
        if len(parts) != 3:
            raise AuthenticationError("Invalid token format")

        b64_header, b64_payload, b64_sig = parts
        signing_input = f"{b64_header}.{b64_payload}"
        secret = cls.get_secret().encode("utf-8")
        expected_sig = hmac.new(secret, signing_input.encode("utf-8"), hashlib.sha256).digest()
        expected_b64_sig = base64.urlsafe_b64encode(expected_sig).decode("ascii").rstrip("=")

        if not hmac.compare_digest(b64_sig, expected_b64_sig):
            raise AuthenticationError("Invalid token signature")

        try:
            padded_payload = b64_payload + "=" * (-len(b64_payload) % 4)
            payload_json = base64.urlsafe_b64decode(padded_payload.encode("ascii")).decode("utf-8")
            payload = json.loads(payload_json)
        except Exception:
            raise AuthenticationError("Malformed token payload")

        # Expiration check
        exp = payload.get("exp", 0)
        if time.time() > exp:
            raise AuthenticationError("Token has expired")

        # Revocation check
        jti = payload.get("jti")
        if jti and jti in cls._REVOKED_TOKENS:
            raise AuthenticationError("Token has been revoked")

        return payload

    @classmethod
    def revoke_token(cls, token: str):
        """Adds token jti to revoked set."""
        try:
            payload = cls.verify_token(token)
            jti = payload.get("jti")
            if jti:
                cls._REVOKED_TOKENS.add(jti)
        except Exception:
            pass


class AuthenticatedUser:
    """Strongly typed authenticated identity for request context."""
    def __init__(self, user_id: str, email: str, tenant_id: str, role: str, plan_tier: str = "agency"):
        self.user_id = str(user_id)
        self.email = email
        self.tenant_id = str(tenant_id)
        self.role = str(role).upper()
        self.plan_tier = plan_tier

    def has_role(self, required_role: PermissionRole) -> bool:
        hierarchy = {
            PermissionRole.VIEWER.value: 1,
            PermissionRole.EDITOR.value: 2,
            PermissionRole.ADMIN.value: 3,
            PermissionRole.OWNER.value: 4,
        }
        user_level = hierarchy.get(self.role, 0)
        req_level = hierarchy.get(required_role.value, 99)
        return user_level >= req_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.user_id,
            "user_id": self.user_id,
            "email": self.email,
            "tenant_id": self.tenant_id,
            "role": self.role,
            "plan_tier": self.plan_tier
        }


def get_authenticated_user(authorization: Optional[str] = Header(None)) -> AuthenticatedUser:
    """
    FastAPI Dependency: Strictly enforces Bearer authentication on protected SaaS endpoints.
    Rejects requests without valid token (No dev backdoors).
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is required (Bearer token)",
            headers={"WWW-Authenticate": "Bearer"}
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authorization header must follow 'Bearer <token>' format",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = parts[1].strip()
    payload = TokenManager.verify_token(token)

    return AuthenticatedUser(
        user_id=payload.get("sub", ""),
        email=payload.get("email", ""),
        tenant_id=payload.get("tenant_id", "tenant_default"),
        role=payload.get("role", "VIEWER"),
        plan_tier=payload.get("plan", "starter")
    )
