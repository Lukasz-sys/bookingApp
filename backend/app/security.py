from datetime import datetime, timedelta
import hashlib, secrets
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def create_access_token(user_id: int, role: str) -> str:
    now = datetime.utcnow()
    payload = {"sub": str(user_id), "role": role, "iat": int(now.timestamp()), "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

def create_email_verification_token():
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw), datetime.utcnow() + timedelta(hours=48)
