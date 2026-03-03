"""
Authentication routes for the ResKiosk Hub console.

Session tokens are stored in-memory (dict). This is intentional:
- The Hub is an offline-first LAN device — no JWTs or external auth needed.
- Users simply log in again after a server restart.
"""

import time
import secrets
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from hub.db.session import get_db
from hub.db import schema
from hub.models.api_models import (
    LoginRequest, LoginResponse,
    ProfileSetupRequest, UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

# ── In-memory session store: token → user_id ──────────────────────────────────
_sessions: dict[str, int] = {}

_bearer = HTTPBearer(auto_error=False)


# ── Password helpers ──────────────────────────────────────────────────────────

def _get_pwd_context():
    try:
        from passlib.context import CryptContext
        return CryptContext(schemes=["bcrypt"], deprecated="auto")
    except ImportError:
        return None


def _verify_password(plain: str, hashed: str) -> bool:
    ctx = _get_pwd_context()
    if ctx:
        return ctx.verify(plain, hashed)
    # Fallback plain: prefix (non-production)
    import hashlib
    if hashed.startswith("plain:"):
        return hashed == "plain:" + hashlib.sha256(plain.encode()).hexdigest()
    return False


def _hash_password(plain: str) -> str:
    ctx = _get_pwd_context()
    if ctx:
        return ctx.hash(plain)
    import hashlib
    return "plain:" + hashlib.sha256(plain.encode()).hexdigest()


# ── Auth dependency ───────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> schema.User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    user_id = _sessions.get(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    user = db.query(schema.User).filter(schema.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> schema.User | None:
    """Return the logged-in user, or None if no valid token is present (no 401)."""
    if not credentials or credentials.scheme.lower() != "bearer":
        return None
    user_id = _sessions.get(credentials.credentials)
    if not user_id:
        return None
    return db.query(schema.User).filter(schema.User.user_id == user_id).first()


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with username + password. Returns a session token."""
    user = db.query(schema.User).filter(schema.User.username == payload.username).first()
    if not user or not _verify_password(payload.password, user.password or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = secrets.token_urlsafe(32)
    _sessions[token] = user.user_id
    logger.info("[Auth] User '%s' (id=%d) logged in.", user.username, user.user_id)
    return LoginResponse(
        token=token,
        user_id=user.user_id,
        username=user.username,
        fname=user.fname,
        lname=user.lname,
        is_first_login=bool(user.is_first_login),
    )


@router.post("/setup", response_model=UserResponse)
def setup_profile(
    payload: ProfileSetupRequest,
    current_user: schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """First-login: set first name, last name, and a new password."""
    if not payload.first_name.strip():
        raise HTTPException(status_code=400, detail="First name is required")
    if not payload.last_name.strip():
        raise HTTPException(status_code=400, detail="Last name is required")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    current_user.fname = payload.first_name.strip()
    current_user.lname = payload.last_name.strip()
    current_user.password = _hash_password(payload.new_password)
    current_user.is_first_login = False
    db.commit()
    db.refresh(current_user)
    logger.info("[Auth] User '%s' completed profile setup.", current_user.username)
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        fname=current_user.fname,
        lname=current_user.lname,
        is_first_login=False,
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: schema.User = Depends(get_current_user)):
    """Return current authenticated user info."""
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        fname=current_user.fname,
        lname=current_user.lname,
        is_first_login=bool(current_user.is_first_login),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    """Invalidate the current session token."""
    if credentials and credentials.scheme.lower() == "bearer":
        _sessions.pop(credentials.credentials, None)
