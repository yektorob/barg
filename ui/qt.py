try:
    from PySide6 import QtWidgets, QtGui, QtCore
    Sig = QtCore.Signal
except Exception:  # fallback PyQt6
    from PyQt6 import QtWidgets, QtGui, QtCore  # type: ignore
    from PyQt6.QtCore import pyqtSignal as Sig  # type: ignore