"""초기 데이터 - 관리자 계정 자동 생성."""

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
