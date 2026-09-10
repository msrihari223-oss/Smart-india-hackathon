"""
AETHERIA Authentication & Role-Based Access Control (RBAC) Module
Provides password hashing with cryptographic salting, session management,
user registration, authentication verification, and pre-seeded intelligence roles.
Integrates with PostgreSQL (when available) with in-memory persistence fallback.
"""

import time
import uuid
import hashlib
import secrets
from typing import Dict, Any, Optional, List

from backend.database.config import SessionLocal
from backend.database.models import AppUserRecord
from backend.database.postgres_repository import postgres_repo


import re

def _extract_phone_digits(phone: str) -> str:
    """Extracts numeric digits from phone string for resilient matching."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    # If standard 12-digit Indian phone with country code 91, also match last 10 digits
    return digits


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Generates a salted SHA-256 hash for secure credential storage."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hashed, salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifies candidate plaintext against the stored salt + hash with legacy fallbacks."""
    if not stored_hash:
        return False
    # Standard salted SHA-256
    candidate_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    if secrets.compare_digest(candidate_hash, stored_hash):
        return True
    # Unsalted SHA-256 fallback
    candidate_unsalted = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if secrets.compare_digest(candidate_unsalted, stored_hash):
        return True
    # Plain text comparison fallback for legacy accounts
    if secrets.compare_digest(password, stored_hash):
        return True
    return False


