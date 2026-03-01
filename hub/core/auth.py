import bcrypt
import secrets
import hashlib
from typing import Optional
from datetime import datetime
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db.schema import User, AdminSession

TOKEN_EXPIRATION_HOURS = 24

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hashed version."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def generate_session_token() -> str:
    """Generate a secure, random session token."""
    return secrets.token_urlsafe(64)

def hash_token(token: str) -> str:
    """Hash a session token so the plain token is not stored in DB."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def get_current_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """FastAPI dependency to protect admin routes and return current User.
    It expects the token either in `admin_session` cookie or `Authorization: Bearer <token>` header.
    """
    token = request.cookies.get("admin_session")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    t_hash = hash_token(token)
    session = db.query(AdminSession).filter(AdminSession.token_hash == t_hash).first()

    now = int(datetime.utcnow().timestamp())
    if not session or session.expires_at < now:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    user = db.query(User).filter(User.user_id == session.user_id, User.is_active == 1).first()
    if not user:
        raise HTTPException(status_code=401, detail="User inactive or deleted")

    session.last_seen_at = now
    db.commit()

    return user

def get_current_admin_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Dependency for routes where auth is optional."""
    try:
        return get_current_admin(request, db)
    except HTTPException:
        return None
