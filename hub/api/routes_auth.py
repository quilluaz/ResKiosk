from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from hub.db.session import get_db
from hub.db.schema import User, AdminSession
from hub.core.auth import verify_password, generate_session_token, hash_token, get_current_admin, TOKEN_EXPIRATION_HOURS
import time

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/auth/login")
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email, User.is_active == 1).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = generate_session_token()
    t_hash = hash_token(token)
    now = int(time.time())
    expires_at = now + (TOKEN_EXPIRATION_HOURS * 3600)
    
    session = AdminSession(
        user_id=user.user_id,
        token_hash=t_hash,
        expires_at=expires_at,
        created_at=now,
        last_seen_at=now
    )
    db.add(session)
    user.last_login_at = now
    db.commit()
    
    response.set_cookie(
        key="admin_session",
        value=token,
        max_age=TOKEN_EXPIRATION_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=False
    )
    
    return {"status": "ok", "user": {"id": user.user_id, "email": user.email, "fname": user.fname, "role": user.role}}

@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("admin_session")
    if token:
        t_hash = hash_token(token)
        session = db.query(AdminSession).filter(AdminSession.token_hash == t_hash).first()
        if session:
            db.delete(session)
            db.commit()
            
    response.delete_cookie("admin_session")
    return {"status": "ok"}

@router.get("/auth/me")
def get_me(user: User = Depends(get_current_admin)):
    return {
        "status": "ok", 
        "user": {
            "id": user.user_id, 
            "email": user.email, 
            "fname": user.fname,
            "lname": user.lname,
            "role": user.role
        }
    }
