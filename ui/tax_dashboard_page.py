# ui/tax_dashboard_page.py
# -*- coding: utf-8 -*-
import os
import sys
import importlib
import traceback
import datetime
import webbrowser

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

# مسیر پروژه را به sys.path اضافه می‌کنیم تا tax_apps و widgets پیدا شود
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))      # .../ui
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)                  # ریشه پروژه
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ----------------------------
# لینک خارجیِ گزارش عملکرد
# ----------------------------
PERFORMANCE_EMBED_URL = (
    "https://lookerstudio.google.com/embed/reporting/"
    "9d2d70dd-713c-4c9e-886d-af9061382890/page/page_12345"
)

# ----------------------------
# تنظیمات تب‌ها
# ----------------------------
DEFAULT_APPS = [
    {"title": "اقدامات",  "module": "tax_apps.app2", "class": "App2Widget"},
    {"title": "ثبت شرکت",     "module": "tax_apps.app1", "class": "MainWindow"},
    {"title": "پرونده شرکت ها",     "module": "tax_apps.app3", "class": "App3Widget"},
    # تب لینک‌محور (فقط لینک باز می‌شود؛ هیچ ویجتی لود نمی‌کنیم، پلاسیهلدر نمایش داده می‌شود)
    {"title": "گزارش گیری", "external_url": PERFORMANCE_EMBED_URL},
]


# ----------------------------
# سربرگ تب با خط زرد متحرک
# ----------------------------
class TabHeader(QtWidgets.QWidget):
    tabChanged = QtCore.Signal(int)
    tabClicked = QtCore.Signal(int)  # هر کلیک—even روی تب فعال

    def __init__(self, tabs, parent=None):
        super().__init__(parent)
        self.setObjectName("TaxTabsHeader")
        self.setLayoutDirection(Qt.RightToLeft)

        self._buttons = []
        self._current = -1

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 6, 0)
        root.setSpacing(0)

        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addStretch(1)

        for i, t in enumerate(tabs):
            btn = QtWidgets.QPushButton(t, self)
            btn.setObjectName("TaxTabBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda _, x=i: self._on_btn_clicked(x))
            self._buttons.append(btn)
            row.addWidget(btn, 0, Qt.AlignLeft)

        row.addStretch(10)
        root.addLayout(row)

        # خط زرد زیر تب فعال
        self._ind = QtWidgets.QFrame(self)
        self._ind.setObjectName("TabUnderline")
        self._ind.setFixedHeight(3)
        self._ind.show()

        self._anim = QtCore.QPropertyAnimation(self._ind, b"geometry", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        self._apply_local_qss()
        QtCore.QTimer.singleShot(0, lambda: self.setCurrent(0))

    def _on_btn_clicked(self, idx: int):
        # همیشه کلیک را اعلام کن (برای تب لینک‌محور لازم داریم)
        self.tabClicked.emit(idx)
        # سپس اگر تب عوض شد، سیگنال تغییر تب را بده
        self.setCurrent(idx)

    def _apply_local_qss(self):
        self.setStyleSheet("""
        #TaxDashboardPage #TaxTabsHeader { background: transparent; }
        #TaxDashboardPage #TaxTabsHeader #TaxTabBtn {
            background: transparent; border: none; padding: 10px 12px 12px 12px;
            color: #F5F5F5; font-weight: 600;
        }
        #TaxDashboardPage #TaxTabsHeader #TaxTabBtn:hover { color: #FFFFFF; }
        #TaxDashboardPage #TaxTabsHeader #TaxTabBtn:checked { color: #FFFFFF; }
        #TaxDashboardPage #TaxTabsHeader #TabUnderline { background: #ffa500; border: none; }
        """)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if 0 <= self._current < len(self._buttons):
            self._move_indicator(self._current, animate=False)

    def setCurrent(self, index: int):
        if index == self._current:
            return
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)
        if 0 <= self._current < len(self._buttons):
            self._buttons[self._current].setChecked(False)
        old = self._current
        self._current = index
        self._move_indicator(index, animate=(old != -1))
        self.tabChanged.emit(index)

    def _move_indicator(self, index: int, animate=True):
        btn = self._buttons[index]
        p = btn.mapTo(self, QtCore.QPoint(0, 0))
        w = btn.width()
        h = self.height()
        target = QtCore.QRect(p.x(), h - self._ind.height(), w, self._ind.height())
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._ind.geometry())
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._ind.setGeometry(target)


