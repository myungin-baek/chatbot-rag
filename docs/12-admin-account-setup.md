# 12. 관리자 계정 초기화 및 설정

## 개요

FastAPI 백엔드 앱 시작 시 자동으로 관리자 계정을 생성하는 스크립트입니다.
PostgreSQL의 users 테이블에 bcrypt 해시로 저장됩니다.

## 관리자 계정 정보

| 항목 | 값 |
|------|-----|
| ID (username) | `admin` |
| Password | `sjaksahffk.` |
| Role | `admin` |

## 데이터베이스 스키마

### users 테이블

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id       VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    username      VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT           NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'user',
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 역할 제한
ALTER TABLE users ADD CONSTRAINT chk_user_role 
    CHECK (role IN ('admin', 'user'));

-- 인덱스
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
```

## SQLAlchemy 모델 (`backend/app/models/user.py`)

```python
from datetime import datetime
from sqlalchemy import Boolean, Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(username={self.username}, role={self.role})>"
```

## 초기화 스크립트 (`backend/app/auth/initial_data.py`)

```python
import os
from sqlalchemy.orm import Session
from app.models.user import User
from app.auth.security import get_password_hash, verify_password

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "sjaksahffk.")


def init_admin_user(db: Session) -> None:
    """관리자 계정 초기 생성"""
    admin = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    
    if not admin:
        admin = User(
            username=ADMIN_USERNAME,
            password_hash=get_password_hash(ADMIN_PASSWORD),
            role="admin",
        )
        db.add(admin)
        db.commit()
        print(f"[INIT] Admin user '{ADMIN_USERNAME}' created.")
    else:
        # 비밀번호 초기화 (운영 시 주석 처리 권장)
        if not verify_password(ADMIN_PASSWORD, admin.password_hash):
            admin.password_hash = get_password_hash(ADMIN_PASSWORD)
            db.commit()
            print(f"[INIT] Admin password reset for '{ADMIN_USERNAME}'.")


def init_default_user(db: Session) -> None:
    """기본 사용자 계정 생성 (테스트용)"""
    default_username = "user"
    default_password = os.getenv("DEFAULT_USER_PASSWORD", "password123")
    
    user = db.query(User).filter(User.username == default_username).first()
    
    if not user:
        user = User(
            username=default_username,
            password_hash=get_password_hash(default_password),
            role="user",
        )
        db.add(user)
        db.commit()
        print(f"[INIT] Default user '{default_username}' created.")


def init_all_users(db: Session) -> None:
    """모든 기본 계정 초기화"""
    init_admin_user(db)
    # init_default_user(db)  # 테스트용, 운영 시 주석 처리
```

## 보안 미들웨어 (`backend/app/auth/security.py`)

```python
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
import os

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_password_hash(password: str) -> str:
    """비밀번호 해싱 (bcrypt)"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
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


def get_current_user(token: str = Depends(oauth2_scheme)):
    """현재 사용자 조회"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="잘못된 인증 정보",
    )
    
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 실제 구현에서는 DB에서 사용자 조회
    from app.database.session import get_db
    from app.models.user import User
    
    db = next(get_db())
    user = db.query(User).filter(User.username == username).first()
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


def require_admin(current_user=Depends(get_current_user)):
    """관리자 권한 확인"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다.",
        )
    return current_user


def require_user(current_user=Depends(get_current_user)):
    """일반 사용자 권한 확인"""
    if current_user.role not in ("admin", "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="접근 권한이 없습니다.",
        )
    return current_user
```

## 앱 시작 시 초기화 (`backend/app/main.py`)

```python
from fastapi import FastAPI
from app.database.session import engine, SessionLocal
from app.auth.initial_data import init_all_users

app = FastAPI(title="Chatbot RAG API")


@app.on_event("startup")
async def startup():
    """앱 시작 시 관리자 계정 초기화"""
    db = SessionLocal()
    try:
        init_all_users(db)
    finally:
        db.close()


# ... 나머지 라우터 설정
```

## 로그인 API (`backend/app/api/auth.py`)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.auth.security import (
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """사용자 로그인"""
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 아이디 또는 비밀번호",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다.",
        )
    
    access_token = create_access_token(data={"sub": user.username})
    
    return LoginResponse(
        access_token=access_token,
        user_id=str(user.user_id),
        role=user.role,
    )


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """일반 사용자 등록"""
    existing = db.query(User).filter(User.username == request.username).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 존재하는 아이디입니다.",
        )
    
    from app.auth.security import get_password_hash
    
    new_user = User(
        username=request.username,
        password_hash=get_password_hash(request.password),
        role="user",
    )
    
    db.add(new_user)
    db.commit()
    
    return {"message": "계정이 생성되었습니다.", "username": request.username}
```

## 보안 권장사항

1. **비밀번호 해싱**: bcrypt 사용 (passlib)
2. **JWT 만료**: 30분으로 설정, Refresh Token 활용 고려
3. **HTTPS 전환**: 프로덕션에서는 SSL 인증서 필수 적용
4. **API Key 관리**: 환경변수로 관리, 코드에 하드코딩 금지
5. **로그인 시도 제한**: 5회 실패 시 15분 잠금 (rate limiting)

---

*문서 생성일: 2026-05-04*
