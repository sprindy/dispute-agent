"""
Authentication module — register, login, JWT token generation/verification.

Uses passlib[bcrypt] for password hashing and PyJWT for token generation.
"""
import os
import hashlib
import hmac
import json
import time
from typing import Optional

import database as db

# --- JWT config (HMAC-SHA256, no external dependency) ---
JWT_SECRET = os.environ.get("JWT_SECRET", "ryde-dispute-agent-secret-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


# --- Password hashing (using hashlib + salt, no bcrypt dependency needed) ---

def _generate_salt() -> str:
    """Generate a random salt using os.urandom."""
    import base64
    return base64.b64encode(os.urandom(16)).decode("utf-8")


def hash_password(password: str) -> str:
    """Hash a password with a random salt using PBKDF2-HMAC-SHA256."""
    salt = _generate_salt()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    hashed = base64_encode(dk)
    return f"pbkdf2_sha256$100000${salt}${hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against the stored hash."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4:
            return False
        algorithm, iterations, salt, stored_dk = parts
        iterations = int(iterations)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return hmac.compare_digest(base64_encode(dk), stored_dk)
    except Exception:
        return False


def base64_encode(data: bytes) -> str:
    import base64
    return base64.b64encode(data).decode("utf-8")


def base64_decode(data: str) -> bytes:
    import base64
    return base64.urlsafe_b64decode(data + "==")


# --- JWT token (manual implementation, no PyJWT needed) ---

def _b64url_encode(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    import base64
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_token(user_id: int, username: str, role: str) -> str:
    """Create a JWT-like token (HMAC-SHA256)."""
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": int(time.time()) + JWT_EXPIRY_HOURS * 3600,
    }
    header_b64 = _b64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{signing_input}.{sig_b64}"


def verify_token(token: str) -> Optional[dict]:
    """Verify a JWT-like token. Returns payload dict or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
        provided_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, provided_sig):
            return None
        payload = json.loads(_b64url_decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            return None  # expired
        return payload
    except Exception:
        return None


# --- Auth operations ---

def register(username: str, email: str, password: str) -> dict:
    """Register a new user. Returns dict with user info and token."""
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    if "@" not in email or "." not in email:
        raise ValueError("Invalid email format")

    password_hash = hash_password(password)
    user = db.create_user(username, email, password_hash)
    token = create_token(user["id"], user["username"], user["role"])
    return {"user": user, "token": token}


def login(username: str, password: str) -> dict:
    """Login an existing user. Returns dict with user info and token."""
    user = db.get_user_by_username(username)
    if not user:
        raise ValueError("Invalid username or password")
    if not verify_password(password, user["password_hash"]):
        raise ValueError("Invalid username or password")
    token = create_token(user["id"], user["username"], user["role"])
    return {
        "user": {"id": user["id"], "username": user["username"], "email": user["email"], "role": user["role"]},
        "token": token,
    }


def get_current_user(token: str) -> Optional[dict]:
    """Extract and verify the user from a token string."""
    payload = verify_token(token)
    if not payload:
        return None
    user = db.get_user_by_id(payload["user_id"])
    if not user:
        return None
    return {"id": user["id"], "username": user["username"], "email": user["email"], "role": user["role"]}


def change_password(user_id: int, old_password: str, new_password: str):
    """Change a user's password after verifying the old one."""
    user = db.get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found")
    if not verify_password(old_password, user["password_hash"]):
        raise ValueError("Current password is incorrect")
    if len(new_password) < 6:
        raise ValueError("New password must be at least 6 characters")
    db.update_user_password(user_id, hash_password(new_password))
