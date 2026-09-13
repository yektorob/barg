import sys, os, re
from PySide6 import QtWidgets, QtCore, QtGui

from ui.widgets import StyledLineEdit, StyledComboBox, StyledButton, inch
from daily_report_logic import (
    load_local_data, weekday_from_jalali, fetch_unfinished,
    mark_task_done, submit_daily_report, valid_status
,
    fetch_activity_dates
)
from daily_report_logic import fetch_rows_for_reporter_date, update_daily_report_row


def _fmt_jalali_ymd(s):
    import datetime
    try:
        import jdatetime
    except Exception:
        return str(s or "")

    text = str(s or "").strip()
    if not text:
        return ""

    text = text.replace("\u200c", "").replace("\u200f", "").replace("\u202a", "").replace("\u202c", "")
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))
    low = text.lower()

    fa_months = {
        "فروردین":1, "اردیبهشت":2, "خرداد":3, "تیر":4,
        "مرداد":5, "شهریور":6, "مهر":7, "آبان":8, "آذر":9,
        "دی":10, "بهمن":11, "اسفند":12
    }

    en_months_greg = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    en_months_jalali = {"apr":1,"may":2,"jun":3,"jul":4,"aug":5,"sep":6,"oct":7,"nov":8,"dec":9,"jan":10,"feb":11,"mar":12}

    def find_en_mon(src, table):
        for k in table:
            if k in src:
                return table[k]
        return None

    month_by_fa_name = None
    for name, num in fa_months.items():
        if name in text:
            month_by_fa_name = num
            break

    nums = [int(x) for x in re.findall(r"\d+", text)]

    def _fmt_y_m_d(y, m, d):
        if 1300 <= y <= 1599 and 1 <= m <= 12 and 1 <= d <= 31:
            return f"{y:04d}/{m:02d}/{d:02d}"
        return ""

    jalali_year = next((n for n in nums if 1300 <= n <= 1599), None)
    if jalali_year is not None:
        if month_by_fa_name is not None:
            m = month_by_fa_name
        else:
            m = find_en_mon(low, en_months_jalali)
            if m is None:
                m = next((n for n in nums if n != jalali_year and 1 <= n <= 12), 0)
        d = next((n for n in nums if n not in (jalali_year, m) and 1 <= n <= 31), 0)
        out = _fmt_y_m_d(jalali_year, m, d)
        if out:
            return out
        if len(nums) >= 3:
            if 1300 <= nums[1] <= 1599 and 1 <= nums[2] <= 12 and 1 <= nums[0] <= 31:
                out = _fmt_y_m_d(nums[1], nums[2], nums[0])
                if out:
                    return out
            if 1300 <= nums[0] <= 1599 and 1 <= nums[2] <= 12 and 1 <= nums[1] <= 31:
                out = _fmt_y_m_d(nums[0], nums[2], nums[1])
                if out:
                    return out
        return text

    greg_year = next((n for n in nums if 1900 <= n <= 2100), None)
    if greg_year is not None:
        m = find_en_mon(low, en_months_greg)
        if m is None:
            m = next((n for n in nums if n != greg_year and 1 <= n <= 12), 1) or 1
        d = next((n for n in nums if n not in (greg_year, m) and 1 <= n <= 31), 1) or 1
        try:
            gdate = datetime.date(greg_year, m, d)
            jdate = jdatetime.date.fromgregorian(date=gdate)
            return jdate.strftime("%Y/%m/%d")
        except Exception:
            pass

    try:
        head10 = text[:10].replace("/", "-")
        dt = datetime.date.fromisoformat(head10)
        jdate = jdatetime.date.fromgregorian(date=dt)
        return jdate.strftime("%Y/%m/%d")
    except Exception:
        return text


class DailyReportPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DailyReportPage")
        self.setLayoutDirection(QtCore.Qt.RightToLeft)

        qss = os.path.join(os.path.dirname(__file__), "styles", "abbaspoor.qss")
        if os.path.exists(qss):
            with open(qss, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        self.setStyleSheet(self.styleSheet() + """
        QAbstractSpinBox { padding-right: 36px; padding-left: 12px; min-height: 40px; }
        QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
            subcontrol-origin: border; width: 30px; height: 20px;
            border-left: 1px solid #505050; background: #2F3238;
        }
        QAbstractSpinBox::up-button { subcontrol-position: top right; }
        QAbstractSpinBox::down-button { subcontrol-position: bottom right; }
        QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover { background: #3A3E47; }
        QListWidget#SentDatesList { font-size: 16px; }
        """)



        self.persons, self.projects = load_local_data()

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        h_center = QtWidgets.QHBoxLayout()
        h_center.addStretch(1)

        frame = QtWidgets.QFrame()
        frame.setObjectName("AbbaspoorFrame")
        frame.setMinimumWidth(inch(11))
        h_center.addWidget(frame)
        h_center.addStretch(1)

        outer.addLayout(h_center)
        outer.addStretch(1)

        v = QtWidgets.QVBoxLayout(frame)
        v.setContentsMargins(30, 30, 30, 30)
        v.setSpacing(18)


        user_box = QtWidgets.QHBoxLayout(); user_box.setSpacing(12)

        self.date_edit = StyledLineEdit("تاریخ (YYYY/MM/DD)")
        self.date_edit.setText(self._today_jalali())
        self.date_edit.setValidator(QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"^\d{4}/\d{2}/\d{2}$"), self
        ))
        self.date_edit.textChanged.connect(self._update_weekday)

        self.weekday_lbl = QtWidgets.QLabel("")
        self.weekday_lbl.setStyleSheet("color:#f5f5f5; padding:6px 10px;")

        user_box.addWidget(QtWidgets.QLabel("تاریخ گزارش:"))
        user_box.addWidget(self.date_edit, 1)
        user_box.addSpacing(10)
        user_box.addWidget(self.weekday_lbl)

        user_box.addSpacing(25)
        user_box.addWidget(QtWidgets.QLabel("نام گزارش‌دهنده:"))

        self.reporter_cb = self._make_combo(self.persons, "انتخاب نام", editable=True)
        self.reporter_cb.setMinimumWidth(200)
        self._tune_combo(self.reporter_cb)
        self.reporter_cb.currentTextChanged.connect(self._on_reporter_change)
        user_box.addWidget(self.reporter_cb, 1)

        v.addLayout(user_box)
        self._update_weekday()


        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        inner = QtWidgets.QWidget()
        self.tasks_layout = QtWidgets.QVBoxLayout(inner)
        self.tasks_layout.setSpacing(10)
        self.tasks_layout.addStretch(1)
        self.scroll.setWidget(inner)
        v.addWidget(self.scroll, 1)


        btn_row = QtWidgets.QHBoxLayout(); btn_row.setSpacing(10)
        self.btn_add = StyledButton("➕ افزودن فعالیت")
        self.btn_remove = StyledButton("❌ حذف فعالیت")
        self.btn_unfin = StyledButton("مشاهده اقدامات انجام نشده")
        self.btn_sent = StyledButton("📅 تاریخ‌های ارسال‌شده")
        self.btn_submit = StyledButton("📤 ارسال گزارش")
        self.btn_edit_activities = StyledButton("✏️ ویرایش فعالیت‌ها")

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_unfin)
        btn_row.addWidget(self.btn_sent)
        btn_row.addWidget(self.btn_edit_activities)
        btn_row.addWidget(self.btn_submit)
        v.addLayout(btn_row)

        self.btn_add.clicked.connect(self.add_task)
        self.btn_remove.clicked.connect(self.remove_task)
        self.btn_unfin.clicked.connect(self.view_unfinished)
        self.btn_sent.clicked.connect(self.view_sent_dates)
        self.btn_submit.clicked.connect(self.submit)
        self.btn_edit_activities.clicked.connect(self.edit_activities)

        self.task_widgets = []
        self.add_task()
        self._disable_task_area()


    def _today_jalali(self):
        import jdatetime
        return jdatetime.date.today().strftime("%Y/%m/%d")


    def _remove_duplicate_items(self, cb: QtWidgets.QComboBox):
        seen = set()
        i = 0
        while i < cb.count():
            t = cb.itemText(i).strip()
            if t in seen:
                cb.removeItem(i)
            else:
                seen.add(t); i += 1

    def _make_combo(self, items, placeholder="", editable=False):
        cb = StyledComboBox(placeholder)


        cb.installEventFilter(self)

        uniq, seen = [], set()
        for it in (items or []):
            t = str(it).strip()
            if not t:
                continue
            if placeholder and t == placeholder:
                continue
            if t not in seen:
                uniq.append(t); seen.add(t)

        cb.addItems(uniq)
        cb.setEditable(editable)
        cb.setInsertPolicy(QtWidgets.QComboBox.NoInsert)


        cb.setCurrentIndex(-1)
        if editable and cb.lineEdit():
            cb.lineEdit().setPlaceholderText(placeholder)


        if cb.isEditable():
            comp = QtWidgets.QCompleter(uniq, cb)
            comp.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            try:
                comp.setFilterMode(QtCore.Qt.MatchContains)
            except Exception:
                pass
            cb.setCompleter(comp)


        self._remove_duplicate_items(cb)
        return cb

    def _tune_combo(self, cb: StyledComboBox):
        cb.setStyleSheet(cb.styleSheet() + """
        QComboBox::drop-down {
            width: 30px;
            border-left-width: 1px;
            border-left-color: #555;
            border-left-style: solid;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        }
        QComboBox:editable {
            min-width: 120px;
            padding-right: 30px;
        }
        QComboBox QAbstractItemView {
            min-width: 200px;
        }
        """)

        if cb.isEditable():
            cb.setStyleSheet(cb.styleSheet() + """
            QComboBox QLineEdit,
            QComboBox QLineEdit:hover {
                background: #2c2e33 !important;
                padding-right: 8px;
            }
            QComboBox:editable, QComboBox:editable:hover {
                background: #2c2e33 !important;
            }
            """)

            if cb.lineEdit() is not None:
                le = cb.lineEdit()
                pal = le.palette()
                txt = cb.palette().color(QtGui.QPalette.Text)
                pal.setColor(QtGui.QPalette.PlaceholderText, txt)
                le.setPalette(pal)
    def eventFilter(self, obj, ev):
        from PySide6 import QtCore, QtWidgets
        if isinstance(obj, QtWidgets.QComboBox) and ev.type() == QtCore.QEvent.Wheel:
            view = obj.view() if hasattr(obj, "view") else None
            if not (view and view.isVisible()):
                return True
        return super().eventFilter(obj, ev)


    def _update_weekday(self):
        self.weekday_lbl.setText(f"روز هفته: {weekday_from_jalali(self.date_edit.text())}")

    def _on_reporter_change(self, text):
        if text and text in self.persons:
            self._enable_task_area()
        else:
            self._disable_task_area()


    def _set_task_enabled(self, tw, enabled: bool):

        for w in tw.get('all_widgets', []):
            w.setEnabled(enabled)
        for lb in tw.get('labels', []):
            lb.setEnabled(enabled)


        if enabled:
            on = tw['other_chk'].isChecked()
            tw['other_cb'].setEnabled(on)
            for lb in tw.get('labels', []):
                if getattr(lb, '_is_other_label', False):
                    lb.setEnabled(on)
            if not on and tw['other_cb'].isEditable() and tw['other_cb'].lineEdit():

                tw['other_cb'].setCurrentIndex(-1)
                tw['other_cb'].lineEdit().clear()
        else:
            tw['other_cb'].setEnabled(False)
            for lb in tw.get('labels', []):
                if getattr(lb, '_is_other_label', False):
                    lb.setEnabled(False)

    def _disable_task_area(self):
        for b in (self.btn_add, self.btn_remove, self.btn_submit, self.btn_unfin, self.btn_sent, self.btn_edit_activities):
            b.setEnabled(False)
        for tw in self.task_widgets:
            self._set_task_enabled(tw, False)

    def _enable_task_area(self):
        for b in (self.btn_add, self.btn_remove, self.btn_submit, self.btn_unfin, self.btn_sent, self.btn_edit_activities):
            b.setEnabled(True)
        for tw in self.task_widgets:
            self._set_task_enabled(tw, True)





    def view_sent_dates(self):
        reporter = self.reporter_cb.currentText().strip()
        if reporter not in self.persons:
            QtWidgets.QMessageBox.warning(self, "خطا", "نام گزارش‌دهنده را از لیست انتخاب کنید.")
            return

        import jdatetime
        j_today = jdatetime.date.today()
        state = {"year": j_today.year, "month": j_today.month}

        JMONTHS = ['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور',
                   'مهر','آبان','آذر','دی','بهمن','اسفند']

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("تاریخ‌های ارسال‌شده")
        dlg.setLayoutDirection(QtCore.Qt.RightToLeft)
        v = QtWidgets.QVBoxLayout(dlg); v.setContentsMargins(12,12,12,12); v.setSpacing(10)


        hdr = QtWidgets.QHBoxLayout()
        btn_prev = StyledButton("◀ ماه قبل")
        lbl_title = QtWidgets.QLabel("")
        lbl_title.setStyleSheet("color:#f5f5f5; font-weight:600; font-size:17px; padding:6px 8px;")
        hdr.addWidget(btn_prev)
        hdr.addStretch(1)
        hdr.addWidget(lbl_title)
        v.addLayout(hdr)


        lst = QtWidgets.QListWidget()
        lst.setObjectName("SentDatesList")
        lst.setAlternatingRowColors(True)
        v.addWidget(lst, 1)

        def refresh():
            y, m = state["year"], state["month"]
            lbl_title.setText(f"{JMONTHS[m-1]} {y}")
            lst.clear()
            data = fetch_activity_dates(reporter, y, m)
            dates = data.get("dates", [])
            if not dates:
                lst.addItem("هیچ فعالیتی در این ماه ثبت نشده.")
                return
            for d in dates:
                it = QtWidgets.QListWidgetItem(f"🗓️  {d}")
                it.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                lst.addItem(it)

        def prev_month():
            if state["month"] == 1:
                state["month"] = 12
                state["year"] -= 1
            else:
                state["month"] -= 1
            refresh()

        btn_prev.clicked.connect(prev_month)
        refresh()
        dlg.resize(480, 520)
        dlg.exec()

    def add_task(self):
        idx = len(self.task_widgets) + 1

        box = QtWidgets.QGroupBox(f"فعالیت {idx}")
        lay = QtWidgets.QGridLayout(box)
        lay.setHorizontalSpacing(12)
        lay.setVerticalSpacing(10)
        lay.setContentsMargins(12, 26, 12, 12)
        lay.setHorizontalSpacing(8)


        lbl_proj = QtWidgets.QLabel("نام پروژه:");  lay.addWidget(lbl_proj, 0, 0)
        proj_cb  = self._make_combo(self.projects, "انتخاب پروژه", editable=True)
        proj_cb.setMinimumWidth(200)
        self._tune_combo(proj_cb)
        lay.addWidget(proj_cb, 0, 1, 1, 3)


        lbl_task = QtWidgets.QLabel("عنوان فعالیت:"); lay.addWidget(lbl_task, 1, 0)
        task_le  = StyledLineEdit("...");             lay.addWidget(task_le, 1, 1, 1, 3)


        lbl_status = QtWidgets.QLabel("وضعیت:");      lay.addWidget(lbl_status, 2, 0)
        status_cb  = self._make_combo(["✅ انجام شده","❌ انجام نشده"], "انتخاب وضعیت", editable=False)
        self._tune_combo(status_cb)
        lay.addWidget(status_cb, 2, 1)

        lbl_dur = QtWidgets.QLabel("مدت زمان (دقیقه):"); lay.addWidget(lbl_dur, 2, 2)
        dur_sb = QtWidgets.QSpinBox()
        dur_sb.setRange(0, 10000)
        dur_sb.setAlignment(QtCore.Qt.AlignCenter)
        dur_sb.setButtonSymbols(QtWidgets.QAbstractSpinBox.UpDownArrows)
        lay.addWidget(dur_sb, 2, 3)


        lbl_note = QtWidgets.QLabel("توضیحات (اختیاری):"); lay.addWidget(lbl_note, 3, 0)
        note_le  = StyledLineEdit("");                       lay.addWidget(note_le, 3, 1, 1, 3)


        other_chk = QtWidgets.QCheckBox("آیا این فعالیت شخص دیگری‌ست؟")
        lay.addWidget(other_chk, 4, 0, 1, 4)

        lbl_other = QtWidgets.QLabel("نام شخص:"); lbl_other._is_other_label = True
        lay.addWidget(lbl_other, 5, 0)
        other_cb  = self._make_combo(self.persons, "انتخاب نام", editable=True)
        other_cb.setMinimumWidth(200)
        self._tune_combo(other_cb)
        other_cb.setEnabled(False); lbl_other.setEnabled(False)
        other_cb.setCurrentIndex(-1)
        lay.addWidget(other_cb, 5, 1, 1, 3)

        def toggle_other():
            on = other_chk.isChecked()
            other_cb.setEnabled(on)
            lbl_other.setEnabled(on)
            if not on:
                other_cb.setCurrentIndex(-1)
                if other_cb.isEditable() and other_cb.lineEdit():
                    other_cb.lineEdit().clear()
        other_chk.toggled.connect(toggle_other)

        widgets = {
            'group': box,
            'proj_cb': proj_cb, 'task_le': task_le, 'status_cb': status_cb,
            'dur_sb': dur_sb,   'note_le': note_le,
            'other_chk': other_chk, 'other_cb': other_cb,
            'labels': [lbl_proj, lbl_task, lbl_status, lbl_dur, lbl_note, lbl_other],
            'all_widgets': [proj_cb, task_le, status_cb, dur_sb, note_le, other_chk, other_cb],
        }
        self.task_widgets.append(widgets)
        self.tasks_layout.insertWidget(self.tasks_layout.count()-1, box)


        if self.reporter_cb.currentText() not in self.persons:
            self._set_task_enabled(widgets, False)

    def remove_task(self):
        if not self.task_widgets:
            QtWidgets.QMessageBox.warning(self, "خطا", "هیچ فعالیتی برای حذف وجود ندارد.")
            return
        w = self.task_widgets.pop()
        w['group'].deleteLater()

    def view_unfinished(self):
        reporter = self.reporter_cb.currentText().strip()
        if reporter not in self.persons:
            QtWidgets.QMessageBox.warning(self, "خطا", "نام گزارش‌دهنده را از لیست انتخاب کنید.")
            return

        data = fetch_unfinished(reporter)
        tasks = data.get('tasks', [])
        if not tasks:
            QtWidgets.QMessageBox.information(self, "پیغام", "هیچ فعالیت انجام نشده‌ای وجود ندارد.")
            return

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("اقدامات انجام نشده")
        dlg.setLayoutDirection(QtCore.Qt.RightToLeft)
        v = QtWidgets.QVBoxLayout(dlg); v.setContentsMargins(12,12,12,12)

        table = QtWidgets.QTableWidget()
        table.setLayoutDirection(QtCore.Qt.RightToLeft)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        table.setWordWrap(True)
        table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        table.verticalHeader().setVisible(False)

        headers = ["گزارش‌دهنده","تاریخ شمسی","روز","پروژه","فعالیت","وضعیت","مدت","توضیحات","عملیات"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)

        widths = [120, 180, 0, 180, 260, 110, 90, 260, 110]
        table.setRowCount(len(tasks))

        for r, t in enumerate(tasks):
            date_raw = t.get('date_shamsi') or t.get('date_c') or t.get('date', '')
            date_jal = _fmt_jalali_ymd(date_raw)
            weekday_fa = weekday_from_jalali(date_jal) or ""
            date_display = (date_jal + (" " + weekday_fa if weekday_fa else "")).strip()

            vals = [
                t.get('reporter',''),
                date_display,
                "",
                t.get('project',''),
                t.get('task',''),
                t.get('status',''),
                str(t.get('duration','')),
                t.get('note','')
            ]
            for c, val in enumerate(vals):
                if c in (4, 7):
                    lbl = QtWidgets.QLabel(val)
                    lbl.setWordWrap(True)
                    lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                    lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
                    table.setCellWidget(r, c, lbl)
                else:
                    it = QtWidgets.QTableWidgetItem(val)
                    it.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                    table.setItem(r, c, it)

            btn = StyledButton("انجام شد")
            btn.setProperty("task", t)
            btn.clicked.connect(lambda _, b=btn, tbl=table: self._on_mark_done_clicked(b, tbl))
            table.setCellWidget(r, 8, btn)

        for i, w in enumerate(widths):
            table.setColumnWidth(i, w)
        table.setColumnHidden(2, True)
        table.resizeRowsToContents()
        v.addWidget(table)

        total_w = sum(widths) + table.verticalHeader().width() + 32
        screen_w = QtWidgets.QApplication.primaryScreen().availableGeometry().width()
        dlg.resize(min(total_w, int(screen_w*0.95)), 560)

        close_btn = StyledButton("بستن")
        close_btn.clicked.connect(dlg.accept)
        v.addWidget(close_btn, 0, QtCore.Qt.AlignLeft)

        dlg.exec()

    def _on_mark_done_clicked(self, button: QtWidgets.QPushButton, table: QtWidgets.QTableWidget):
        t = button.property("task") or {}
        ok, msg = mark_task_done(
            timestamp=t.get("timestamp",""),
            reporter=t.get("reporter",""),
            row=t.get("row"),
            status_col=t.get("status_col"),
        )
        if ok:
            row_to_remove = -1
            for r in range(table.rowCount()):
                if table.cellWidget(r, 8) is button:
                    row_to_remove = r
                    break
            if row_to_remove >= 0:
                table.removeRow(row_to_remove)
            QtWidgets.QMessageBox.information(self, "موفق", msg)
        else:
            QtWidgets.QMessageBox.critical(self, "خطا", msg)


    def edit_activities(self):
        reporter = self.reporter_cb.currentText().strip()
        if reporter not in self.persons:
            QtWidgets.QMessageBox.warning(self, "خطا", "نام گزارش‌دهنده را از لیست انتخاب کنید.")
            return

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("جستجو و ویرایش فعالیت‌ها")
        dlg.setLayoutDirection(QtCore.Qt.RightToLeft)
        v = QtWidgets.QVBoxLayout(dlg); v.setContentsMargins(12,12,12,12); v.setSpacing(8)

        h = QtWidgets.QHBoxLayout()
        date_le = StyledLineEdit("YYYY/MM/DD")
        date_le.setText(self.date_edit.text())
        date_le.setValidator(QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"^\d{4}/\d{2}/\d{2}$"), self
        ))
        btn_search = StyledButton("🔎 جستجو")
        h.addWidget(QtWidgets.QLabel("تاریخ:"))
        h.addWidget(date_le, 1)
        h.addWidget(btn_search)
        v.addLayout(h)

        table = QtWidgets.QTableWidget()
        table.setLayoutDirection(QtCore.Qt.RightToLeft)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        table.setWordWrap(True)
        table.verticalHeader().setVisible(False)
        headers = ["تاریخ","پروژه","فعالیت","وضعیت","مدت","توضیحات","انجام‌دهنده","عملیات"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        v.addWidget(table, 1)

        def do_search():
            d = date_le.text().strip()
            if not d:
                QtWidgets.QMessageBox.warning(dlg, "خطا", "تاریخ را وارد کنید.")
                return
            rows = fetch_rows_for_reporter_date(reporter, d)
            table.setRowCount(0)
            if not rows:
                QtWidgets.QMessageBox.information(dlg, "پیغام", "اطلاعاتی یافت نشد.")
                return
            table.setRowCount(len(rows))
            for r, item in enumerate(rows):
                vals = [item.get('date_shamsi',''), item.get('project',''), item.get('task',''), item.get('status',''), str(item.get('duration','') or ''), item.get('note',''), item.get('performed_by','')]
                for c, val in enumerate(vals):
                    if c in (2,5):
                        lbl = QtWidgets.QLabel(val)
                        lbl.setWordWrap(True)
                        lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                        lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
                        table.setCellWidget(r, c, lbl)
                    else:
                        it = QtWidgets.QTableWidgetItem(val)
                        it.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                        table.setItem(r, c, it)

                btn = StyledButton("ویرایش")
                btn.setProperty("row_id", item.get('id'))
                btn.clicked.connect(lambda _, iid=item.get('id'), it=item: self._open_edit_row_dialog(iid, it, table))
                table.setCellWidget(r, 7, btn)
            table.resizeRowsToContents()

        btn_search.clicked.connect(do_search)
        # initial search
        do_search()

        close_btn = StyledButton("بستن")
        close_btn.clicked.connect(dlg.accept)
        v.addWidget(close_btn, 0, QtCore.Qt.AlignLeft)
        dlg.resize(880, 520)
        dlg.exec()


    def _open_edit_row_dialog(self, row_id, item: dict, table: QtWidgets.QTableWidget):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("ویرایش فعالیت")
        dlg.setLayoutDirection(QtCore.Qt.RightToLeft)
        v = QtWidgets.QVBoxLayout(dlg); v.setContentsMargins(12,12,12,12); v.setSpacing(8)

        form = QtWidgets.QGridLayout(); form.setHorizontalSpacing(12); form.setVerticalSpacing(8)
        form.setContentsMargins(0,0,0,0)

        lbl_date = QtWidgets.QLabel("تاریخ (YYYY/MM/DD):"); form.addWidget(lbl_date, 0, 0)
        date_le = StyledLineEdit("YYYY/MM/DD"); date_le.setText(item.get('date_shamsi',''))
        date_le.setValidator(QtGui.QRegularExpressionValidator(QtCore.QRegularExpression(r"^\d{4}/\d{2}/\d{2}$"), self))
        form.addWidget(date_le, 0, 1)

        lbl_proj = QtWidgets.QLabel("پروژه:"); form.addWidget(lbl_proj, 1, 0)
        proj_cb = self._make_combo(self.projects, "انتخاب پروژه", editable=True)
        proj_cb.setCurrentText(item.get('project',''))
        self._tune_combo(proj_cb)
        form.addWidget(proj_cb, 1, 1)

        lbl_task = QtWidgets.QLabel("فعالیت:"); form.addWidget(lbl_task, 2, 0)
        task_le = StyledLineEdit(item.get('task','')); form.addWidget(task_le, 2, 1)

        lbl_status = QtWidgets.QLabel("وضعیت:"); form.addWidget(lbl_status, 3, 0)
        status_cb = self._make_combo(["✅ انجام شده","❌ انجام نشده"], "انتخاب وضعیت", editable=False)
        status_cb.setCurrentText(item.get('status',''))
        self._tune_combo(status_cb)
        form.addWidget(status_cb, 3, 1)

        lbl_dur = QtWidgets.QLabel("مدت (دقیقه):"); form.addWidget(lbl_dur, 4, 0)
        dur_sb = QtWidgets.QSpinBox(); dur_sb.setRange(0, 10000); dur_sb.setValue(int(item.get('duration') or 0)); form.addWidget(dur_sb, 4, 1)

        lbl_note = QtWidgets.QLabel("توضیحات:"); form.addWidget(lbl_note, 5, 0)
        note_le = StyledLineEdit(item.get('note','')); form.addWidget(note_le, 5, 1)

        lbl_perf = QtWidgets.QLabel("انجام‌دهنده:"); form.addWidget(lbl_perf, 6, 0)

        other_chk = QtWidgets.QCheckBox("آیا این فعالیت شخص دیگری‌ست؟")
        # determine initial state: checked if performed_by exists and is different from reporter
        reporter_name = self.reporter_cb.currentText().strip()
        perf_val = item.get('performed_by','') or ''
        is_other = bool(perf_val and perf_val != reporter_name)
        other_chk.setChecked(is_other)
        form.addWidget(other_chk, 6, 1)

        perf_cb = self._make_combo(self.persons, "انتخاب نام", editable=True)
        self._tune_combo(perf_cb)
        form.addWidget(perf_cb, 7, 1)
        # Prefill performed_by: use stored value if present, otherwise default to reporter
        if perf_val:
            perf_cb.setCurrentText(perf_val)
        else:
            perf_cb.setCurrentText(reporter_name)

        # Enable/disable combo visually but keep selection when toggled off
        perf_cb.setEnabled(is_other)

        def toggle_perf():
            on = other_chk.isChecked()
            perf_cb.setEnabled(on)

        other_chk.toggled.connect(toggle_perf)

        v.addLayout(form)

        h = QtWidgets.QHBoxLayout()
        save_btn = StyledButton("ذخیره")
        cancel_btn = StyledButton("انصراف")
        h.addWidget(cancel_btn, 0, QtCore.Qt.AlignLeft)
        h.addStretch(1)
        h.addWidget(save_btn)
        v.addLayout(h)

        def do_save():
            d = date_le.text().strip()
            if not d:
                QtWidgets.QMessageBox.warning(dlg, "خطا", "تاریخ صحیح وارد کنید.")
                return
            proj = proj_cb.currentText().strip()
            if proj not in self.projects:
                QtWidgets.QMessageBox.warning(dlg, "خطا", "نام پروژه را از لیست انتخاب کنید.")
                return
            status = status_cb.currentText().strip()
            if not valid_status(status):
                QtWidgets.QMessageBox.warning(dlg, "خطا", "وضعیت را انتخاب کنید.")
                return
            perf = perf_cb.currentText().strip()
            if perf not in self.persons:
                QtWidgets.QMessageBox.warning(dlg, "خطا", "نام انجام‌دهنده را از لیست انتخاب کنید.")
                return
            fields = {
                'date_shamsi': d,
                'project': proj,
                'task': task_le.text().strip(),
                'status': status,
                'duration': int(dur_sb.value()),
                'note': note_le.text().strip(),
                'performed_by': perf,
            }
            ok = update_daily_report_row(row_id, **fields)
            if ok:
                QtWidgets.QMessageBox.information(dlg, "موفق", "ذخیره شد.")
                # update table widget if present
                for r in range(table.rowCount()):
                    wid = table.cellWidget(r, 7)
                    if wid and wid.property("row_id") == row_id:
                        table.setItem(r, 0, QtWidgets.QTableWidgetItem(fields['date_shamsi']))
                        table.setItem(r, 1, QtWidgets.QTableWidgetItem(fields['project']))
                        lbl = QtWidgets.QLabel(fields['task'])
                        lbl.setWordWrap(True); lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                        table.setCellWidget(r, 2, lbl)
                        table.setItem(r, 3, QtWidgets.QTableWidgetItem(fields['status']))
                        table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(fields['duration'])))
                        lbl2 = QtWidgets.QLabel(fields['note'])
                        lbl2.setWordWrap(True); lbl2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                        table.setCellWidget(r, 5, lbl2)
                        table.setItem(r, 6, QtWidgets.QTableWidgetItem(fields['performed_by']))
                        break
                dlg.accept()
            else:
                QtWidgets.QMessageBox.critical(dlg, "خطا", "ذخیره انجام نشد.")

        save_btn.clicked.connect(do_save)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()


    def _reset_form(self):

        self.date_edit.setText(self._today_jalali())
        self._update_weekday()


        self.reporter_cb.setCurrentIndex(-1)
        if self.reporter_cb.isEditable() and self.reporter_cb.lineEdit():
            self.reporter_cb.lineEdit().clear()


        for tw in self.task_widgets:
            try:
                tw['group'].deleteLater()
            except Exception:
                pass
        self.task_widgets.clear()


        self.add_task()
        self._disable_task_area()

    def submit(self):
        reporter = self.reporter_cb.currentText().strip()
        if reporter not in self.persons:
            QtWidgets.QMessageBox.critical(self, "خطا", "نام گزارش‌دهنده را از لیست انتخاب کنید.")
            return

        date_str = self.date_edit.text().strip()
        weekday = weekday_from_jalali(date_str)
        if not weekday:
            QtWidgets.QMessageBox.critical(self, "خطا", "تاریخ صحیح وارد کنید (YYYY/MM/DD).")
            return

        rows = []
        for tw in self.task_widgets:
            proj = tw['proj_cb'].currentText().strip()
            if proj not in self.projects:
                QtWidgets.QMessageBox.critical(self, "خطا", "نام پروژه را از لیست انتخاب کنید.")
                return
            status = tw['status_cb'].currentText().strip()
            if not valid_status(status):
                QtWidgets.QMessageBox.critical(self, "خطا", "وضعیت فعالیت را انتخاب کنید.")
                return
            if tw['other_chk'].isChecked():
                perf = tw['other_cb'].currentText().strip()
                if perf not in self.persons:
                    QtWidgets.QMessageBox.critical(self, "خطا", "نام انجام‌دهنده را از لیست انتخاب کنید.")
                    return
            else:
                perf = reporter
            rows.append({
                "project": proj,
                "task": tw['task_le'].text().strip(),
                "status": status,
                "performed_by": perf,
                "duration": int(tw['dur_sb'].value()),
                "note": tw['note_le'].text().strip()
            })

        ok, msg = submit_daily_report(date_str, weekday, reporter, rows)
        if ok:
            QtWidgets.QMessageBox.information(self, "ارسال", msg)
            self._reset_form()                    
        else:
            QtWidgets.QMessageBox.critical(self, "خطا", msg)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qss = os.path.join(os.path.dirname(__file__), "styles", "main.qss")
    if os.path.exists(qss):
        with open(qss, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    w = DailyReportPage()
    w.show()
    sys.exit(app.exec())