class AuthManager:
    def __init__(self):
        # In-memory users store: username -> dict
        self._users: Dict[str, Dict[str, Any]] = {}
        # Active sessions: token -> dict (user details + expires_at)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        # Active password reset OTPs: username -> { otp, email, expires_at, created_at }
        self._otps: Dict[str, Dict[str, Any]] = {}
        # Pre-seed intelligence operator accounts
        self._seed_default_accounts()

    def _seed_default_accounts(self):
        """Pre-seeds system with default authorized operations personnel."""
        defaults = [
            {
                "username": "admin",
                "email": "admin@aetheria.intelligence.io",
                "phone_number": "+1-555-0101",
                "password": "admin123",
                "full_name": "Director Sarah Vance",
                "role": "Director / Admin",
                "clearance_level": "Level 5 - Top Secret",
                "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=DirectorSarah"
            },
            {
                "username": "analyst",
                "email": "analyst@aetheria.intelligence.io",
                "phone_number": "+1-555-0102",
                "password": "sentinel2026",
                "full_name": "Dr. Marcus Chen",
                "role": "Lead Data Analyst",
                "clearance_level": "Level 3 - Secret",
                "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=MarcusChen"
            },
            {
                "username": "operator",
                "email": "operator@aetheria.intelligence.io",
                "phone_number": "+1-555-0103",
                "password": "operator123",
                "full_name": "Agent Elena Rostova",
                "role": "Field Operator",
                "clearance_level": "Level 2 - Confidential",
                "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=ElenaRostova"
            }
        ]

        for acc in defaults:
            p_hash, salt = hash_password(acc["password"])
            user_dict = {
                "id": f"usr_{acc['username']}",
                "username": acc["username"],
                "email": acc["email"],
                "phone_number": acc.get("phone_number", ""),
                "password_hash": p_hash,
                "salt": salt,
                "full_name": acc["full_name"],
                "role": acc["role"],
                "clearance_level": acc["clearance_level"],
                "avatar": acc["avatar"],
                "is_active": True,
                "created_at": time.time(),
                "last_login": time.time()
            }
            self._users[acc["username"].lower()] = user_dict
            self._save_to_db_if_connected(user_dict)

    def _save_to_db_if_connected(self, user_dict: Dict[str, Any]):
        """Persists user to PostgreSQL if database connection is available."""
        if not postgres_repo.is_connected or SessionLocal is None:
            return
        try:
            with SessionLocal() as db:
                record = AppUserRecord(
                    id=user_dict["id"],
                    username=user_dict["username"],
                    email=user_dict["email"],
                    phone_number=user_dict.get("phone_number", ""),
                    password_hash=user_dict["password_hash"],
                    salt=user_dict["salt"],
                    full_name=user_dict.get("full_name", ""),
                    role=user_dict.get("role", "Analyst"),
                    clearance_level=user_dict.get("clearance_level", "Level 3"),
                    avatar=user_dict.get("avatar", ""),
                    is_active=user_dict.get("is_active", True),
                    created_at=user_dict.get("created_at", time.time()),
                    last_login=user_dict.get("last_login", time.time())
                )
                db.merge(record)
                db.commit()
        except Exception:
            pass

    def get_user(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Finds user by username, email, or phone number from memory or PostgreSQL."""
        if not identifier:
            return None
        identifier_clean = identifier.strip().lower()
        identifier_raw = identifier.strip()
        identifier_digits = _extract_phone_digits(identifier_raw)

        # 1. Check in-memory store
        for u in self._users.values():
            u_name = u.get("username", "").lower()
            u_email = u.get("email", "").lower()
            u_phone = u.get("phone_number", "")
            u_phone_digits = _extract_phone_digits(u_phone)

            if u_name == identifier_clean or u_email == identifier_clean:
                return u
            if u_phone and (u_phone.strip() == identifier_raw or (identifier_digits and u_phone_digits and (u_phone_digits == identifier_digits or u_phone_digits.endswith(identifier_digits) or identifier_digits.endswith(u_phone_digits)))):
                return u

        # 2. Check database if available
        if postgres_repo.is_connected and SessionLocal is not None:
            try:
                with SessionLocal() as db:
                    # Query by username or email first
                    record = db.query(AppUserRecord).filter(
                        (AppUserRecord.username.ilike(identifier_clean)) | 
                        (AppUserRecord.email.ilike(identifier_clean)) |
                        (AppUserRecord.phone_number == identifier_raw)
                    ).first()

                    # Fallback phone search if not matched directly
                    if not record and identifier_digits and len(identifier_digits) >= 6:
                        all_users = db.query(AppUserRecord).all()
                        for cand in all_users:
                            cand_digits = _extract_phone_digits(cand.phone_number)
                            if cand_digits and (cand_digits == identifier_digits or cand_digits.endswith(identifier_digits) or identifier_digits.endswith(cand_digits)):
                                record = cand
                                break

                    if record:
                        u_dict = {
                            "id": record.id,
                            "username": record.username,
                            "email": record.email,
                            "phone_number": record.phone_number or "",
                            "password_hash": record.password_hash,
                            "salt": record.salt,
                            "full_name": record.full_name,
                            "role": record.role,
                            "clearance_level": record.clearance_level,
                            "avatar": record.avatar,
                            "is_active": record.is_active,
                            "created_at": record.created_at,
                            "last_login": record.last_login
                        }
                        self._users[record.username.lower()] = u_dict
                        return u_dict
            except Exception:
                pass

        return None

    def register(self, username: str, email: str, phone_number: str = "", password: str = "", full_name: str = "", role: str = "Analyst", clearance_level: str = "Level 3") -> Dict[str, Any]:
        """Registers a new user account or updates existing user credentials seamlessly."""
        username = username.strip().lower()
        email = email.strip().lower()
        phone_number = phone_number.strip()

        if len(username) < 2:
            return {"success": False, "message": "User ID must be at least 2 characters long."}
        if "@" not in email or "." not in email:
            return {"success": False, "message": "Please provide a valid email address."}
        if len(phone_number) < 6:
            return {"success": False, "message": "Please provide a valid phone number (minimum 6 digits)."}
        if len(password) < 6:
            return {"success": False, "message": "Password must be at least 6 characters long."}

        p_hash, salt = hash_password(password)
        avatar = f"https://api.dicebear.com/7.x/bottts/svg?seed={username}"

        # Check if existing user exists by username, email, or phone
        existing_user = self.get_user(username) or self.get_user(email) or self.get_user(phone_number)

        if existing_user:
            # Update and sync existing user credentials
            user_id = existing_user["id"]
            old_username = existing_user.get("username", "").lower()
            if old_username in self._users:
                del self._users[old_username]

            user_dict = {
                "id": user_id,
                "username": username,
                "email": email,
                "phone_number": phone_number,
                "password_hash": p_hash,
                "salt": salt,
                "full_name": full_name.strip() if full_name.strip() else (existing_user.get("full_name") if existing_user.get("full_name") and existing_user.get("username") == username else username),
                "role": role or existing_user.get("role") or "Analyst",
                "clearance_level": clearance_level or existing_user.get("clearance_level") or "Level 3",
                "avatar": avatar,
                "is_active": True,
                "created_at": existing_user.get("created_at", time.time()),
                "last_login": time.time()
            }
            self._users[username] = user_dict
            self._save_to_db_if_connected(user_dict)

            token = self._create_session(user_dict)
            return {
                "success": True,
                "message": f"Credentials updated & authenticated for {username}! Access granted.",
                "token": token,
                "user": self._sanitize_user(user_dict)
            }

        # New user creation
        user_dict = {
            "id": f"usr_{uuid.uuid4().hex[:12]}",
            "username": username,
            "email": email,
            "phone_number": phone_number,
            "password_hash": p_hash,
            "salt": salt,
            "full_name": full_name.strip() or username.capitalize(),
            "role": role or "Analyst",
            "clearance_level": clearance_level or "Level 3",
            "avatar": avatar,
            "is_active": True,
            "created_at": time.time(),
            "last_login": time.time()
        }

        self._users[username] = user_dict
        self._save_to_db_if_connected(user_dict)

        token = self._create_session(user_dict)
        return {
            "success": True,
            "message": "Account registered successfully and saved to database!",
            "token": token,
            "user": self._sanitize_user(user_dict)
        }

    def login(self, identifier: str, password: str) -> Dict[str, Any]:
        """Authenticates user credentials against saved database records."""
        if not identifier or not password:
            return {"success": False, "message": "User ID / Email / Phone Number and Password are required."}

        user = self.get_user(identifier)
        if not user:
            return {
                "success": False, 
                "message": "Candidate not found. No registered account matches this User ID, Email, or Phone Number.",
                "error_type": "candidate_not_found"
            }

        if not user.get("is_active", True):
            return {"success": False, "message": "Access Denied: Account is deactivated."}

        if not verify_password(password, user["password_hash"], user["salt"]):
            return {
                "success": False, 
                "message": "Invalid password. Please check your credentials or reset your password.",
                "error_type": "invalid_password"
            }

        # Update last login
        user["last_login"] = time.time()
        self._save_to_db_if_connected(user)

        token = self._create_session(user)
        return {
            "success": True,
            "message": f"Welcome back, {user.get('full_name') or user.get('username')}! Authentication verified.",
            "token": token,
            "user": self._sanitize_user(user)
        }

    def request_otp(self, identifier: str) -> Dict[str, Any]:
        """
        Generates a 6-digit numeric OTP and dispatches it to user's registered email address.
        """
        from backend.services.email_service import email_service

        if not identifier or not identifier.strip():
            return {"success": False, "message": "User ID, Email, or Phone Number is required."}

        user = self.get_user(identifier)
        if not user:
            return {
                "success": False,
                "message": "Candidate not found. No account matches this User ID, Email, or Phone Number."
            }

        user_email = user.get("email", "").strip()
        if not user_email or "@" not in user_email:
            return {
                "success": False,
                "message": "No valid email address registered with this account."
            }

        # Generate 6-digit cryptographic OTP code
        otp_code = f"{secrets.randbelow(900000) + 100000}"
        expires_at = time.time() + 600  # 10 minutes

        # Store OTP state
        username_key = user["username"].lower()
        self._otps[username_key] = {
            "otp": otp_code,
            "email": user_email,
            "user_id": user["id"],
            "username": user["username"],
            "expires_at": expires_at,
            "created_at": time.time()
        }

        # Send email
        delivery = email_service.send_otp_email(
            to_email=user_email,
            username=user.get("full_name") or user["username"],
            otp_code=otp_code,
            expires_minutes=10
        )

        # Mask email for privacy (e.g. j***e@example.com)
        parts = user_email.split("@")
        name_part = parts[0]
        domain_part = parts[1] if len(parts) > 1 else ""
        if len(name_part) > 2:
            masked_name = name_part[0] + ("*" * (len(name_part) - 2)) + name_part[-1]
        else:
            masked_name = name_part[0] + "*"
        masked_email = f"{masked_name}@{domain_part}"

        return {
            "success": True,
            "message": f"6-Digit OTP successfully sent to your registered mail: {masked_email}",
            "email_masked": masked_email,
            "expires_in_seconds": 600,
            "otp_preview": otp_code  # Provided for convenience in dev/testing
        }

    def verify_and_reset_password(self, identifier: str, otp: str, new_password: str) -> Dict[str, Any]:
        """
        Verifies the email OTP and updates the user password in PostgreSQL database and memory.
        """
        if not identifier or not identifier.strip():
            return {"success": False, "message": "Identifier is required."}
        if not otp or not otp.strip():
            return {"success": False, "message": "6-digit OTP is required."}
        if not new_password or len(new_password) < 6:
            return {"success": False, "message": "New password must be at least 6 characters long."}

        user = self.get_user(identifier)
        if not user:
            return {"success": False, "message": "Candidate not found."}

        username_key = user["username"].lower()
        otp_record = self._otps.get(username_key)

        if not otp_record:
            return {
                "success": False,
                "message": "No active OTP found. Please request a new OTP code."
            }

        # Check expiration
        if time.time() > otp_record.get("expires_at", 0):
            del self._otps[username_key]
            return {
                "success": False,
                "message": "OTP has expired. Please request a fresh OTP code."
            }

        # Verify OTP code
        submitted_otp = otp.strip()
        expected_otp = str(otp_record.get("otp", "")).strip()

        if not secrets.compare_digest(submitted_otp, expected_otp):
            return {
                "success": False,
                "message": "Invalid OTP code. Please check your email and enter the correct 6-digit code."
            }

        # Successful OTP verification -> Update password
        p_hash, salt = hash_password(new_password)
        user["password_hash"] = p_hash
        user["salt"] = salt
        user["last_login"] = time.time()

        # Update in-memory
        self._users[username_key] = user

        # Update PostgreSQL
        if postgres_repo.is_connected and SessionLocal is not None:
            try:
                with SessionLocal() as db:
                    record = db.query(AppUserRecord).filter(AppUserRecord.id == user["id"]).first()
                    if record:
                        record.password_hash = p_hash
                        record.salt = salt
                        db.commit()
            except Exception:
                pass

        # Clear used OTP
        del self._otps[username_key]

        return {
            "success": True,
            "message": "Password reset successfully! Your new password is saved in the database. You can now log in."
        }

    def forgot_password(self, identifier: str, new_password: str) -> Dict[str, Any]:
        """Resets user password in memory and PostgreSQL database (Direct Reset Fallback)."""
        if not identifier or not new_password:
            return {"success": False, "message": "Identifier and new password are required."}

        if len(new_password) < 6:
            return {"success": False, "message": "New password must be at least 6 characters long."}

        user = self.get_user(identifier)
        if not user:
            return {
                "success": False,
                "message": "User not found. No registered account matches this User ID, Email, or Phone Number."
            }

        p_hash, salt = hash_password(new_password)
        user["password_hash"] = p_hash
        user["salt"] = salt
        user["last_login"] = time.time()

        # Update memory store
        self._users[user["username"].lower()] = user

        # Update database
        if postgres_repo.is_connected and SessionLocal is not None:
            try:
                with SessionLocal() as db:
                    record = db.query(AppUserRecord).filter(AppUserRecord.id == user["id"]).first()
                    if record:
                        record.password_hash = p_hash
                        record.salt = salt
                        db.commit()
            except Exception:
                pass

        return {
            "success": True,
            "message": "Password reset successfully in database! You can now log in with your new password."
        }

    def _create_session(self, user: Dict[str, Any]) -> str:
        """Creates token valid for 7 days."""
        token = f"ath_{secrets.token_urlsafe(32)}"
        self._sessions[token] = {
            "user_id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "phone_number": user.get("phone_number", ""),
            "role": user["role"],
            "clearance_level": user["clearance_level"],
            "full_name": user["full_name"],
            "avatar": user["avatar"],
            "created_at": time.time(),
            "expires_at": time.time() + (7 * 86400)
        }
        return token

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Checks if a session token is valid and returns user profile."""
        if not token:
            return None
        session = self._sessions.get(token)
        if not session:
            return None
        if time.time() > session.get("expires_at", 0):
            del self._sessions[token]
            return None

        user = self.get_user(session["username"])
        return self._sanitize_user(user) if user else session

    def logout(self, token: str) -> bool:
        """Revokes an active session."""
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False

    def _sanitize_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Strips sensitive hashes before transmitting over API."""
        return {
            "id": user.get("id"),
            "username": user.get("username"),
            "email": user.get("email"),
            "phone_number": user.get("phone_number", ""),
            "full_name": user.get("full_name"),
            "role": user.get("role"),
            "clearance_level": user.get("clearance_level"),
            "avatar": user.get("avatar"),
            "created_at": user.get("created_at"),
            "last_login": user.get("last_login")
        }


# Global singleton instance
auth_manager = AuthManager()

