# core/users.py
from typing import List, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .security import hash_password
from .db import User
from .licensing import ALL_FEATURES

# فقط ماژول‌های معتبر
_VALID_FEATURE_IDS = {f["id"] for f in ALL_FEATURES}


def serialize_feature_ids(feature_ids: Optional[List[str]]) -> str:
    """
    لیست id ماژول‌ها را به رشته‌ی کاما جدا تبدیل می‌کند،
    فقط idهای معتبر را نگه می‌دارد.
    """
    if not feature_ids:
        return ""
    cleaned = sorted({fid for fid in feature_ids if fid in _VALID_FEATURE_IDS})
    return ",".join(cleaned)


def parse_feature_ids(s: Optional[str]) -> List[str]:
    """
    رشته‌ی کاما جدا را به لیست id ماژول‌ها تبدیل می‌کند،
    فقط idهای معتبر را برمی‌گرداند.
    """
    if not s:
        return []
    parts = [p.strip() for p in s.split(",")]
    return [p for p in parts if p in _VALID_FEATURE_IDS]


def ensure_admin_user(session: Session, admin_password_hash: str) -> None:
    """
    اگر هیچ کاربری در دیتابیس نیست، یک ادمین پیش‌فرض می‌سازد.
    """
    if not admin_password_hash:
        raise RuntimeError("admin_password_hash should be set before ensure_admin_user().")

    # آیا از قبل هیچ کاربری داریم؟
    existing = session.execute(select(User).limit(1)).scalars().first()
    if existing is not None:
        return

    admin = User(
        username="admin",
        password_hash=admin_password_hash,
        role="admin",
        is_active=True,
    )
    session.add(admin)
    session.commit()


def list_users(session: Session) -> List[Dict]:
    """
    همه‌ی کاربران را به‌صورت لیست dict برمی‌گرداند.
    """
    stmt = select(User).order_by(User.username)
    rows = session.execute(stmt).scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
            "password_hash": u.password_hash,
            "features": parse_feature_ids(getattr(u, "feature_perms", None)),
        }
        for u in rows
    ]


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    stmt = select(User).where(User.username == username)
    return session.execute(stmt).scalars().first()


def create_user(
    session: Session,
    username: str,
    plain_password: str,
    role: str = "user",
    feature_ids: Optional[List[str]] = None,
) -> User:
    u = User(
        username=username,
        password_hash=hash_password(plain_password),
        role=role,
        is_active=True,
        feature_perms=serialize_feature_ids(feature_ids),
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def update_user(
    session: Session,
    user_id: int,
    *,
    role: Optional[str] = None,
    plain_password: Optional[str] = None,
    is_active: Optional[bool] = None,
    feature_ids: Optional[List[str]] = None,
) -> Optional[User]:
    u = session.get(User, user_id)
    if not u:
        return None

    if role is not None:
        u.role = role
    if is_active is not None:
        u.is_active = is_active
    if plain_password:
        u.password_hash = hash_password(plain_password)
    if feature_ids is not None:
        u.feature_perms = serialize_feature_ids(feature_ids)

    session.commit()
    session.refresh(u)
    return u


def delete_user(session: Session, user_id: int) -> bool:
    u = session.get(User, user_id)
    if not u:
        return False

    session.delete(u)
    session.commit()
    return True