# ----------------------------
# صفحه داشبورد مالیاتی
# ----------------------------
class TaxDashboardPage(QtWidgets.QWidget):
    def __init__(self, apps=None, parent=None):
        super().__init__(parent)
        self.setObjectName("TaxDashboardPage")
        self.setLayoutDirection(Qt.RightToLeft)

        self._apps = apps or DEFAULT_APPS
        self._loaded = [False] * len(self._apps)
        self._widgets = [None] * len(self._apps)
        self._calendar_index = self._find_calendar_index()
        self._performance_index = self._find_performance_index()

        # UI
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 8, 16, 16)
        root.setSpacing(10)

        # نوار ابزار بالا — فقط دکمه «برو به امروز» سمت چپ
        tools_bar = QtWidgets.QWidget(self)
        tools_bar.setLayoutDirection(Qt.LeftToRight)
        hb = QtWidgets.QHBoxLayout(tools_bar)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(8)
        hb.addStretch(1)
        self.btn_today = QtWidgets.QPushButton("برو به امروز", tools_bar)
        self.btn_today.setObjectName("TodayBtn")
        self.btn_today.setCursor(Qt.PointingHandCursor)
        self.btn_today.setFixedHeight(32)
        hb.addWidget(self.btn_today, 0, Qt.AlignLeft)
        root.addWidget(tools_bar)

        # سربرگ تب‌ها
        self.header = TabHeader([a["title"] for a in self._apps], self)
        self.header.tabChanged.connect(self._on_tab_changed)
        self.header.tabClicked.connect(self._on_tab_clicked)  # برای کلیک‌های تکراری روی همان تب
        root.addWidget(self.header)

        # بدنه صفحات
        self.stack = QtWidgets.QStackedWidget(self)
        root.addWidget(self.stack, 1)

        # صفحه‌های اولیه (Placeholder)
        for i, app in enumerate(self._apps):
            if i == self._performance_index:
                self.stack.addWidget(self._make_external_placeholder(i))
            else:
                self.stack.addWidget(self._make_placeholder(i))

        # استایل محلی TodayBtn
        self.setStyleSheet("""
        #TodayBtn {
            border:1px solid #383838; border-radius:16px; background:#2C2E33;
            color:#F5F5F5; padding:0 12px; min-width:110px;
        }
        #TodayBtn:hover { border-color:#FFFFFF; }
        """)

        # سیگنال دکمه today
        self.btn_today.clicked.connect(self._on_go_today_clicked)
        self.btn_today.setVisible(False)

    # --------- Placeholder / Error ------
    def _make_placeholder(self, i):
        w = QtWidgets.QWidget()
        w.setLayoutDirection(Qt.RightToLeft)
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 12, 0, 0)
        v.setSpacing(12)

        title = QtWidgets.QLabel(self._apps[i]["title"])
        title.setStyleSheet("color:#F5F5F5; font-weight:700;")
        title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        sub = QtWidgets.QLabel("برای بارگذاری، تب را انتخاب کنید.")
        sub.setStyleSheet("color:#A0A0A0;")
        sub.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        v.addWidget(title)
        v.addWidget(sub, 0, Qt.AlignRight)
        v.addStretch(1)
        return w

    def _make_external_placeholder(self, i):
        # پلاسیهلدر مخصوص تب لینک‌محور
        w = QtWidgets.QWidget()
        w.setLayoutDirection(Qt.RightToLeft)
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 24, 0, 0)
        v.setSpacing(8)

        title = QtWidgets.QLabel(self._apps[i]["title"])
        title.setStyleSheet("color:#F5F5F5; font-weight:700;")
        title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        sub = QtWidgets.QLabel("این تب فقط لینک گزارش را در مرورگر باز می‌کند.")
        sub.setStyleSheet("color:#A0A0A0;")
        sub.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        v.addWidget(title)
        v.addWidget(sub, 0, Qt.AlignRight)
        v.addStretch(1)
        return w

    def _make_error(self, i, err_msg, tb_text):
        w = QtWidgets.QWidget()
        w.setLayoutDirection(Qt.RightToLeft)
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 12, 0, 0)
        v.setSpacing(10)

        lab = QtWidgets.QLabel(f"خطا در بارگذاری «{self._apps[i]['title']}»")
        lab.setStyleSheet("color:#F5F5F5; font-weight:700;")
        lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        msg = QtWidgets.QLabel(err_msg)
        msg.setStyleSheet("color:#D32F2F;")
        msg.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        msg.setTextInteractionFlags(Qt.TextSelectableByMouse)

        tb = QtWidgets.QTextEdit()
        tb.setReadOnly(True)
        tb.setStyleSheet("background:transparent; color:#A0A0A0; border:1px solid #383838; border-radius:8px;")
        tb.setPlainText(tb_text)

        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        retry = QtWidgets.QPushButton("🔄 تلاش مجدد")
        retry.setCursor(Qt.PointingHandCursor)
        retry.setProperty("variant", "primary")
        retry.clicked.connect(lambda: self._reload_tab(i))
        row.addWidget(retry)

        v.addWidget(lab)
        v.addWidget(msg)
        v.addWidget(tb, 1)
        v.addLayout(row)
        return w

    # ---------- تب ----------
    def _on_tab_clicked(self, index: int):
        """هر کلیک—even روی تب فعال—اگر تب لینک‌محور است، لینک را باز کن."""
        if index == self._performance_index:
            url = self._apps[index].get("external_url") or PERFORMANCE_EMBED_URL
            try:
                webbrowser.open(url, new=2)
            except Exception:
                pass

    def _on_tab_changed(self, index):
        """فقط مدیریت UI/لود؛ اینجا لینک را باز نکن تا دوبار باز نشود."""
        self.stack.setCurrentIndex(index)

        if index == self._performance_index:
            # روی همین تب بمان و پلاسیهلدر نشان بده
            self.btn_today.setVisible(False)
            self._loaded[index] = True
            self._widgets[index] = self.stack.widget(index)
            return

        # تب‌های معمولی
        if not self._loaded[index]:
            self._ensure_loaded(index)

        is_calendar = (index == self._calendar_index)
        self.btn_today.setVisible(is_calendar)
        if is_calendar:
            self._select_today_on_calendar()

    def _reload_tab(self, index):
        self._loaded[index] = False
        self._widgets[index] = None
        self.stack.removeWidget(self.stack.widget(index))
        # برای تب لینک‌محور هم همان پلاسیهلدر مخصوص را بازسازی کن
        if index == self._performance_index:
            self.stack.insertWidget(index, self._make_external_placeholder(index))
            # برای external چیزی لود نمی‌کنیم
            self._loaded[index] = True
            self._widgets[index] = self.stack.widget(index)
        else:
            self.stack.insertWidget(index, self._make_placeholder(index))
            QtCore.QTimer.singleShot(0, lambda: self._ensure_loaded(index))
        self.stack.setCurrentIndex(index)

    def _ensure_loaded(self, index):
        app = self._apps[index]

        # اگر تب لینک‌محور است، اصلاً چیزی لود نکن
        if app.get("external_url"):
            self._loaded[index] = True
            self._widgets[index] = self.stack.widget(index)  # همان پلاسیهلدر
            return

        mod_name = app["module"]
        cls_name = app["class"]

        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            tb = traceback.format_exc()
            self._show_error(index, f"ماژول پیدا نشد یا خطا داشت: {e}", tb)
            return

        try:
            cls = getattr(mod, cls_name, None)
            if cls is None:
                raise AttributeError(f"کلاس «{cls_name}» در «{mod_name}» یافت نشد.")
            widget = cls(parent=self)
            if not isinstance(widget, QtWidgets.QWidget):
                raise TypeError("کلاس انتخابی باید زیرکلاس QWidget باشد.")
        except Exception as e:
            tb = traceback.format_exc()
            self._show_error(index, f"ساخت ویجت با خطا مواجه شد: {e}", tb)
            return

        self._widgets[index] = widget
        self._loaded[index] = True

        old = self.stack.widget(index)
        self.stack.removeWidget(old)
        old.deleteLater()
        self.stack.insertWidget(index, widget)
        self.stack.setCurrentIndex(index)

    def _show_error(self, index, msg, tb):
        err = self._make_error(index, msg, tb)
        old = self.stack.widget(index)
        self.stack.removeWidget(old)
        old.deleteLater()
        self.stack.insertWidget(index, err)
        self.stack.setCurrentIndex(index)

    # ---------- Today helpers ----------
    def _find_calendar_index(self) -> int:
        for i, a in enumerate(self._apps):
            if a.get("module") == "tax_apps.app2" and a.get("class") == "App2Widget":
                return i
        return 0

    def _find_performance_index(self) -> int:
        for i, a in enumerate(self._apps):
            if a.get("external_url") or a.get("title") == "گزارش عملکرد":
                return i
        return -1

    def _get_tab_widget(self, index: int):
        if index < 0 or index >= len(self._apps):
            return None
        if self._loaded[index]:
            return self._widgets[index]
        return self.stack.widget(index)

    def _select_today_on_calendar(self):
        """انتخاب کارت امروز روی App2Widget — در صورت وجود متد داخلی."""
        idx = self._calendar_index
        if not self._loaded[idx]:
            self._ensure_loaded(idx)

        w = self._widgets[idx]
        if not isinstance(w, QtWidgets.QWidget):
            return

        # اگر خود ویجت متد «امروز» دارد
        for m in ("reset_to_today", "go_to_today", "select_today"):
            if hasattr(w, m) and callable(getattr(w, m)):
                try:
                    getattr(w, m)()
                    return
                except Exception:
                    pass

        # fallback عمومی
        try:
            app2 = importlib.import_module("tax_apps.app2")
            today = datetime.date.today()
            if hasattr(w, "today"):
                w.today = today
            if hasattr(app2, "start_of_week_saturday") and hasattr(w, "week_anchor"):
                w.week_anchor = app2.start_of_week_saturday(today)
            if hasattr(w, "selected_date"):
                w.selected_date = today
            for m in ("_rebuild_ui_state", "rebuild_ui", "refresh"):
                if hasattr(w, m) and callable(getattr(w, m)):
                    getattr(w, m)()
                    break
        except Exception:
            pass

    def _on_go_today_clicked(self):
        # دکمه فقط روی تب تقویم نمایش دارد؛ پس مستقیم today را اعمال کن
        self._select_today_on_calendar()