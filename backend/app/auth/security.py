"""JWT 보안 모듈 - 비밀번호 해싱 및 토큰 관리."""

import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.user import User as UserModel

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_password_hash(password: str) -> str:
    """비밀번호 해싱 (bcrypt)"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """JWT 토큰 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """JWT 토큰 디코딩"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰",
        )


def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> UserModel:
    """현재 사용자 인증 - DB에서 실제 User 객체 조회"""
    payload = decode_access_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증되지 않은 사용자",
        )

    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다",
            )
        return user
    finally:
        db.close()
