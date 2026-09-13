from typing import Any, Optional
import json
from sqlalchemy.exc import NoResultFound
from .db import get_session, AppState


def get_state(key: str) -> Optional[Any]:
    try:
        sess = get_session()
        with sess.begin():
            row = sess.get(AppState, key)
            if row is None or row.value is None:
                return None
            return json.loads(row.value)
    except Exception:
        return None


def set_state(key: str, value: Any) -> bool:
    try:
        sess = get_session()
        with sess.begin():
            obj = sess.get(AppState, key)
            v = json.dumps(value, ensure_ascii=False)
            if obj is None:
                obj = AppState(key=key, value=v)
                sess.add(obj)
            else:
                obj.value = v
                sess.add(obj)
        return True
    except Exception:
        return False


def migrate_json_file_to_state(path: str, key: str) -> bool:
    try:
        import os
        if not os.path.exists(path):
            return False
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return set_state(key, data)
    except Exception:
        return False
