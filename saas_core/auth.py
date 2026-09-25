import time
import json
import base64
import hmac
import hashlib
from typing import Optional, Dict, Any
from core.database import get_user_by_email, get_user_by_id, verify_password, create_user

SECRET_KEY = "openseo-commercial-saas-super-secret-key-2026"

class SaaSAuthManager:
    """
    Module quản lý xác thực tài khoản & JWT Token bảo mật.
    """
    @staticmethod
    def create_token(user_id: int, email: str, plan_tier: str) -> str:
        payload = {
            "sub": user_id,
            "email": email,
            "plan": plan_tier,
            "exp": int(time.time()) + 86400 * 30 # 30 ngày
        }
        raw_payload = json.dumps(payload).encode("utf-8")
        b64_payload = base64.urlsafe_b64encode(raw_payload).decode("utf-8").rstrip("=")
        
        signature = hmac.new(SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{b64_payload}.{signature}"

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return None
            b64_payload, signature = parts
            expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected_sig):
                return None
            
            # Giải mã payload
            padded = b64_payload + "=" * (-len(b64_payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
            if data.get("exp", 0) < time.time():
                return None # Hết hạn
            return data
        except Exception:
            return None

    @classmethod
    def authenticate_user(cls, email: str, password: str) -> Optional[Dict[str, Any]]:
        user = get_user_by_email(email)
        if not user:
            return None
        if verify_password(password, user["password_hash"], user["salt"]):
            token = cls.create_token(user["id"], user["email"], user["plan_tier"])
            return {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "plan_tier": user["plan_tier"],
                "credits_remaining": user["credits_remaining"],
                "token": token
            }
        return None
