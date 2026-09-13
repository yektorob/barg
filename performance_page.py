from typing import Dict, List

from PySide6 import QtWidgets, QtCore
from ui.widgets import StyledComboBox, StyledButton, inch

from core.db import DailyReport, get_session    # ⬅️ اضافه
from sqlalchemy import or_                      # ⬅️ اضافه

from performance_logic import PeopleProjectsSheet, TargetsSheet

# ------------------ ابزارک‌های کمکی ------------------
class NoWheelSpinBox(QtWidgets.QSpinBox):
    def wheelEvent(self, event): event.ignore()


class NoWheelComboBox(StyledComboBox):
    def wheelEvent(self, event): event.ignore()


def _vspace(h=8):
    return QtWidgets.QSpacerItem(0, h, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)


# ------------------ صفحه اصلی عملکرد ------------------
class PerformancePage(QtWidgets.QWidget):
    """
    مدیریت «افراد/پروژه‌ها/اهداف» با استفاده از دیتابیس.
    - افراد/پروژه‌ها: Performance table
    - اهداف: PerformanceTarget table
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PerformancePage")
        self.setLayoutDirection(QtCore.Qt.RightToLeft)

        # مدل‌های درون‌حافظه
        self.persons: List[str] = []
        self.projects: List[str] = []
        self._person_ids: Dict[str,str]  = {}   # name -> id
        self._project_ids: Dict[str,str] = {}   # name -> id
        self.targets: List[Dict] = []          # dict: id, person, project, minutes

        # اتصال به دیتابیس (lazy initialization)
        self.pp_sheet = None
        self.t_sheet = None
        
        # محاولهٔ اول برای لود کردن شیت‌ها
        self._init_sheets()

        # ---------- چیدمان مرکزی ----------
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        outer.addStretch(1)

        h_center = QtWidgets.QHBoxLayout()
        h_center.addStretch(1)

        # استک: این‌جا بین فرم اصلی و داشبورد سوییچ می‌کنیم
        self.stack = QtWidgets.QStackedWidget()
        self.stack.setMinimumWidth(inch(11))
        h_center.addWidget(self.stack)
        h_center.addStretch(1)

        outer.addLayout(h_center)
        outer.addStretch(1)

        # صفحه اصلی (همین فرم فعلی)
        self.main_page = QtWidgets.QFrame()
        self.main_page.setObjectName("AbbaspoorFrame")
        self.stack.addWidget(self.main_page)

        v = QtWidgets.QVBoxLayout(self.main_page)
        v.setContentsMargins(30,30,30,30)
        v.setSpacing(18)

        # --- تیتر صفحه
        title = QtWidgets.QLabel("گزارش عملکرد")
        title.setObjectName("AbbaspoorH1")
        v.addWidget(title); v.addItem(_vspace(6))

        row = QtWidgets.QHBoxLayout(); row.setSpacing(18); v.addLayout(row)

        # کارت افراد
        card_p = QtWidgets.QFrame(); card_p.setObjectName("AbbaspoorSubFrame")
        clp = QtWidgets.QVBoxLayout(card_p); clp.setContentsMargins(16,16,16,16); clp.setSpacing(10)
        cap = QtWidgets.QLabel("مدیریت افراد"); cap.setObjectName("AbbaspoorH3"); clp.addWidget(cap)
        self.list_persons = QtWidgets.QListWidget(); clp.addWidget(self.list_persons)
        btn_row_p = QtWidgets.QHBoxLayout()
        self.btn_add_person = StyledButton("➕ افزودن")
        self.btn_edit_person= StyledButton("✏️ ویرایش")
        self.btn_del_person = StyledButton("🗑️ حذف")
        btn_row_p.addWidget(self.btn_add_person); btn_row_p.addWidget(self.btn_edit_person); btn_row_p.addWidget(self.btn_del_person); btn_row_p.addStretch(1)
        clp.addLayout(btn_row_p)

        # کارت پروژه‌ها
        card_j = QtWidgets.QFrame(); card_j.setObjectName("AbbaspoorSubFrame")
        clj = QtWidgets.QVBoxLayout(card_j); clj.setContentsMargins(16,16,16,16); clj.setSpacing(10)
        caj = QtWidgets.QLabel("مدیریت پروژه‌ها"); caj.setObjectName("AbbaspoorH3"); clj.addWidget(caj)
        self.list_projects = QtWidgets.QListWidget(); clj.addWidget(self.list_projects)
        btn_row_j = QtWidgets.QHBoxLayout()
        self.btn_add_proj = StyledButton("➕ افزودن")
        self.btn_edit_proj= StyledButton("✏️ ویرایش")
        self.btn_del_proj = StyledButton("🗑️ حذف")
        btn_row_j.addWidget(self.btn_add_proj); btn_row_j.addWidget(self.btn_edit_proj); btn_row_j.addWidget(self.btn_del_proj); btn_row_j.addStretch(1)
        clj.addLayout(btn_row_j)

        row.addWidget(card_p, 1)
        row.addWidget(card_j, 1)

        v.addItem(_vspace(8))

        # کارت اهداف
        card_t = QtWidgets.QFrame(); card_t.setObjectName("AbbaspoorSubFrame")
        clt = QtWidgets.QVBoxLayout(card_t); clt.setContentsMargins(16,16,16,16); clt.setSpacing(10)
        cat = QtWidgets.QLabel("مدیریت اهداف"); cat.setObjectName("AbbaspoorH3"); clt.addWidget(cat)

        self.tbl_targets = QtWidgets.QTableWidget(0, 3)
        self.tbl_targets.setHorizontalHeaderLabels(["شخص", "پروژه", "دقیقه"])
        self.tbl_targets.horizontalHeader().setStretchLastSection(True)
        self.tbl_targets.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.tbl_targets.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.tbl_targets.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_targets.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        clt.addWidget(self.tbl_targets)

        btn_row_t = QtWidgets.QHBoxLayout()
        self.btn_add_target = StyledButton("➕ افزودن")
        self.btn_edit_target= StyledButton("✏️ ویرایش")
        self.btn_del_target = StyledButton("🗑️ حذف")
        btn_row_t.addWidget(self.btn_add_target); btn_row_t.addWidget(self.btn_edit_target); btn_row_t.addWidget(self.btn_del_target); btn_row_t.addStretch(1)
        clt.addLayout(btn_row_t)

        v.addWidget(card_t)

        # نوار پایین: فقط گزارش
        # نوار پایین: فقط گزارش
        action_bar = QtWidgets.QHBoxLayout(); action_bar.setSpacing(12)
        action_bar.addStretch(1)
        self.btn_view_report = StyledButton("📊 مشاهده گزارش")
        self.btn_view_report.setMinimumWidth(160)
        action_bar.addWidget(self.btn_view_report)
        v.addLayout(action_bar)

       # ---------- صفحه داشبورد ----------
        self.dashboard_page = QtWidgets.QFrame()
        self.dashboard_page.setObjectName("AbbaspoorFrame")

        dash_layout = QtWidgets.QVBoxLayout(self.dashboard_page)
        dash_layout.setContentsMargins(30, 30, 30, 30)
        dash_layout.setSpacing(18)

        # نوار بالا: دکمه بازگشت
        top_bar = QtWidgets.QHBoxLayout()
        self.btn_back_to_form = StyledButton("⬅️ بازگشت به تنظیم اهداف")
        top_bar.addWidget(self.btn_back_to_form)
        top_bar.addStretch(1)
        dash_layout.addLayout(top_bar)

        # تیتر داشبورد
        dash_title = QtWidgets.QLabel("داشبورد وضعیت کارهای انجام‌نشده")
        dash_title.setObjectName("AbbaspoorH1")
        dash_layout.addWidget(dash_title)
        dash_layout.addItem(_vspace(4))

        # ---------------- ردیف فیلترها (۵ کمبو) ----------------
        filters_row = QtWidgets.QHBoxLayout()
        filters_row.setSpacing(8)

        # 1) نام گزارش‌دهنده
        self.cmb_filter_person = StyledComboBox()
        self.cmb_filter_person.setEditable(True)
        self.cmb_filter_person.setPlaceholderText("نام گزارش‌دهنده")
        filters_row.addWidget(self.cmb_filter_person)

        # 2) ماه (مثلاً 1404/05)
        self.cmb_filter_month = StyledComboBox()
        self.cmb_filter_month.setEditable(True)
        self.cmb_filter_month.setPlaceholderText("ماه (مثلاً 1404/05)")
        filters_row.addWidget(self.cmb_filter_month)

        # 3) روز ماه
        self.cmb_filter_day = StyledComboBox()
        self.cmb_filter_day.setEditable(True)
        self.cmb_filter_day.setPlaceholderText("روز ماه")
        filters_row.addWidget(self.cmb_filter_day)

        # 4) روز هفته
        self.cmb_filter_weekday = StyledComboBox()
        self.cmb_filter_weekday.setEditable(True)
        self.cmb_filter_weekday.setPlaceholderText("روز هفته")
        filters_row.addWidget(self.cmb_filter_weekday)

        # 5) نام پروژه
        self.cmb_filter_project = StyledComboBox()
        self.cmb_filter_project.setEditable(True)
        self.cmb_filter_project.setPlaceholderText("نام پروژه")
        filters_row.addWidget(self.cmb_filter_project)

        dash_layout.addLayout(filters_row)
        dash_layout.addItem(_vspace(10))

        # ---------------- کارت تعداد کارهای انجام‌نشده ----------------
        card_unfinished = QtWidgets.QFrame()
        card_unfinished.setObjectName("AbbaspoorSubFrame")
        card_layout = QtWidgets.QVBoxLayout(card_unfinished)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(10)

        lbl_title = QtWidgets.QLabel("تعداد کارهای انجام‌نشده")
        lbl_title.setObjectName("AbbaspoorH3")
        card_layout.addWidget(lbl_title)

        self.lbl_unfinished_count = QtWidgets.QLabel("0")
        # استایلش رو در QSS با AbbaspoorKPI بزرگ و پررنگ کن
        self.lbl_unfinished_count.setObjectName("AbbaspoorKPI")
        self.lbl_unfinished_count.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        card_layout.addWidget(self.lbl_unfinished_count)

        dash_layout.addWidget(card_unfinished)

        # اگر بعداً چارت/جدول هم خواستی، زیر این اضافه کن

        # اضافه به استک و انتخاب صفحه‌ی اصلی
        self.stack.addWidget(self.dashboard_page)
        self.stack.setCurrentWidget(self.main_page)
        # اتصال سیگنال‌ها
        self.btn_add_person.clicked.connect(self._add_person)
        self.btn_edit_person.clicked.connect(self._edit_person)
        self.btn_del_person.clicked.connect(self._del_person)

        self.btn_add_proj.clicked.connect(self._add_project)
        self.btn_edit_proj.clicked.connect(self._edit_project)
        self.btn_del_proj.clicked.connect(self._del_project)

        self.btn_add_target.clicked.connect(self._add_target)
        self.btn_edit_target.clicked.connect(self._edit_target)
        self.btn_del_target.clicked.connect(self._del_target)

        # صفحه داشبورد / بازگشت
        self.btn_view_report.clicked.connect(self._open_report)
        self.btn_back_to_form.clicked.connect(self._back_to_form)

        # هر تغییری در فیلترها → اعمال فیلتر
        for cmb in (
            self.cmb_filter_person,
            self.cmb_filter_month,
            self.cmb_filter_day,
            self.cmb_filter_weekday,
            self.cmb_filter_project,
        ):
            cmb.currentIndexChanged.connect(self._apply_dashboard_filters)
            # بهتر شدن سرچ
            cmb.setEditable(True)
            compl = cmb.completer()
            if compl is not None:
                compl.setFilterMode(QtCore.Qt.MatchContains)
                compl.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
            cmb.setInsertPolicy(QtWidgets.QComboBox.NoInsert)

        # مقداردهی اولیه فیلترها و کارت
        self._init_dashboard_filters()

        # ⬇️ فالبک برای وقتی که QSS اصلی تو نسخه‌ی exe لود نشه
        self.setStyleSheet(self.styleSheet() + """
        QPushButton {
            background: #2C2E33;
            color: #EDEDED;
            border: 1px solid #3a3a3a;
            border-radius: 6px;
            padding: 6px 10px;
        }
        QPushButton:hover   { background: #3A3E44; }
        QPushButton:pressed { background: #272B30; }
        QPushButton:disabled{
            background: #1F2226;
            color: #888;
            border-color: #2a2a2a;
        }
        """)
        # بارگذاری اولیه از شیت‌ها
        self._load_remote_and_refresh()

    # ----------- اولین‌بار سازی ورق‌های درون‌حافظه -----------
    def _init_sheets(self):
        """لود شیت‌های درون‌حافظه از دیتابیس

        رفتار:
        - نمونه‌های `PeopleProjectsSheet` و `TargetsSheet` را می‌سازد.
        - اگر سشن دیتابیس در دسترس نباشد، تلاش می‌کند با خواندن `config` و فراخوانی
          `init_db(cfg)` دیتابیس را مقداردهی کند، سپس دوباره سشن را بررسی می‌کند.
        - در نهایت اگر سشن موجود باشد داده‌ها را لود می‌کند، وگرنه شیت‌ها را None نگه می‌دارد.
        """
        try:
            from performance_logic import PeopleProjectsSheet, TargetsSheet
        except Exception as e:
            print(f"خطا در وارد کردن performance_logic: {e}")
            self.pp_sheet = None
            self.t_sheet = None
            return

        # ایجاد نمونه‌های شیت‌ها
        self.pp_sheet = PeopleProjectsSheet()
        self.t_sheet = TargetsSheet()

        # بررسی وجود سشن؛ اگر نباشد تلاش کن دیتابیس را مقداردهی کنی
        session = None
        try:
            if getattr(self.pp_sheet, "_db", None) and hasattr(self.pp_sheet._db, "_get_session"):
                session = self.pp_sheet._db._get_session()
        except Exception:
            session = None

        if session is None:
            # تلاش برای مقداردهی دیتابیس از config
            try:
                from core.config import load_config
                from core.db import init_db, get_session
                cfg = load_config()
                init_db(cfg)
                session = get_session()
            except Exception:
                session = None

        if session is None:
            print("اطلاع: دیتابیس راه‌اندازی نشده؛ بارگذاری شیت‌ها لغو شد.")
            self.pp_sheet = None
            self.t_sheet = None
            return

        # حالا داده‌ها را لود کن
        try:
            ppl, prj = self.pp_sheet.list_all()
            self._person_ids = {name: pid for pid, name in ppl}
            self._project_ids = {name: pid for pid, name in prj}
            self.persons = list(self._person_ids.keys())
            self.projects = list(self._project_ids.keys())

            self.targets = self.t_sheet.list_all() if self.t_sheet else []
        except Exception as e:
            print(f"خطا در بارگذاری داده‌ها در _init_sheets: {e}")
            self.pp_sheet = None
            self.t_sheet = None

    # ----------- خواندن از Sheet4/Sheet5 -----------
    def _load_remote_and_refresh(self):
        # افراد/پروژه‌ها
        self.persons, self.projects = [], []
        self._person_ids.clear(); self._project_ids.clear()

        if self.pp_sheet:
            persons, projects = self.pp_sheet.list_all()
            self._person_ids  = {name: pid for (pid, name) in persons}
            self._project_ids = {name: pid for (pid, name) in projects}
            self.persons  = [name for (_,name) in persons]
            self.projects = [name for (_,name) in projects]

        self._refresh_persons()
        self._refresh_projects()

        # اهداف
        self.targets = []
        if self.t_sheet:
            self.targets = self.t_sheet.list_all()
        self._refresh_targets()

    # ----------- UI refresh -----------
    def _refresh_persons(self):
        self.list_persons.clear()
        if self.persons: self.list_persons.addItems(self.persons)

    def _refresh_projects(self):
        self.list_projects.clear()
        if self.projects: self.list_projects.addItems(self.projects)

    def _refresh_targets(self):
        self.tbl_targets.setRowCount(0)
        for t in self.targets:
            r = self.tbl_targets.rowCount()
            self.tbl_targets.insertRow(r)
            self.tbl_targets.setItem(r, 0, QtWidgets.QTableWidgetItem(t.get("person","")))
            self.tbl_targets.setItem(r, 1, QtWidgets.QTableWidgetItem(t.get("project","")))
            self.tbl_targets.setItem(r, 2, QtWidgets.QTableWidgetItem(str(t.get("minutes",0))))

    # ----------- CRUD: Persons -----------
    def _add_person(self):
        text, ok = QtWidgets.QInputDialog.getText(self, "افزودن فرد", "نام:")
        if not (ok and text): return
        name = text.strip()
        if not name: return
        if name in self.persons:
            QtWidgets.QMessageBox.critical(self, "خطا", "این نام وجود دارد."); return

        self.btn_add_person.setEnabled(False)
        try:
            if not self.pp_sheet:
                # تلاش برای مقداردهی مجدد شیت‌ها در صورت آماده شدن دیتابیس
                try:
                    self._init_sheets()
                except Exception:
                    pass
            if not self.pp_sheet:
                QtWidgets.QMessageBox.critical(self, "خطا", "Sheet4 در دسترس نیست.")
                return
            new_id = self.pp_sheet.add_name("person", name)
            self._person_ids[name] = new_id
            self.persons.append(name)
            self._refresh_persons()
            QtWidgets.QMessageBox.information(self, "موفق", "ثبت شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", f"افزودن ناموفق:\n{e}")
        finally:
            self.btn_add_person.setEnabled(True)

    def _edit_person(self):
        row = self.list_persons.currentRow()
        if row < 0: return
        old = self.persons[row]
        text, ok = QtWidgets.QInputDialog.getText(self, "ویرایش فرد", "نام جدید:", text=old)
        if not (ok and text): return
        new = text.strip()
        if not new: return
        if new != old and new in self.persons:
            QtWidgets.QMessageBox.critical(self, "خطا", "این نام وجود دارد."); return

        self.btn_edit_person.setEnabled(False)
        try:
            if not self.pp_sheet:
                try:
                    self._init_sheets()
                except Exception:
                    pass
            pid = self._person_ids.get(old)
            if not pid: raise RuntimeError("ID یافت نشد.")
            if not self.pp_sheet.edit_name(pid, new):
                raise RuntimeError("ویرایش در شیت ناموفق بود.")
            self.persons[row] = new
            self._person_ids.pop(old, None)
            self._person_ids[new] = pid
            self._refresh_persons()
            QtWidgets.QMessageBox.information(self, "موفق", "ویرایش ثبت شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", f"ویرایش ناموفق:\n{e}")
        finally:
            self.btn_edit_person.setEnabled(True)

    def _del_person(self):
        row = self.list_persons.currentRow()
        if row < 0: return
        name = self.persons[row]
        if QtWidgets.QMessageBox.question(self, "حذف", f"«{name}» حذف شود؟") != QtWidgets.QMessageBox.Yes:
            return
        self.btn_del_person.setEnabled(False)
        try:
            if not self.pp_sheet:
                try:
                    self._init_sheets()
                except Exception:
                    pass
            pid = self._person_ids.get(name, "")
            if not pid: raise RuntimeError("ID یافت نشد.")
            if not self.pp_sheet.delete_name(pid):
                raise RuntimeError("حذف در شیت ناموفق بود.")
            self.persons.pop(row); self._person_ids.pop(name, None)
            self._refresh_persons()
            QtWidgets.QMessageBox.information(self, "حذف شد", "با موفقیت حذف شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", f"حذف ناموفق:\n{e}")
        finally:
            self.btn_del_person.setEnabled(True)

    # ----------- CRUD: Projects -----------
    def _add_project(self):
        text, ok = QtWidgets.QInputDialog.getText(self, "افزودن پروژه", "نام:")
        if not (ok and text): return
        name = text.strip()
        if not name: return
        if name in self.projects:
            QtWidgets.QMessageBox.critical(self, "خطا", "این پروژه وجود دارد."); return
        self.btn_add_proj.setEnabled(False)
        try:
            if not self.pp_sheet:
                try:
                    self._init_sheets()
                except Exception:
                    pass
            if not self.pp_sheet:
                QtWidgets.QMessageBox.critical(self, "خطا", "Sheet4 در دسترس نیست.")
                return
            new_id = self.pp_sheet.add_name("project", name)
            self._project_ids[name] = new_id
            self.projects.append(name)
            self._refresh_projects()
            QtWidgets.QMessageBox.information(self, "موفق", "ثبت شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", f"افزودن ناموفق:\n{e}")
        finally:
            self.btn_add_proj.setEnabled(True)

    def _edit_project(self):
        row = self.list_projects.currentRow()
        if row < 0: return
        old = self.projects[row]
        text, ok = QtWidgets.QInputDialog.getText(self, "ویرایش پروژه", "نام جدید:", text=old)
        if not (ok and text): return
        new = text.strip()
        if not new: return
        if new != old and new in self.projects:
            QtWidgets.QMessageBox.critical(self, "خطا", "این پروژه وجود دارد."); return
        self.btn_edit_proj.setEnabled(False)
        try:
            if not self.pp_sheet:
                try:
                    self._init_sheets()
                except Exception:
                    pass
            pid = self._project_ids.get(old, "")
            if not pid: raise RuntimeError("ID یافت نشد.")
            if not self.pp_sheet.edit_name(pid, new):
                raise RuntimeError("ویرایش در شیت ناموفق بود.")
            self.projects[row] = new
            self._project_ids.pop(old, None)
            self._project_ids[new] = pid
            self._refresh_projects()
            QtWidgets.QMessageBox.information(self, "موفق", "ویرایش ثبت شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", f"ویرایش ناموفق:\n{e}")
        finally:
            self.btn_edit_proj.setEnabled(True)

    def _del_project(self):
        row = self.list_projects.currentRow()
        if row < 0: return
        name = self.list_projects.currentItem().text()
        if QtWidgets.QMessageBox.question(self, "حذف", f"«{name}» حذف شود؟") != QtWidgets.QMessageBox.Yes:
            return
        self.btn_del_proj.setEnabled(False)
        try:
            if not self.pp_sheet:
                try:
                    self._init_sheets()
                except Exception:
                    pass
            pid = self._project_ids.get(name, "")
            if not pid: raise RuntimeError("ID یافت نشد.")
            if not self.pp_sheet.delete_name(pid):
                raise RuntimeError("حذف در شیت ناموفق بود.")
            self.projects.pop(row); self._project_ids.pop(name, None)
            self._refresh_projects()
            QtWidgets.QMessageBox.information(self, "حذف شد", "با موفقیت حذف شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", f"حذف ناموفق:\n{e}")
        finally:
            self.btn_del_proj.setEnabled(True)

    # ----------- دیالوگ هدف (وسط‌چین، بدون Cancel، دکمه "ثبت") -----------
    def _pick_target(self, init_person: str = "", init_project: str = "", init_minutes: int = 0):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("هدف")
        dlg.setLayoutDirection(QtCore.Qt.RightToLeft)
        dlg.setModal(True)

        # اندازهٔ مناسب
        dlg.resize(700, 360)
        dlg.setMinimumSize(620, 300)

        # ظرف مرکزی برای وسط‌چین
        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)
        lay.setAlignment(QtCore.Qt.AlignCenter)

        container = QtWidgets.QFrame()
        container.setObjectName("ResultBox")
        container.setMinimumWidth(560)
        form = QtWidgets.QVBoxLayout(container)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        form.setAlignment(QtCore.Qt.AlignCenter)

        # شخص
        lbl_p = QtWidgets.QLabel("شخص")
        lbl_p.setAlignment(QtCore.Qt.AlignCenter)
        cbp = NoWheelComboBox("نام شخص")
        cbp.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        cbp.setMinimumWidth(360)
        cbp.addItem("— انتخاب شخص —", None)
        for name in self.persons:
            cbp.addItem(name, name)
        if init_person:
            i = cbp.findText(init_person)
            cbp.setCurrentIndex(i if i >= 0 else 0)
        form.addWidget(lbl_p, 0, QtCore.Qt.AlignCenter)
        form.addWidget(cbp, 0, QtCore.Qt.AlignCenter)

        # پروژه
        lbl_j = QtWidgets.QLabel("پروژه")
        lbl_j.setAlignment(QtCore.Qt.AlignCenter)
        cbj = NoWheelComboBox("نام پروژه")
        cbj.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        cbj.setMinimumWidth(360)
        cbj.addItem("— انتخاب پروژه —", None)
        for name in self.projects:
            cbj.addItem(name, name)
        if init_project:
            j = cbj.findText(init_project)
            cbj.setCurrentIndex(j if j >= 0 else 0)
        form.addWidget(lbl_j, 0, QtCore.Qt.AlignCenter)
        form.addWidget(cbj, 0, QtCore.Qt.AlignCenter)

        # دقیقه
        lbl_m = QtWidgets.QLabel("دقیقه")
        lbl_m.setAlignment(QtCore.Qt.AlignCenter)
        sp = NoWheelSpinBox()
        sp.setRange(0, 100000)
        sp.setValue(int(init_minutes or 0))
        sp.setFixedWidth(160)
        form.addWidget(lbl_m, 0, QtCore.Qt.AlignCenter)
        form.addWidget(sp, 0, QtCore.Qt.AlignCenter)

        lay.addWidget(container, 0, QtCore.Qt.AlignCenter)

        # دکمه ثبت (بدون Cancel)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setAlignment(QtCore.Qt.AlignCenter)
        btn_ok = StyledButton("ثبت")
        btn_ok.setMinimumWidth(160)
        btn_ok.setDefault(True)  # Enter triggers
        btn_row.addWidget(btn_ok, 0, QtCore.Qt.AlignCenter)
        lay.addLayout(btn_row)

        def _accept():
            person = cbp.currentData()
            project = cbj.currentData()
            if person is None or project is None:
                QtWidgets.QMessageBox.warning(dlg, "ناقص", "لطفاً «شخص» و «پروژه» را انتخاب کن.")
                return
            dlg._result = (person, project, int(sp.value()))
            dlg.accept()

        btn_ok.clicked.connect(_accept)

        if dlg.exec() == QtWidgets.QDialog.Accepted:
            return dlg._result
        return None

    # ----------- کمک: بررسی یکتایی (person, project) -----------
    def _exists_pair(self, person: str, project: str, exclude_id: str = None) -> bool:
        for t in self.targets:
            if exclude_id and t.get("id") == exclude_id:
                continue
            if t.get("person") == person and t.get("project") == project:
                return True
        return False

    # ----------- CRUD: Targets -----------
    def _current_target_index(self) -> int:
        sel = self.tbl_targets.selectionModel().selectedRows()
        return sel[0].row() if sel else -1

    def _add_target(self):
        # اگر لیست‌ها خالی‌اند، تلاش کن شیت‌ها را مقداردهی کنی
        if not (self.persons and self.projects):
            try:
                self._init_sheets()
            except Exception:
                pass
        if not (self.persons and self.projects):
            QtWidgets.QMessageBox.warning(self, "هشدار", "اول شخص و پروژه تعریف کن.")
            return
        picked = self._pick_target()
        if not picked: return
        person, project, minutes = picked

        # یکتایی (person, project)
        if self._exists_pair(person, project):
            QtWidgets.QMessageBox.warning(self, "تکراری", "این ترکیب «شخص-پروژه» قبلاً ثبت شده است.")
            return

        self.btn_add_target.setEnabled(False)
        try:
            if not self.t_sheet:
                try:
                    self._init_sheets()
                except Exception:
                    pass
            if not self.t_sheet:
                QtWidgets.QMessageBox.critical(self, "خطا", "Sheet5 در دسترس نیست.")
                return
            new_id = self.t_sheet.add_target(person, project, minutes)
            self.targets.append({"id": new_id, "person": person, "project": project, "minutes": minutes})
            self._refresh_targets()
            QtWidgets.QMessageBox.information(self, "موفق", "ثبت شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", f"افزودن ناموفق:\n{e}")
        finally:
            self.btn_add_target.setEnabled(True)

    def _edit_target(self):
        r = self._current_target_index()
        if r < 0: return
        t = self.targets[r]
        picked = self._pick_target(t.get("person",""), t.get("project",""), t.get("minutes",0))
        if not picked: return
        person, project, minutes = picked

        # یکتایی (person, project) با صرفنظر از رکورد جاری
        if self._exists_pair(person, project, exclude_id=t["id"]):
            QtWidgets.QMessageBox.warning(self, "تکراری", "این ترکیب «شخص-پروژه» قبلاً ثبت شده است.")
            return

        self.btn_edit_target.setEnabled(False)
        try:
            if not self.t_sheet:
                try:
                    self._init_sheets()
                except Exception:
                    pass
            if not self.t_sheet:
                QtWidgets.QMessageBox.critical(self, "خطا", "Sheet5 در دسترس نیست.")
                return
            if not self.t_sheet.edit_target(t["id"], person, project, minutes):
                raise RuntimeError("ویرایش در شیت ناموفق بود.")
            # apply
            t.update({"person": person, "project": project, "minutes": minutes})
            self._refresh_targets()
            QtWidgets.QMessageBox.information(self, "موفق", "ویرایش ثبت شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", f"ویرایش ناموفق:\n{e}")
        finally:
            self.btn_edit_target.setEnabled(True)

    def _del_target(self):
        r = self._current_target_index()
        if r < 0: return
        t = self.targets[r]
        if QtWidgets.QMessageBox.question(self, "حذف", f"هدف «{t.get('person','')} - {t.get('project','')}» حذف شود؟") != QtWidgets.QMessageBox.Yes:
            return
        self.btn_del_target.setEnabled(False)
        try:
            if not self.t_sheet:
                try:
                    self._init_sheets()
                except Exception:
                    pass
            if not self.t_sheet:
                QtWidgets.QMessageBox.critical(self, "خطا", "Sheet5 در دسترس نیست.")
                return
            if not self.t_sheet.delete_target(t["id"]):
                raise RuntimeError("حذف در شیت ناموفق بود.")
            self.targets.pop(r)
            self._refresh_targets()
            QtWidgets.QMessageBox.information(self, "حذف شد", "با موفقیت حذف شد.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "خطا", f"حذف ناموفق:\n{e}")
        finally:
            self.btn_del_target.setEnabled(True)

# ----------- گزارش -----------
    def _open_report(self):
        # رفتن به صفحه داشبورد
        if hasattr(self, "stack") and hasattr(self, "dashboard_page"):
            self.stack.setCurrentWidget(self.dashboard_page)

    def _back_to_form(self):
        # برگشت به فرم اصلی
        if hasattr(self, "stack") and hasattr(self, "main_page"):
            self.stack.setCurrentWidget(self.main_page)
    def _init_dashboard_filters(self):
        """مقداردهی دراپ‌داون‌های داشبورد از جدول DailyReport"""

        session = get_session()

        # ۱) نام گزارش‌دهنده‌ها (reporter)
        self.cmb_filter_person.clear()
        self.cmb_filter_person.addItem("همه")

        reporters = (
            session.query(DailyReport.reporter)
            .filter(DailyReport.reporter.isnot(None))
            .filter(DailyReport.reporter != "")
            .distinct()
            .all()
        )
        for (name,) in reporters:
            self.cmb_filter_person.addItem(name)

        # ۲) ماه‌ها بر اساس date_shamsi = "YYYY/MM/DD"
        self.cmb_filter_month.clear()
        self.cmb_filter_month.addItem("همه")

        dates = (
            session.query(DailyReport.date_shamsi)
            .filter(DailyReport.date_shamsi.isnot(None))
            .filter(DailyReport.date_shamsi != "")
            .distinct()
            .all()
        )
        months = set()
        for (ds,) in dates:
            ds = (ds or "").strip()
            if len(ds) >= 7:   # "YYYY/MM"
                months.add(ds[:7])

        for m in sorted(months, reverse=True):
            self.cmb_filter_month.addItem(m)

        # ۳) روز ماه (۱ تا ۳۱)
        self.cmb_filter_day.clear()
        self.cmb_filter_day.addItem("همه")
        for d in range(1, 32):
            self.cmb_filter_day.addItem(str(d))

        # ۴) روز هفته (طبق daily_report_logic.weekday_from_jalali)
        self.cmb_filter_weekday.clear()
        self.cmb_filter_weekday.addItem("همه")
        weekdays = ["دوشنبه","سه‌شنبه","چهارشنبه","پنج‌شنبه","جمعه","شنبه","یکشنبه"]
        for wd in weekdays:
            self.cmb_filter_weekday.addItem(wd)

        # ۵) نام پروژه‌ها
        self.cmb_filter_project.clear()
        self.cmb_filter_project.addItem("همه")

        projects = (
            session.query(DailyReport.project)
            .filter(DailyReport.project.isnot(None))
            .filter(DailyReport.project != "")
            .distinct()
            .all()
        )
        for (pname,) in projects:
            self.cmb_filter_project.addItem(pname)

        # اولین بار، مقدار کارت را هم حساب کن
        self._apply_dashboard_filters()
    def _apply_dashboard_filters(self):
        """هر تغییری در فیلترها → محاسبه‌ی دوباره‌ی تعداد کارهای انجام‌نشده"""

        def _norm_combo(combo: StyledComboBox):
            txt = combo.currentText().strip()
            if not txt or txt == "همه":
                return None
            return txt

        person  = _norm_combo(self.cmb_filter_person)
        month   = _norm_combo(self.cmb_filter_month)   # "1404/05"
        day     = _norm_combo(self.cmb_filter_day)     # "1".."31"
        weekday = _norm_combo(self.cmb_filter_weekday)
        project = _norm_combo(self.cmb_filter_project)

        count = self._count_unfinished_tasks(
            person=person,
            month=month,
            day=day,
            weekday=weekday,
            project=project,
        )
        self.lbl_unfinished_count.setText(str(count))
    def _count_unfinished_tasks(
        self,
        person: str | None = None,
        month: str | None = None,
        day: str | None = None,
        weekday: str | None = None,
        project: str | None = None,
    ) -> int:
        """
        ترکیب فیلترها:
        - بدون هیچ فیلتر: کل کارهای انجام‌نشده
        - person: فقط آن گزارش‌دهنده
        - month: فقط آن ماه (مثلاً 1404/05)
        - day: فقط آن روز ماه (۱..۳۱)
        - weekday: مثلا "سه‌شنبه"
        - project: فقط آن پروژه
        همگی با AND روی هم اعمال می‌شوند.
        """
        session = get_session()

        # فقط کارهای انجام‌نشده
        q = session.query(DailyReport).filter(
            or_(
                DailyReport.status.contains('❌'),
                DailyReport.status.ilike('%انجام نشده%'),
            )
        )

        if person:
            q = q.filter(DailyReport.reporter == person)

        if project:
            q = q.filter(DailyReport.project == project)

        if month:
            # date_shamsi مثل "1404/05/12" → فیلتر روی "1404/05/%"
            q = q.filter(DailyReport.date_shamsi.like(f"{month}/%"))

        if day:
            try:
                d_int = int(day)
                day_str = f"{d_int:02d}"   # "5" → "05"
                q = q.filter(DailyReport.date_shamsi.like(f"%/{day_str}"))
            except ValueError:
                pass

        if weekday:
            q = q.filter(DailyReport.weekday == weekday)

        return q.count()