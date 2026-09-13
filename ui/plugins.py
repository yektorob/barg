import importlib
import sys
import os

from .qt import QtWidgets


def load_page_widget(modname: str) -> QtWidgets.QWidget:
    """
    همان load_page_widget قبلی:
    - ماژول را import می‌کند
    - بهترین کلاس QWidget را پیدا کرده و نمونه‌اش را برمی‌گرداند.
    """
    try:
        # اضافه کردن پوشه‌ی والد به sys.path برای دسترسی به ماژول‌های سطح بالا
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        if ":" in modname:
            modname, clsname = modname.split(":", 1)
        else:
            clsname = None

        if modname.endswith(".py"):
            modname = modname[:-3]

        # Try a few import strategies so modules work both as top-level
        # scripts and when the app is installed as a package.
        last_exc = None
        attempts = [modname]
        pkg = __package__ or ""
        if pkg:
            attempts.append(f"{pkg}.{modname}")
            root = pkg.split('.')[0]
            attempts.append(f"{root}.{modname}")
            if '.' in pkg:
                parent = pkg.rsplit('.', 1)[0]
                attempts.append(f"{parent}.{modname}")

        mod = None
        for m in attempts:
            try:
                mod = importlib.import_module(m)
                modname = m
                break
            except Exception as e:
                last_exc = e

        if mod is None:
            raise last_exc
    except Exception as e:
        w = QtWidgets.QTextBrowser()
        w.setHtml(f"<h3>Import failed</h3><p><code>import {modname}</code><br>{e}</p>")
        return w

    best = None
    for name, obj in vars(mod).items():
        if isinstance(obj, type):
            try:
                if issubclass(obj, QtWidgets.QWidget):
                    score = 0
                    ln = name.lower()
                    for kw in ("main", "window", "widget", "page", "ui", "app"):
                        if kw in ln:
                            score += 1
                    try:
                        if issubclass(obj, QtWidgets.QMainWindow):
                            score += 1
                    except Exception:
                        pass
                    best = max(best, (score, name, obj)) if best else (score, name, obj)
            except Exception:
                pass

    if best is None:
        w = QtWidgets.QTextBrowser()
        w.setHtml(f"<h3>هیچ QWidgetای در ماژول {modname} پیدا نشد.</h3>")
        return w

    _score, name, cls = best
    try:
        return cls()
    except Exception as e:
        w = QtWidgets.QTextBrowser()
        w.setHtml(f"<h3>ساخت نمونه از {name} شکست خورد</h3><p>{e}</p>")
        return w