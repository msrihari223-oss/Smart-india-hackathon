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


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Generates a salted SHA-256 hash for secure credential storage."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hashed, salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifies candidate plaintext against the stored salt + hash."""
    candidate_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return secrets.compare_digest(candidate_hash, stored_hash)


class AuthManager:
    def __init__(self):
        # In-memory users store: username -> dict
        self._users: Dict[str, Dict[str, Any]] = {}
        # Active sessions: token -> dict (user details + expires_at)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        # Pre-seed intelligence operator accounts
        self._seed_default_accounts()

    def _seed_default_accounts(self):
        """Pre-seeds system with default authorized operations personnel."""
        defaults = [
            {
                "username": "admin",
                "email": "admin@aetheria.intelligence.io",
                "password": "admin123",
                "full_name": "Director Sarah Vance",
                "role": "Director / Admin",
                "clearance_level": "Level 5 - Top Secret",
                "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=DirectorSarah"
            },
            {
                "username": "analyst",
                "email": "analyst@aetheria.intelligence.io",
                "password": "sentinel2026",
                "full_name": "Dr. Marcus Chen",
                "role": "Lead Data Analyst",
                "clearance_level": "Level 3 - Secret",
                "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=MarcusChen"
            },
            {
                "username": "operator",
                "email": "operator@aetheria.intelligence.io",
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
        """Finds user by username or email from memory or PostgreSQL."""
        identifier_clean = identifier.strip().lower()

        # Check in-memory store
        for u in self._users.values():
            if u["username"].lower() == identifier_clean or u["email"].lower() == identifier_clean:
                return u

        # Check database if available
        if postgres_repo.is_connected and SessionLocal is not None:
            try:
                with SessionLocal() as db:
                    record = db.query(AppUserRecord).filter(
                        (AppUserRecord.username.ilike(identifier_clean)) | 
                        (AppUserRecord.email.ilike(identifier_clean))
                    ).first()
                    if record:
                        u_dict = {
                            "id": record.id,
                            "username": record.username,
                            "email": record.email,
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

    def register(self, username: str, email: str, password: str, full_name: str = "", role: str = "Analyst", clearance_level: str = "Level 3") -> Dict[str, Any]:
        """Registers a new user account with validation."""
        username = username.strip().lower()
        email = email.strip().lower()

        if len(username) < 3:
            return {"success": False, "message": "Username must be at least 3 characters long."}
        if "@" not in email or "." not in email:
            return {"success": False, "message": "Please provide a valid email address."}
        if len(password) < 6:
            return {"success": False, "message": "Password must be at least 6 characters long."}

        # Check for duplicate
        if self.get_user(username) or self.get_user(email):
            return {"success": False, "message": "An account with this username or email already exists."}

        p_hash, salt = hash_password(password)
        avatar = f"https://api.dicebear.com/7.x/bottts/svg?seed={username}"

        user_dict = {
            "id": f"usr_{uuid.uuid4().hex[:12]}",
            "username": username,
            "email": email,
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
            "message": "Access granted. Account profile registered.",
            "token": token,
            "user": self._sanitize_user(user_dict)
        }

    def login(self, identifier: str, password: str) -> Dict[str, Any]:
        """Authenticates user credentials and generates active session token."""
        user = self.get_user(identifier)
        if not user:
            return {"success": False, "message": "Access Denied: Invalid operator handle or security passcode."}

        if not user.get("is_active", True):
            return {"success": False, "message": "Access Denied: Account is deactivated."}

        if not verify_password(password, user["password_hash"], user["salt"]):
            return {"success": False, "message": "Access Denied: Invalid operator handle or security passcode."}

        # Update last login
        user["last_login"] = time.time()
        self._save_to_db_if_connected(user)

        token = self._create_session(user)
        return {
            "success": True,
            "message": "Authentication verified. Access permitted.",
            "token": token,
            "user": self._sanitize_user(user)
        }

    def _create_session(self, user: Dict[str, Any]) -> str:
        """Creates token valid for 7 days."""
        token = f"ath_{secrets.token_urlsafe(32)}"
        self._sessions[token] = {
            "user_id": user["id"],
            "username": user["username"],
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
            "full_name": user.get("full_name"),
            "role": user.get("role"),
            "clearance_level": user.get("clearance_level"),
            "avatar": user.get("avatar"),
            "created_at": user.get("created_at"),
            "last_login": user.get("last_login")
        }


# Global singleton instance
auth_manager = AuthManager()
