"""인증 API - 로그인 및 사용자 등록."""

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
