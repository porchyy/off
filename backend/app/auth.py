"""Authentication module: JWT tokens, OAuth verification, and user dependencies."""

from __future__ import annotations

import base64
import json
import time
from typing import Any

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

# Simple HMAC secret for JWT session tokens (or local offline tokens)
SECRET_KEY = "postureai-sso-secret-key-change-in-production"
TOKEN_EXPIRY_SECONDS = 30 * 24 * 3600  # 30 days


def _urlsafe_b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _urlsafe_b64decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(user_id: str) -> str:
    """Generate a lightweight JWT session token for the user."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS
    }
    header_b64 = _urlsafe_b64encode(json.dumps(header).encode('utf-8'))
    payload_b64 = _urlsafe_b64encode(json.dumps(payload).encode('utf-8'))
    signature_input = f"{header_b64}.{payload_b64}"
    
    # Lightweight HMAC-SHA256 signature using Python stdlib
    import hmac
    import hashlib
    sig = hmac.new(SECRET_KEY.encode('utf-8'), signature_input.encode('utf-8'), hashlib.sha256).digest()
    sig_b64 = _urlsafe_b64encode(sig)
    return f"{signature_input}.{sig_b64}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify JWT token."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signature_input = f"{header_b64}.{payload_b64}"

        import hmac
        import hashlib
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), signature_input.encode('utf-8'), hashlib.sha256).digest()
        if _urlsafe_b64encode(expected_sig) != sig_b64:
            return None

        payload = json.loads(_urlsafe_b64decode(payload_b64).decode('utf-8'))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def get_current_user_optional(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
) -> User | None:
    """Extract authenticated user if Authorization header is present."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    return db.get(User, payload["sub"])


def get_current_user(
    user: User | None = Depends(get_current_user_optional)
) -> User:
    """Require authenticated user dependency."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing or invalid",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def verify_oauth_token(provider: str, id_token: str) -> dict[str, str]:
    """
    Parse OAuth ID token payload (or mock parse for offline demo/testing).
    Returns dict: {'email', 'name', 'avatar_url', 'sub'}
    """
    try:
        # JWT format: header.payload.signature
        parts = id_token.split('.')
        if len(parts) >= 2:
            payload_json = _urlsafe_b64decode(parts[1]).decode('utf-8')
            data = json.loads(payload_json)
            email = data.get("email") or data.get("preferred_username") or f"user@{provider}.com"
            name = data.get("name") or email.split('@')[0]
            avatar_url = data.get("picture")
            sub = data.get("sub") or f"{provider}_{email}"
            return {
                "sub": sub,
                "email": email,
                "name": name,
                "avatar_url": avatar_url
            }
    except Exception:
        pass

    # Fallback / Mock Token format
    clean_id = id_token.replace("mock-", "")
    return {
        "sub": f"{provider}_{clean_id}",
        "email": f"{clean_id}@{provider}.com",
        "name": f"{provider.capitalize()} User ({clean_id})",
        "avatar_url": None
    }
