from collections.abc import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_optional_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User | None:
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return None
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        return None
    return user

def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Musisz się zalogować.", headers={"WWW-Authenticate": "Bearer"})
    return user

def require_verified_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Najpierw zweryfikuj adres e-mail.")
    return user

def require_roles(*roles: str) -> Callable[[User], User]:
    def dependency(user: User = Depends(require_verified_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Brak uprawnień do tej operacji.")
        return user
    return dependency
