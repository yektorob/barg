from .qt import QtWidgets, QtGui, QtCore

DPI = 96
def inch(x):
    return int(x * DPI)


class StyledLineEdit(QtWidgets.QLineEdit):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(40)
        self.setStyleSheet("""
            QLineEdit {
                color: #f5f5f5; background-color: #2C2E33;
                border: 1px solid #383838; border-radius: 20px;
                padding-right: 12px;
            }
        """)


class StyledComboBox(QtWidgets.QComboBox):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setEditable(False)
        self.setFixedHeight(40)
        self._bg_color     = QtGui.QColor("#2C2E33")
        self._border_color = QtGui.QColor("#383838")
        self._arrow_bg     = QtGui.QColor("#383838")
        self._arrow_color  = QtGui.QColor("#f5f5f5")

        if placeholder:
            self.addItem(placeholder)
            try:
                self.model().item(0).setEnabled(False)
            except Exception:
                pass

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()

        pen = QtGui.QPen(self._border_color, 1)
        painter.setPen(pen)
        painter.setBrush(self._bg_color)
        painter.drawRoundedRect(rect, 20, 20)

        diameter = rect.height() - 8
        circle_rect = QtCore.QRect(4, (rect.height() - diameter)//2, diameter, diameter)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._arrow_bg)
        painter.drawEllipse(circle_rect)

        cx, cy = circle_rect.center().x(), circle_rect.center().y()
        points = [QtCore.QPoint(cx-4, cy-2), QtCore.QPoint(cx+4, cy-2), QtCore.QPoint(cx, cy+4)]
        painter.setBrush(self._arrow_color)
        painter.drawPolygon(QtGui.QPolygon(points))

        painter.setPen(self._arrow_color)
        text_rect = rect.adjusted(circle_rect.right()+8, 0, -8, 0)
        painter.drawText(text_rect, QtCore.Qt.AlignVCenter, self.currentText())
        painter.end()


class StyledButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(40)
        try:
            self.setCursor(QtCore.Qt.PointingHandCursor)
        except Exception:
            pass


def _find_abbaspoor_qss() -> str | None:
    candidates = [
        os.path.join(os.path.dirname(__file__), '..', 'styles', 'abbaspoor.qss'),
        os.path.join(os.getcwd(), 'styles', 'abbaspoor.qss'),
        os.path.join(os.path.dirname(__file__), 'styles', 'abbaspoor.qss'),
    ]
    for p in candidates:
        try:
            p0 = os.path.abspath(p)
            if os.path.exists(p0):
                return p0
        except Exception:
            continue
    return None


def apply_abbaspoor_qss(target=None):
    """Load styles/abbaspoor.qss (if present) and apply to `target`.

    `target` can be a QApplication or a QWidget. If None, apply to the
    current QApplication instance when available.
    """
    qss_path = _find_abbaspoor_qss()
    if not qss_path:
        return False
    try:
        with open(qss_path, 'r', encoding='utf-8') as f:
            qss = f.read()
    except Exception:
        return False

    try:
        if target is None:
            app = QtWidgets.QApplication.instance()
            if app is None:
                return False
            app.setStyleSheet(app.styleSheet() + "\n" + qss)
            try:
                app.setLayoutDirection(QtCore.Qt.RightToLeft)
            except Exception:
                pass
            return True
        # QWidget-like
        if hasattr(target, 'setStyleSheet'):
            try:
                target.setStyleSheet(target.styleSheet() + "\n" + qss)
            except Exception:
                target.setStyleSheet(qss)
            try:
                target.setLayoutDirection(QtCore.Qt.RightToLeft)
            except Exception:
                pass
            return True
    except Exception:
        return False
    return False
