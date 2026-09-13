from typing import List

try:
    import bcrypt
except ImportError as e:
    # بدون bcrypt برنامه رو اجرا نکن
    raise RuntimeError("Package 'bcrypt' must be installed (pip install bcrypt).") from e


def hash_password(plain: str) -> str:
    """
    هش کردن پسورد با استفاده از bcrypt.
    """
    if not isinstance(plain, str):
        raise TypeError("password must be a string")
    hashed: bytes = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, stored_hash: str) -> bool:
    """
    بررسی صحت پسورد با استفاده از bcrypt.
    """
    if not stored_hash:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        return False


def password_strength_errors(password: str) -> List[str]:
    """
    چک کردن قدرت رمز – اگر مشکلی باشه، متن خطا می‌ده.
    """
    errors: List[str] = []

    if len(password) < 8:
        errors.append("طول رمز باید حداقل ۸ کاراکتر باشد.")

    has_digit = any(c.isdigit() for c in password)
    has_alpha = any(c.isalpha() for c in password)

    if not has_alpha:
        errors.append("رمز باید حداقل یک حرف داشته باشد.")
    if not has_digit:
        errors.append("رمز باید حداقل یک رقم داشته باشد.")

    return errors 