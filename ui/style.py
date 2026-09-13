from .qt import QtWidgets, QtGui, QtCore
from ..core.utils import rsrc_path
import os

def apply_qss(app: QtWidgets.QApplication):
    try:
        app.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
    except Exception:
        pass

    for path in ("styles/main.qss", "main.qss"):
        p = rsrc_path(path)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                app.setStyleSheet(app.styleSheet() + "\n" + f.read())
            break

    QtWidgets.QApplication.setStyle("Fusion")

    try:
        dark = QtGui.QColor(45, 45, 48)
        darker = QtGui.QColor(28, 28, 28)
        text = QtGui.QColor(220, 220, 220)
        highlight = QtGui.QColor(0, 122, 204)
        white = QtGui.QColor(255, 255, 255)

        pal = QtGui.QPalette()
        Role = QtGui.QPalette.ColorRole

        pal.setColor(Role.Window, dark)
        pal.setColor(Role.WindowText, text)
        pal.setColor(Role.Base, darker)
        pal.setColor(Role.AlternateBase, dark)
        pal.setColor(Role.ToolTipBase, white)
        pal.setColor(Role.ToolTipText, QtGui.QColor(32, 32, 32))
        pal.setColor(Role.Text, text)
        pal.setColor(Role.Button, dark)
        pal.setColor(Role.ButtonText, text)
        pal.setColor(Role.Highlight, highlight)
        pal.setColor(Role.HighlightedText, QtGui.QColor(240, 240, 240))

        try:
            pal.setColor(Role.PlaceholderText, QtGui.QColor(160, 160, 160))
            pal.setColor(Role.ToolTipText, white)
        except Exception:
            pass

        app.setPalette(pal)
    except Exception:
        pass

    app.setStyleSheet(app.styleSheet() + """
    QLabel,
    QGroupBox, QGroupBox::title,
    QAbstractButton,
    QHeaderView::section,
    QTabBar::tab,
    QTreeView, QListView, QTableView,
    QTreeWidget, QListWidget, QTableWidget {
        color: #ffffff;
    }

    QDialog, QMessageBox, QInputDialog, QProgressDialog {
        background: #2a2a2a;
    }
    QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel, QProgressDialog QLabel {
        color: #ffffff;
    }
    QDialog QPushButton, QMessageBox QPushButton, QProgressDialog QPushButton, QPlainTextEdit {
        color: #ffffff;
        background: #3a3a3a;
        border: 1px solid #555;
        padding: 6px 12px;
        border-radius: 4px;
    }
    QToolTip {
        color: #111111;
        background: #f5f5f5;
        border: 1px solid #888888;
    }
    """)

    FD = QtWidgets.QFileDialog

    def _force_native(func):
        def _inner(*args, **kwargs):
            opts = kwargs.get("options", FD.Options())
            try:
                opts = FD.Options(int(opts) & ~int(FD.Option.DontUseNativeDialog))
            except Exception:
                pass
            kwargs["options"] = opts
            return func(*args, **kwargs)
        return _inner

    FD.getOpenFileName = staticmethod(_force_native(FD.getOpenFileName))
    FD.getOpenFileNames = staticmethod(_force_native(FD.getOpenFileNames))
    FD.getSaveFileName = staticmethod(_force_native(FD.getSaveFileName))
    FD.getExistingDirectory = staticmethod(_force_native(FD.getExistingDirectory))

def fix_item_views_colors(parent: QtWidgets.QWidget):
    dark_bg = "#1d1f23"
    alt_bg = "#24262b"
    white = "#ffffff"
    sel_bg = "#2f7ed8"

    Role = QtGui.QPalette.ColorRole
    for w in parent.findChildren(QtWidgets.QAbstractItemView):
        pal = w.palette()
        pal.setColor(Role.Base, QtGui.QColor(dark_bg))
        pal.setColor(Role.AlternateBase, QtGui.QColor(alt_bg))
        pal.setColor(Role.Text, QtGui.QColor(white))
        pal.setColor(Role.Highlight, QtGui.QColor(sel_bg))
        pal.setColor(Role.HighlightedText, QtGui.QColor(white))
        w.setPalette(pal)