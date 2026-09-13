import os, sys

def rsrc_path(p: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        # مسیر ریشه پکیج (نزدیک به همین فایل)
        base = os.path.dirname(os.path.dirname(__file__))  # بسته به ساختارت
    return os.path.join(base, p)