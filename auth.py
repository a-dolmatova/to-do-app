from datetime import datetime, timedelta
from jose import jwt, JWTError
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import session_local


SECRET_KEY = "secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(request: Request,
                           token: str = Depends(oauth2_scheme),
                           db: Session = Depends(get_db)):
    if not token:
        auth_cookie = request.cookies.get("Authorization")
        if not auth_cookie:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Неавторизованный",
                                headers={"WWW-Authenticate": "Bearer"})
        scheme, _, param = auth_cookie.partition(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Неверный формат токена.",
                                headers={"WWW-Authenticate": "Bearer"})
        token = param

    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail="Не удалось проверить учетные данные пользователя.",
                                          headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    from crud import get_user
    user = get_user(db, int(user_id))
    if not user:
        raise credentials_exception
    return user