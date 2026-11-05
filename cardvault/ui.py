# CardVault - user interface
# Copyright (c) 2026 Gabriel Dobre. All rights reserved.

import json
import os
import sys
import time
import unicodedata
from datetime import datetime

from PySide6.QtCore import (QEvent, QLibraryInfo, QObject, QRectF, QSize, QSortFilterProxyModel,
                            Qt, QTimer, QTranslator, Signal)
from PySide6.QtGui import (QAction, QActionGroup, QColor, QFont, QGuiApplication, QIcon,
                           QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap)
from PySide6.QtWidgets import (QApplication, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                               QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
                               QSizePolicy, QStyle, QStyledItemDelegate,
                               QVBoxLayout, QWidget)

from . import APP_NAME, APP_VERSION, AUTHOR, COPYRIGHT, copyright_line, copyright_short
from .banks import BANK_IDS, OTHER_BANK_ID, bank, guess_bank_id, logo_path
from .cards import (COLORS, days_left, detect_brand, digits, expiry_status, format_number,
                    luhn_ok, mask_number, parse_expiry)

EXPIRY_WARNING_DAYS = 60
from . import netguard
from .i18n import LANGUAGES, T, Translator, detect_system_language
from .localpath import (cloud_service, default_vault_path, home_dir, is_network_path,
                        settings_dir)
from .vault import Vault, WrongPassword

AUTO_LOCK_SECONDS = 5 * 60
DETAILS_AUTO_HIDE_SECONDS = 30   # shown card details hide again after 30 s of inactivity
CLIPBOARD_CLEAR_SECONDS = 30
MIN_PASSWORD = 8

# ---------------------------------------------------------------- paths/settings

def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, rel)


def app_data_dir() -> str:
    """Settings folder (local, never synced)."""
    return settings_dir()


def default_db_path() -> str:
    return default_vault_path()


def _legacy_settings_file():
    base = os.environ.get("APPDATA")
    return os.path.join(base, "CardVault", "settings.json") if base else None


def load_settings() -> dict:
    candidates = [os.path.join(app_data_dir(), "settings.json"), _legacy_settings_file()]
    for path in candidates:
        if not path or is_network_path(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def save_settings(settings: dict):
    folder = app_data_dir()
    if is_network_path(folder):
        return  # never write anything to the network
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "settings.json"), "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


class _HideNetworkDrives(QSortFilterProxyModel):
    """Hides mapped network drives from the file dialog."""

    def filterAcceptsRow(self, row, parent):
        model = self.sourceModel()
        idx = model.index(row, 0, parent)
        path = model.filePath(idx) if hasattr(model, "filePath") else ""
        root = path.rstrip("/\\")
        if len(root) == 2 and root[1] == ":":     # drive root, e.g. "Z:"
            return not is_network_path(root + "\\")
        return True


def pick_vault_file(parent, tr, title, start, save=True):
    """File dialog (Qt, non-native: no shell extensions, no "Network" section).

    Returns a validated local path, or None. Rejects network locations and
    warns about cloud-synced folders.
    """
    while True:
        dlg = QFileDialog(parent, title, start, "CardVault (*.cvw)")
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg.setProxyModel(_HideNetworkDrives(dlg))
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave if save else QFileDialog.AcceptMode.AcceptOpen)
        dlg.setFileMode(QFileDialog.FileMode.AnyFile if save else QFileDialog.FileMode.ExistingFile)
        if save:
            dlg.setDefaultSuffix("cvw")
        L = QFileDialog.DialogLabel
        dlg.setLabelText(L.LookIn, tr("fd_look_in"))
        dlg.setLabelText(L.FileName, tr("fd_file_name"))
        dlg.setLabelText(L.FileType, tr("fd_file_type"))
        dlg.setLabelText(L.Accept, tr("save") if save else tr("fd_open"))
        dlg.setLabelText(L.Reject, tr("cancel"))
        dlg.resize(820, 520)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.selectedFiles():
            return None
        path = os.path.abspath(dlg.selectedFiles()[0])
        if save and not path.lower().endswith(".cvw"):
            path += ".cvw"
        ok, path = check_local_location(parent, tr, path)
        if ok:
            return path
        start = os.path.dirname(start) if start else home_dir()


_QT_TRANSLATOR = None


def install_qt_translator(lang: str):
    """Qt translations (file dialog etc.) for the languages where they exist."""
    global _QT_TRANSLATOR
    app = QApplication.instance()
    if app is None:
        return
    if _QT_TRANSLATOR is not None:
        app.removeTranslator(_QT_TRANSLATOR)
        _QT_TRANSLATOR = None
    folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    tr = QTranslator()
    if tr.load(f"qtbase_{lang}", folder):
        app.installTranslator(tr)
        _QT_TRANSLATOR = tr


def check_local_location(parent, tr, path):
    """(ok, path). Rejects network paths; asks for confirmation on cloud folders."""
    if is_network_path(path):
        QMessageBox.warning(parent, tr("local_only_title"), tr("network_path_blocked"))
        return False, path
    service = cloud_service(path)
    if service and not ask(parent, tr, tr("cloud_warning", service=service)):
        return False, path
    return True, path


# ---------------------------------------------------------------- theme

C_BG = "#0f1420"
C_PANEL = "#171d2b"
C_PANEL2 = "#1d2436"
C_BORDER = "#283149"
C_TEXT = "#e6e9f0"
C_MUTED = "#8a93a8"
C_ACCENT = "#4f7cff"
C_DANGER = "#ff5c6c"
C_WARN = "#ffb547"

STYLE = f"""
* {{ font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 10pt; color: {C_TEXT}; }}
QMainWindow, QDialog, QWidget#page {{ background: {C_BG}; }}
QMenuBar {{ background: {C_PANEL}; border-bottom: 1px solid {C_BORDER}; }}
QMenuBar::item {{ padding: 6px 12px; background: transparent; }}
QMenuBar::item:selected {{ background: {C_PANEL2}; }}
QMenu {{ background: {C_PANEL}; border: 1px solid {C_BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 24px; border-radius: 4px; }}
QMenu::item:selected {{ background: {C_ACCENT}; }}
QMenu::separator {{ height: 1px; background: {C_BORDER}; margin: 4px 8px; }}
QStatusBar {{ background: {C_PANEL}; border-top: 1px solid {C_BORDER}; color: {C_MUTED}; }}
QStatusBar QLabel {{ color: {C_MUTED}; font-size: 9pt; }}
QLineEdit, QPlainTextEdit {{
    background: {C_PANEL2}; border: 1px solid {C_BORDER}; border-radius: 8px;
    padding: 8px 10px; selection-background-color: {C_ACCENT};
}}
QLineEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {C_ACCENT}; }}
QPushButton {{
    background: {C_PANEL2}; border: 1px solid {C_BORDER}; border-radius: 8px; padding: 8px 16px;
}}
QPushButton:hover {{ border-color: {C_ACCENT}; }}
QPushButton:disabled {{ color: {C_MUTED}; }}
QPushButton#primary {{ background: {C_ACCENT}; border: none; font-weight: 600; color: white; }}
QPushButton#primary:hover {{ background: #6a90ff; }}
QPushButton#primary:disabled {{ background: #34436e; color: #9aa7c9; }}
QPushButton#danger {{ color: {C_DANGER}; }}
QPushButton#danger:hover {{ border-color: {C_DANGER}; }}
QPushButton#link {{ background: transparent; border: none; color: {C_MUTED}; padding: 4px; }}
QPushButton#link:hover {{ color: {C_TEXT}; text-decoration: underline; }}
QLabel#offline {{ color: #3ccf91; font-weight: 600; }}
QFileDialog {{ background: {C_BG}; }}
QFileDialog QListView, QFileDialog QTreeView {{ background: {C_PANEL}; border: 1px solid {C_BORDER}; }}
QHeaderView {{ background: {C_PANEL2}; }}
QHeaderView::section {{ background: {C_PANEL2}; border: none; padding: 4px; }}
QToolButton {{ background: {C_PANEL2}; border: 1px solid {C_BORDER}; border-radius: 6px; padding: 3px; }}
QPushButton#small {{ padding: 4px 10px; font-size: 9pt; border-radius: 6px; }}
QListWidget {{ background: {C_PANEL}; border: none; outline: none; }}
QFrame#sidebar {{ background: {C_PANEL}; border-right: 1px solid {C_BORDER}; }}
QFrame#box {{ background: {C_PANEL}; border: 1px solid {C_BORDER}; border-radius: 14px; }}
QLabel#title {{ font-size: 18pt; font-weight: 600; }}
QLabel#muted {{ color: {C_MUTED}; }}
QLabel#error {{ color: {C_DANGER}; }}
QLabel#fieldName {{ color: {C_MUTED}; font-size: 9pt; }}
QLabel#fieldValue {{ font-size: 11pt; }}
QComboBox {{
    background: {C_PANEL2}; border: 1px solid {C_BORDER}; border-radius: 8px; padding: 4px 10px;
}}
QComboBox:focus {{ border: 1px solid {C_ACCENT}; }}
QComboBox QAbstractItemView {{
    background: {C_PANEL}; border: 1px solid {C_BORDER}; selection-background-color: {C_ACCENT};
    padding: 4px; outline: none;
}}
QComboBox QAbstractItemView::item {{ min-height: 34px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {C_BORDER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QMessageBox QLabel {{ min-width: 280px; }}
"""


def mono_font(size: float, bold=False) -> QFont:
    f = QFont("Consolas")
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setPointSizeF(size)
    f.setBold(bold)
    return f


def card_bank_id(card: dict) -> str:
    bid = card.get("bank_id") or guess_bank_id(card.get("bank", ""))
    if not bid and (card.get("bank") or "").strip():
        bid = OTHER_BANK_ID          # free-text bank that is not in the list
    return bid


def card_custom_colors(card: dict):
    """The user's colour override (c1, c2), or None to use the bank's colours."""
    cc = card.get("custom_colors")
    if isinstance(cc, (list, tuple)) and len(cc) == 2 and all(QColor(c).isValid() for c in cc):
        return tuple(cc)
    return None


def readable_text_color(c1: str, c2: str) -> QColor:
    """Black or white text, whichever reads better on the given gradient."""
    def lum(c):
        q = QColor(c)
        return 0.2126 * q.redF() + 0.7152 * q.greenF() + 0.0722 * q.blueF()
    return QColor("#000000") if (lum(c1) + lum(c2)) / 2 > 0.55 else QColor("#FFFFFF")


_LOGO_CACHE = {}


def bank_logo(bank_id: str):
    if bank_id not in _LOGO_CACHE:
        path = logo_path(bank_id)
        pm = QPixmap(path) if path else QPixmap()
        _LOGO_CACHE[bank_id] = pm if not pm.isNull() else None
    return _LOGO_CACHE[bank_id]


def draw_bank_mark(p: QPainter, area: QRectF, bank_id: str, color: QColor, align_left=True, mini=False,
                   label=None):
    """The bank logo (if the file exists) or its name (or `label`, if given)."""
    b = bank(bank_id)
    logo = None if label is not None else bank_logo(bank_id)
    if logo:
        scaled = logo.scaled(int(area.width()), int(area.height()),
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        x = area.x() if align_left else area.center().x() - scaled.width() / 2
        p.drawPixmap(int(x), int(area.center().y() - scaled.height() / 2), scaled)
        return
    f = QFont()
    f.setBold(True)
    f.setPixelSize(max(6, int(area.height() * 0.78)))
    f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)
    if label is None:
        label = b.get("mini", b["short"]) if mini else b["short"]
    p.setFont(f)
    while p.fontMetrics().horizontalAdvance(label) > area.width() and f.pixelSize() > 6:
        f.setPixelSize(f.pixelSize() - 1)
        p.setFont(f)
    p.setPen(color)
    flags = (Qt.AlignmentFlag.AlignLeft if align_left else Qt.AlignmentFlag.AlignHCenter) | Qt.AlignmentFlag.AlignVCenter
    p.drawText(area, flags, p.fontMetrics().elidedText(label, Qt.TextElideMode.ElideRight, int(area.width())))


# ---------------------------------------------------------------- card drawing

def paint_card(p: QPainter, rect: QRectF, card: dict, tr, reveal=False, compact=False):
    bid = card_bank_id(card)
    theme = bank(bid)
    custom = card_custom_colors(card)
    is_other = bid == OTHER_BANK_ID
    ghost = is_other and not custom            # "Other bank" without a colour: outline only
    if custom:                                 # user colour override; the bank name/logo stays
        c1, c2 = custom
        text = readable_text_color(c1, c2)
        accent = QColor(text)
        deco_alpha = 30
    elif ghost:
        c1 = c2 = None
        text = QColor(C_TEXT)
        accent = QColor(C_MUTED)
        deco_alpha = 0
    else:
        c1, c2 = theme["colors"]
        text = QColor(theme["text"])
        accent = QColor(theme["accent"])
        deco_alpha = theme.get("deco_alpha", 38)
    soft = QColor(text)
    soft.setAlpha(185)
    w, h = rect.width(), rect.height()
    radius = h * 0.08
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if ghost:
        p.setPen(QPen(QColor(C_MUTED), max(1.2, h * 0.012)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
    else:
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0, QColor(c1))
        grad.setColorAt(1, QColor(c2))
        p.fillPath(path, grad)
        p.setClipPath(path)
        # decorative shapes in the accent colour
        p.setPen(Qt.PenStyle.NoPen)
        deco = QColor(accent)
        deco.setAlpha(deco_alpha)
        p.setBrush(deco)
        p.drawEllipse(QRectF(rect.x() + w * 0.58, rect.y() - h * 0.5, w * 0.8, w * 0.8))
        p.setBrush(QColor(255, 255, 255, 16))
        p.drawEllipse(QRectF(rect.x() + w * 0.35, rect.y() + h * 0.5, w * 0.9, w * 0.9))
        p.setClipping(False)
        p.setPen(QColor(255, 255, 255, 45))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    if compact:
        if is_other:
            qf = QFont()
            qf.setBold(True)
            qf.setPixelSize(max(8, int(h * 0.6)))
            p.setFont(qf)
            p.setPen(text)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "?")
        elif bid:
            draw_bank_mark(p, rect.adjusted(w * 0.1, h * 0.28, -w * 0.1, -h * 0.28), bid, text, align_left=False, mini=True)
        p.restore()
        return

    pad = w * 0.07

    # bank logo / name (top left)
    other_label = ((card.get("bank") or "").strip() or "?") if is_other else None
    draw_bank_mark(p, QRectF(rect.x() + pad, rect.y() + pad * 0.75, w * 0.5, h * 0.15), bid, text,
                   label=other_label)

    # card network (top right) — short code + auto-shrink so it never overlaps the bank
    brand = {"American Express": "AMEX", "Diners Club": "DINERS"}.get(
        detect_brand(card.get("number", "")), detect_brand(card.get("number", "")).upper())
    brand_area = QRectF(rect.x() + w * 0.54, rect.y() + pad * 0.75, w * 0.46 - pad, h * 0.15)
    f = QFont()
    f.setBold(True)
    f.setItalic(True)
    f.setPixelSize(max(8, int(h * 0.09)))
    p.setFont(f)
    while brand and p.fontMetrics().horizontalAdvance(brand) > brand_area.width() and f.pixelSize() > 7:
        f.setPixelSize(f.pixelSize() - 1)
        p.setFont(f)
    p.setPen(text)
    p.drawText(brand_area, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, brand)

    # chip
    chip = QRectF(rect.x() + pad, rect.y() + h * 0.32, w * 0.12, h * 0.17)
    cg = QLinearGradient(chip.topLeft(), chip.bottomRight())
    cg.setColorAt(0, QColor("#f5d77a"))
    cg.setColorAt(1, QColor("#b8902e"))
    p.setPen(QPen(QColor(120, 90, 20, 160), 1))
    p.setBrush(cg)
    p.drawRoundedRect(chip, chip.height() * 0.18, chip.height() * 0.18)
    p.drawLine(chip.left(), chip.center().y(), chip.right(), chip.center().y())
    p.drawLine(chip.center().x(), chip.top(), chip.center().x(), chip.bottom())

    # card name (right, next to the chip)
    lf = QFont()
    lf.setPixelSize(max(7, int(h * 0.06)))
    p.setFont(lf)
    p.setPen(soft)
    lrect = QRectF(rect.x() + w * 0.3, rect.y() + h * 0.32, w * 0.7 - pad, h * 0.17)
    p.drawText(lrect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
               p.fontMetrics().elidedText(card.get("label", ""), Qt.TextElideMode.ElideRight, int(lrect.width())))

    # card number
    num = format_number(card.get("number", "")) if reveal else mask_number(card.get("number", ""))
    nf = mono_font(1)
    nf.setPixelSize(max(8, int(h * 0.105)))
    p.setFont(nf)
    p.setPen(text)
    p.drawText(QRectF(rect.x() + pad, rect.y() + h * 0.55, w - 2 * pad, h * 0.15),
               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, num)

    # cardholder + expiry
    f2 = QFont()
    f2.setPixelSize(max(7, int(h * 0.05)))
    p.setFont(f2)
    p.setPen(soft)
    p.drawText(QRectF(rect.x() + w * 0.55, rect.y() + h * 0.73, w * 0.45 - pad, h * 0.08),
               Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, tr("valid_thru"))
    f3 = QFont()
    f3.setPixelSize(max(8, int(h * 0.075)))
    f3.setBold(True)
    p.setFont(f3)
    p.setPen(text)
    holder = (card.get("holder") or "").upper()
    hrect = QRectF(rect.x() + pad, rect.y() + h * 0.81, w * 0.6, h * 0.12)
    p.drawText(hrect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
               p.fontMetrics().elidedText(holder, Qt.TextElideMode.ElideRight, int(hrect.width())))
    ef = mono_font(1, bold=True)
    ef.setPixelSize(max(8, int(h * 0.08)))
    p.setFont(ef)
    p.drawText(QRectF(rect.x() + w * 0.62, rect.y() + h * 0.81, w * 0.38 - pad, h * 0.12),
               Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, card.get("expiry", ""))
    p.restore()


class CardView(QWidget):
    RATIO = 85.6 / 53.98

    def __init__(self, tr, parent=None):
        super().__init__(parent)
        self.tr = tr
        self.card = {}
        self.reveal = False
        self.setMinimumSize(300, 190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(230)

    def set_card(self, card, reveal=False):
        self.card = card or {}
        self.reveal = reveal
        self.update()

    def paintEvent(self, _):
        w = min(self.width(), self.height() * self.RATIO)
        h = w / self.RATIO
        rect = QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)
        p = QPainter(self)
        paint_card(p, rect.adjusted(1, 1, -1, -1), self.card, self.tr, self.reveal)
        p.end()


class CardItemDelegate(QStyledItemDelegate):
    def __init__(self, tr, parent=None):
        super().__init__(parent)
        self.tr = tr

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 68)

    def paint(self, p, option, index):
        card = index.data(Qt.ItemDataRole.UserRole) or {}
        r = QRectF(option.rect).adjusted(8, 4, -8, -4)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = option.state & QStyle.StateFlag.State_Selected
        hover = option.state & QStyle.StateFlag.State_MouseOver
        if selected or hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(C_ACCENT if selected else C_PANEL2))
            if selected:
                p.setBrush(QColor(79, 124, 255, 60))
            p.drawRoundedRect(r, 10, 10)
        mini = QRectF(r.x() + 10, r.center().y() - 17, 54, 34)
        paint_card(p, mini, card, self.tr, compact=True)

        x = mini.right() + 12
        status = expiry_status(card.get("expiry", ""))
        badge_w = 0
        if status in ("expired", "soon"):
            text = self.tr("expired" if status == "expired" else "expires_soon")
            bf = QFont()
            bf.setPointSizeF(8)
            p.setFont(bf)
            badge_w = p.fontMetrics().horizontalAdvance(text) + 14
            br = QRectF(r.right() - badge_w - 8, r.center().y() - 10, badge_w, 20)
            col = QColor(C_DANGER if status == "expired" else C_WARN)
            bg = QColor(col)
            bg.setAlpha(40)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(br, 10, 10)
            p.setPen(col)
            p.drawText(br, Qt.AlignmentFlag.AlignCenter, text)
            badge_w += 12
        avail = int(r.right() - x - badge_w - 8)

        tf = QFont()
        tf.setPointSizeF(10.5)
        tf.setBold(True)
        p.setFont(tf)
        p.setPen(QColor(C_TEXT))
        p.drawText(QRectF(x, r.y() + 10, avail, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   p.fontMetrics().elidedText(card.get("label", ""), Qt.TextElideMode.ElideRight, avail))
        sf = QFont()
        sf.setPointSizeF(9)
        p.setFont(sf)
        p.setPen(QColor(C_MUTED))
        parts = [s for s in (card.get("bank"), "•••• " + digits(card.get("number", ""))[-4:]) if s]
        p.drawText(QRectF(x, r.y() + 32, avail, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   p.fontMetrics().elidedText("  ·  ".join(parts), Qt.TextElideMode.ElideRight, avail))
        p.restore()


# ---------------------------------------------------------------- dialogs

def ask(parent, tr, text) -> bool:
    """Yes/No confirmation with translated buttons (Qt has no Romanian translation)."""
    box = QMessageBox(parent)
    box.setWindowTitle(tr("confirm"))
    box.setIcon(QMessageBox.Icon.Question)
    box.setText(text)
    yes = box.addButton(tr("yes"), QMessageBox.ButtonRole.YesRole)
    no = box.addButton(tr("no"), QMessageBox.ButtonRole.NoRole)
    box.setDefaultButton(no)
    box.exec()
    return box.clickedButton() is yes


def inform(parent, tr, text):
    box = QMessageBox(parent)
    box.setWindowTitle(APP_NAME)
    box.setIcon(QMessageBox.Icon.Information)
    box.setText(text)
    box.addButton(tr("ok"), QMessageBox.ButtonRole.AcceptRole)
    box.exec()

def bank_swatch(card_or_bank, tr, w=40, h=26) -> QPixmap:
    card = card_or_bank if isinstance(card_or_bank, dict) else {"bank_id": card_or_bank}
    pm = QPixmap(w * 2, h * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    paint_card(p, QRectF(1, 1, w - 2, h - 2), card, tr, compact=True)
    p.end()
    return pm


class CardDialog(QDialog):
    def __init__(self, tr, card=None, parent=None):
        super().__init__(parent)
        self.tr = tr
        self.card = dict(card or {})
        self.setWindowTitle(tr("edit_card") if card else tr("add_card"))
        self.setMinimumWidth(580)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)
        self.preview = CardView(tr)
        self.preview.setFixedHeight(200)
        lay.addWidget(self.preview)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.e_label = QLineEdit(self.card.get("label", ""))
        self.e_bank = QComboBox()
        self.e_bank.setIconSize(QSize(40, 26))
        self.e_bank.setMinimumHeight(38)
        self.e_bank.addItem(tr("choose_bank"), "")
        for bid in BANK_IDS:
            self.e_bank.addItem(QIcon(bank_swatch(bid, tr)), bank(bid)["name"], bid)
        self.e_bank.addItem(QIcon(bank_swatch(OTHER_BANK_ID, tr)), tr("other_bank"), OTHER_BANK_ID)
        current = card_bank_id(self.card)
        self.e_bank.setCurrentIndex(max(0, self.e_bank.findData(current)) if current else 0)
        # bank name, typed by the user when "Other bank" is selected
        self.e_bank_name = QLineEdit(self.card.get("bank", "") if current == OTHER_BANK_ID else "")
        self.e_bank_name.setPlaceholderText(tr("other_bank_name"))
        self.e_bank_name.setMaxLength(40)
        # card colour: bank default, a preset, or any colour
        self.custom_colors = card_custom_colors(self.card)
        color_row = QHBoxLayout()
        color_row.setSpacing(6)
        # first swatch = the selected bank's own colours (the default, preselected)
        self.btn_default_color = QPushButton()
        self.btn_default_color.setFixedSize(26, 26)
        self.btn_default_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_default_color.clicked.connect(lambda: self.set_colors(None))
        color_row.addWidget(self.btn_default_color)
        sep = QFrame()
        sep.setFixedSize(1, 20)
        sep.setStyleSheet(f"background: {C_BORDER};")
        color_row.addSpacing(4)
        color_row.addWidget(sep)
        color_row.addSpacing(4)
        self.color_btns = []
        for c1, c2 in COLORS:
            b = QPushButton()
            b.setFixedSize(26, 26)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setProperty("grad", (c1, c2))
            b.clicked.connect(lambda _=False, a=c1, z=c2: self.set_colors((a, z)))
            color_row.addWidget(b)
            self.color_btns.append(b)
        self.btn_pick_color = QPushButton("+")
        self.btn_pick_color.setFixedSize(26, 26)
        self.btn_pick_color.setToolTip(tr("color_custom"))
        self.btn_pick_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pick_color.clicked.connect(self.pick_color)
        color_row.addWidget(self.btn_pick_color)
        color_row.addStretch()
        # caption under the swatches: what is currently selected
        self.color_caption = QLabel()
        self.color_caption.setObjectName("muted")
        color_box = QVBoxLayout()
        color_box.setSpacing(4)
        color_box.addLayout(color_row)
        color_box.addWidget(self.color_caption)
        self.e_holder = QLineEdit(self.card.get("holder", ""))
        self.e_number = QLineEdit(format_number(self.card.get("number", "")))
        self.e_number.setFont(mono_font(11))
        self.e_number.setMaxLength(23)
        self.e_expiry = QLineEdit(self.card.get("expiry", ""))
        self.e_expiry.setInputMask("99/99;_")
        self.e_expiry.setFont(mono_font(11))
        self.e_expiry.setFixedWidth(110)
        self.e_cvv = QLineEdit(self.card.get("cvv", ""))
        self.e_cvv.setEchoMode(QLineEdit.EchoMode.Password)
        self.e_cvv.setMaxLength(4)
        self.e_cvv.setFixedWidth(110)
        self.e_pin = QLineEdit(self.card.get("pin", ""))
        self.e_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.e_pin.setMaxLength(12)
        self.e_pin.setFixedWidth(110)
        self.e_notes = QPlainTextEdit(self.card.get("notes", ""))
        self.e_notes.setFixedHeight(70)

        form.addRow(tr("bank") + " *", self.e_bank)
        form.addRow("", self.e_bank_name)
        self._bank_name_row = form.rowCount() - 1
        self._form = form
        form.addRow(tr("color"), color_box)
        form.addRow(tr("label") + " *", self.e_label)
        form.addRow(tr("holder"), self.e_holder)
        form.addRow(tr("number") + " *", self.e_number)
        form.addRow(tr("expiry") + " *", self.e_expiry)
        form.addRow(tr("cvv"), self.e_cvv)
        form.addRow(tr("pin"), self.e_pin)
        form.addRow(tr("notes"), self.e_notes)
        lay.addLayout(form)

        self.error = QLabel()
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)

        btns = QDialogButtonBox()
        ok = btns.addButton(tr("save"), QDialogButtonBox.ButtonRole.AcceptRole)
        ok.setObjectName("primary")
        btns.addButton(tr("cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        btns.accepted.connect(self.on_save)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        for e in (self.e_label, self.e_holder, self.e_expiry, self.e_bank_name):
            e.textChanged.connect(self.update_preview)
        self.e_bank.currentIndexChanged.connect(self.on_bank_changed)
        self.e_number.textEdited.connect(self.on_number_edited)
        self.on_bank_changed()
        self.set_colors(self.custom_colors)

    def on_bank_changed(self, *_):
        is_other = self.e_bank.currentData() == OTHER_BANK_ID
        self._form.setRowVisible(self._bank_name_row, is_other)
        if is_other:
            self.e_bank_name.setFocus()
        if hasattr(self, "color_btns"):
            self.set_colors(self.custom_colors)   # refresh the "bank colours" swatch
        self.update_preview()

    @staticmethod
    def _swatch_style(bg, selected, check_color="#FFFFFF", dashed=False):
        if selected:
            border = "2px solid white"
        else:
            border = f"1px {'dashed' if dashed else 'solid'} {C_MUTED if dashed else C_BORDER}"
        return (f"QPushButton {{ border-radius: 13px; border: {border}; padding: 0; background: {bg};"
                f" color: {check_color}; font-weight: 800; font-size: 11pt; }}")

    def set_colors(self, colors):
        """None = the bank's own colours (default); (c1, c2) = colour override."""
        tr = self.tr
        self.custom_colors = tuple(colors) if colors else None
        grad = "qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {}, stop:1 {})".format
        check = "✓"

        # default = the selected bank's colours, shown as the first swatch
        bid = self.e_bank.currentData() or ""
        is_default = self.custom_colors is None
        if bid and bid != OTHER_BANK_ID:
            a, z = bank(bid)["colors"]
            self.btn_default_color.setStyleSheet(
                self._swatch_style(grad(a, z), is_default, readable_text_color(a, z).name()))
            default_caption = tr("color_bank_default")
        else:                                   # "Other bank" / no bank: outline only (ghost)
            self.btn_default_color.setStyleSheet(
                self._swatch_style("transparent", is_default, C_TEXT, dashed=True))
            default_caption = tr("color_none")
        self.btn_default_color.setText(check if is_default else "")
        self.btn_default_color.setToolTip(default_caption)

        for b in self.color_btns:
            a, z = b.property("grad")
            selected = self.custom_colors == (a, z)
            b.setStyleSheet(self._swatch_style(grad(a, z), selected, readable_text_color(a, z).name()))
            b.setText(check if selected else "")

        is_preset = self.custom_colors in [tuple(c) for c in COLORS]
        custom_other = self.custom_colors is not None and not is_preset
        if custom_other:
            a, z = self.custom_colors
            self.btn_pick_color.setStyleSheet(
                self._swatch_style(grad(a, z), True, readable_text_color(a, z).name()))
            self.btn_pick_color.setText(check)
        else:
            self.btn_pick_color.setStyleSheet(self._swatch_style(C_PANEL2, False, C_TEXT))
            self.btn_pick_color.setText("+")
        self.btn_pick_color.setToolTip(tr("color_custom"))

        self.color_caption.setText(default_caption if is_default else tr("color_selected_custom"))
        self.update_preview()

    def pick_color(self):
        start = QColor(self.custom_colors[0]) if self.custom_colors else QColor("#4f7cff")
        dlg = QColorDialog(start, self)
        dlg.setWindowTitle(self.tr("color_pick_title"))
        dlg.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selectedColor().isValid():
            c = dlg.selectedColor()
            self.set_colors((c.name(), c.darker(145).name()))

    def on_number_edited(self, text):
        formatted = format_number(text)[:23]
        if formatted != text:
            self.e_number.setText(formatted)
        self.update_preview()

    def collect(self) -> dict:
        exp = self.e_expiry.text()
        if digits(exp) == "":
            exp = ""
        bid = self.e_bank.currentData() or ""
        bank_name = self.e_bank_name.text().strip() if bid == OTHER_BANK_ID else bank(bid)["name"]
        data = {**self.card,
                "label": self.e_label.text().strip(),
                "bank_id": bid,
                "bank": bank_name,
                "holder": self.e_holder.text().strip(),
                "number": digits(self.e_number.text()),
                "expiry": exp,
                "cvv": self.e_cvv.text().strip(),
                "pin": self.e_pin.text().strip(),
                "notes": self.e_notes.toPlainText().strip()}
        if getattr(self, "custom_colors", None):
            data["custom_colors"] = list(self.custom_colors)
        else:
            data.pop("custom_colors", None)
        return data

    def update_preview(self):
        self.preview.set_card(self.collect(), reveal=True)

    def fail(self, msg, widget):
        self.error.setText(msg)
        widget.setFocus()

    def on_save(self):
        tr = self.tr
        c = self.collect()
        c.pop("color", None)
        if not c["bank_id"]:
            self.e_bank.showPopup()
            return self.fail(tr("bank_required"), self.e_bank)
        if c["bank_id"] == OTHER_BANK_ID and not c["bank"]:
            return self.fail(tr("required", field=tr("other_bank_name")), self.e_bank_name)
        if not c["label"]:
            return self.fail(tr("required", field=tr("label")), self.e_label)
        if not 12 <= len(c["number"]) <= 19:
            return self.fail(tr("invalid_number"), self.e_number)
        if not parse_expiry(c["expiry"]):
            return self.fail(tr("invalid_expiry"), self.e_expiry)
        if c["cvv"] and not (c["cvv"].isdigit() and 3 <= len(c["cvv"]) <= 4):
            return self.fail(tr("invalid_cvv"), self.e_cvv)
        if c["pin"] and not (c["pin"].isdigit() and 4 <= len(c["pin"]) <= 12):
            return self.fail(tr("invalid_pin"), self.e_pin)
        if not luhn_ok(c["number"]):
            if not ask(self, tr, tr("luhn_warning")):
                return self.e_number.setFocus()
        self.result_card = c
        self.accept()


class ChangePasswordDialog(QDialog):
    def __init__(self, tr, parent=None):
        super().__init__(parent)
        self.tr = tr
        self.setWindowTitle(tr("change_password").rstrip("…"))
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        form = QFormLayout()
        form.setSpacing(10)
        self.old = QLineEdit()
        self.new = QLineEdit()
        self.new2 = QLineEdit()
        for e in (self.old, self.new, self.new2):
            e.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(tr("current_password"), self.old)
        form.addRow(tr("new_password"), self.new)
        form.addRow(tr("confirm_password"), self.new2)
        lay.addLayout(form)
        self.error = QLabel()
        self.error.setObjectName("error")
        lay.addWidget(self.error)
        btns = QDialogButtonBox()
        ok = btns.addButton(tr("save"), QDialogButtonBox.ButtonRole.AcceptRole)
        ok.setObjectName("primary")
        btns.addButton(tr("cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        btns.accepted.connect(self.on_ok)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def on_ok(self):
        if len(self.new.text()) < MIN_PASSWORD:
            self.error.setText(self.tr("pw_too_short", n=MIN_PASSWORD))
            return
        if self.new.text() != self.new2.text():
            self.error.setText(self.tr("pw_mismatch"))
            return
        self.accept()


# ---------------------------------------------------------------- login page

class LoginPage(QWidget):
    def __init__(self, window, create_mode: bool):
        super().__init__()
        self.setObjectName("page")
        self.win = window
        tr = window.tr
        self.create_mode = create_mode
        self.failures = 0
        self.wait_until = 0

        outer = QVBoxLayout(self)
        outer.addStretch()
        box = QFrame()
        box.setObjectName("box")
        box.setFixedWidth(420)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(36, 32, 36, 32)
        lay.setSpacing(12)

        logo = QLabel()
        logo.setPixmap(window.windowIcon().pixmap(64, 64))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)
        name = QLabel(APP_NAME)
        name.setObjectName("title")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(name)
        tag = QLabel(tr("tagline"))
        tag.setObjectName("muted")
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(tag)
        lay.addSpacing(10)

        head = QLabel(tr("create_title") if create_mode else tr("unlock_title"))
        head.setStyleSheet("font-size: 13pt; font-weight: 600;")
        lay.addWidget(head)
        info = QLabel(tr("create_info") if create_mode else tr("unlock_info"))
        info.setObjectName("muted")
        info.setWordWrap(True)
        lay.addWidget(info)

        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw.setPlaceholderText(tr("password"))
        lay.addWidget(self.pw)
        self.pw2 = None
        self.db_path = window.vault.path if window.vault else default_db_path()
        if create_mode:
            self.pw2 = QLineEdit()
            self.pw2.setEchoMode(QLineEdit.EchoMode.Password)
            self.pw2.setPlaceholderText(tr("confirm_password"))
            lay.addWidget(self.pw2)
            self.pw2.returnPressed.connect(self.submit)

            lay.addSpacing(4)
            loc_label = QLabel(tr("create_location"))
            loc_label.setObjectName("fieldName")
            lay.addWidget(loc_label)
            loc_row = QHBoxLayout()
            loc_row.setSpacing(8)
            self.loc_edit = QLineEdit(self.db_path)
            self.loc_edit.setReadOnly(True)
            self.loc_edit.setCursorPosition(0)
            self.loc_edit.setToolTip(self.db_path)
            loc_row.addWidget(self.loc_edit, 1)
            browse = QPushButton(tr("browse"))
            browse.setCursor(Qt.CursorShape.PointingHandCursor)
            browse.clicked.connect(self.choose_location)
            loc_row.addWidget(browse)
            lay.addLayout(loc_row)
        self.pw.returnPressed.connect(self.submit)

        self.error = QLabel()
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)

        self.btn = QPushButton(tr("create_btn") if create_mode else tr("unlock_btn"))
        self.btn.setObjectName("primary")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self.submit)
        lay.addWidget(self.btn)

        open_btn = QPushButton(tr("open_existing"))
        open_btn.setObjectName("link")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(self.win.open_vault)
        lay.addWidget(open_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(box)
        h.addStretch()
        outer.addLayout(h)
        outer.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        QTimer.singleShot(0, self.pw.setFocus)

    def choose_location(self):
        tr = self.win.tr
        start = self.db_path or default_db_path()
        path = pick_vault_file(self, tr, tr("save_db_title"), start, save=True)
        if path:
            self.db_path = path
            self.loc_edit.setText(path)
            self.loc_edit.setCursorPosition(0)
            self.loc_edit.setToolTip(path)

    def tick(self):
        left = int(self.wait_until - time.monotonic() + 0.99)
        if left <= 0:
            self.timer.stop()
            self.btn.setEnabled(True)
            self.pw.setEnabled(True)
            self.error.setText("")
            self.pw.setFocus()
        else:
            self.error.setText(self.win.tr("wait_seconds", s=left))

    def submit(self):
        tr = self.win.tr
        if not self.btn.isEnabled():
            return
        pw = self.pw.text()
        if self.create_mode:
            if len(pw) < MIN_PASSWORD:
                self.error.setText(tr("pw_too_short", n=MIN_PASSWORD))
                return
            if pw != self.pw2.text():
                self.error.setText(tr("pw_mismatch"))
                return
            ok, self.db_path = check_local_location(self, tr, self.db_path)
            if not ok:
                self.choose_location()
                return
        self.error.setText("")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            if self.create_mode:
                self.win.create_wallet(self.db_path, pw)
            else:
                self.win.vault.unlock(pw)
        except WrongPassword:
            QApplication.restoreOverrideCursor()
            self.failures += 1
            self.pw.selectAll()
            if self.failures >= 3:
                delay = min(60, 5 * (self.failures - 2))
                self.wait_until = time.monotonic() + delay
                self.btn.setEnabled(False)
                self.pw.setEnabled(False)
                self.timer.start(250)
                self.tick()
            else:
                self.error.setText(tr("wrong_password"))
            return
        except Exception as e:  # e.g. the chosen file cannot be written
            QApplication.restoreOverrideCursor()
            self.error.setText(str(e))
            return
        QApplication.restoreOverrideCursor()
        self.pw.clear()
        self.win.show_wallet()


# ---------------------------------------------------------------- wallet page

# ---------------------------------------------------------------- sorting

SORT_MODES = ("bank", "name", "custom")


def _fold(text: str) -> str:
    """Case- and accent-insensitive sort key ("Ștefan" sorts next to "Stefan")."""
    norm = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in norm if not unicodedata.combining(ch)).casefold()


def sort_cards(cards, mode, order=None):
    """bank: by bank name, then card name (default) · name: by card name · custom: user order."""
    by_bank = lambda c: (_fold(c.get("bank")) or "\uffff", _fold(c.get("label")))
    if mode == "name":
        return sorted(cards, key=lambda c: (_fold(c.get("label")), _fold(c.get("bank"))))
    if mode == "custom":
        pos = {cid: i for i, cid in enumerate(order or [])}
        # cards not in the saved order (e.g. newly added) go to the end
        return sorted(cards, key=lambda c: (pos.get(c["id"], len(pos)), by_bank(c)))
    return sorted(cards, key=by_bank)


class CardList(QListWidget):
    """Card list with drag & drop reordering; emits orderChanged after a drop."""
    orderChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.orderChanged.emit()


class WalletPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.setObjectName("page")
        self.win = window
        tr = window.tr
        self.cards = []
        self.details_shown = False   # one switch for all hidden data of the selected card

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- sidebar
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(340)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(12, 14, 12, 10)
        sl.setSpacing(10)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("search"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.populate)
        top.addWidget(self.search)
        add = QPushButton("+")
        add.setObjectName("primary")
        add.setToolTip(tr("add_card") + " (Ctrl+N)")
        add.setFixedWidth(40)
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.clicked.connect(self.add_card)
        top.addWidget(add)
        sl.addLayout(top)

        # sort mode: bank A-Z (default), card name A-Z, or the user's own order
        self.view = self.win.vault.get_view()
        if self.view.get("sort") not in SORT_MODES:
            self.view["sort"] = "bank"
        self.sort_box = QComboBox()
        for mode in SORT_MODES:
            self.sort_box.addItem(tr(f"sort_{mode}"), mode)
        self.sort_box.setCurrentIndex(SORT_MODES.index(self.view["sort"]))
        self.sort_box.currentIndexChanged.connect(self.on_sort_changed)
        sl.addWidget(self.sort_box)

        self.list = CardList()
        self.list.orderChanged.connect(self.on_order_changed)
        self.list.setItemDelegate(CardItemDelegate(tr, self.list))
        self.list.setMouseTracking(True)
        self.list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list.currentItemChanged.connect(self.on_selection_changed)
        self.list.itemDoubleClicked.connect(lambda *_: self.edit_card())
        sl.addWidget(self.list, 1)
        self.count = QLabel()
        self.count.setObjectName("muted")
        sl.addWidget(self.count)
        self.hint = QLabel()
        self.hint.setObjectName("muted")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("font-size: 8.5pt;")
        sl.addWidget(self.hint)
        root.addWidget(side)

        # ---- detail
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        root.addWidget(self.scroll, 1)

        # hide shown details automatically after a period of inactivity
        self.hide_timer = QTimer(self)
        self.hide_timer.setInterval(1000)
        self.hide_timer.timeout.connect(self.check_auto_hide)

        self.reload()

    # data
    def reload(self, select_id=None):
        self.cards = self.win.vault.list_cards()
        for c in self.cards:  # cards from v1.0: the bank was free text
            bid = card_bank_id(c)
            c["bank_id"] = bid
            if bid and bid != OTHER_BANK_ID:
                c["bank"] = bank(bid)["name"]
        self.cards = sort_cards(self.cards, self.view["sort"], self.view.get("order"))
        self.populate(select_id=select_id)

    def save_view(self):
        ids = {c["id"] for c in self.cards}
        self.view["order"] = [cid for cid in self.view.get("order", []) if cid in ids]
        if self.win.vault.unlocked:
            self.win.vault.set_view(self.view)

    def on_sort_changed(self, *_):
        mode = self.sort_box.currentData()
        if mode == "custom" and not self.view.get("order"):
            # first switch to "my order": start from what is on screen now
            self.view["order"] = [c["id"] for c in self.cards]
        self.view["sort"] = mode
        self.save_view()
        self.cards = sort_cards(self.cards, mode, self.view.get("order"))
        self.populate()

    def on_order_changed(self):
        """A card was dragged: the order shown becomes the user's custom order."""
        ids = [self.list.item(i).data(Qt.ItemDataRole.UserRole)["id"] for i in range(self.list.count())]
        self.view["order"] = ids
        self.view["sort"] = "custom"
        self.sort_box.blockSignals(True)
        self.sort_box.setCurrentIndex(SORT_MODES.index("custom"))
        self.sort_box.blockSignals(False)
        self.save_view()
        self.cards = sort_cards(self.cards, "custom", ids)
        self.update_hint()

    def update_hint(self):
        searching = bool(self.search.text().strip())
        self.list.setDragEnabled(not searching)   # reordering a filtered list would be ambiguous
        self.hint.setText(self.win.tr("drag_hint_search" if searching else "drag_hint"))

    def populate(self, *_, select_id=None):
        if select_id is None and self.list.currentItem():
            select_id = (self.list.currentItem().data(Qt.ItemDataRole.UserRole) or {}).get("id")
        q = self.search.text().strip().lower()
        self.list.blockSignals(True)
        self.list.clear()
        sel_row = 0
        for c in self.cards:
            hay = " ".join([c.get("label", ""), c.get("bank", ""), c.get("holder", ""),
                            detect_brand(c.get("number", "")), c.get("number", "")[-4:]]).lower()
            if q and q not in hay:
                continue
            it = QListWidgetItem()
            it.setData(Qt.ItemDataRole.UserRole, c)
            self.list.addItem(it)
            if c["id"] == select_id:
                sel_row = self.list.count() - 1
        self.list.blockSignals(False)
        if self.list.count():
            self.list.setCurrentRow(sel_row)
        self.count.setText(self.win.tr("cards_count", n=len(self.cards)))
        self.update_hint()
        self.show_details()

    def current(self):
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    # details
    def show_details(self):
        tr = self.win.tr
        card = self.current()
        w = QWidget()
        w.setObjectName("page")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 28, 36, 28)
        lay.setSpacing(16)
        if not card:
            msg = QLabel(tr("no_cards") if not self.cards else tr("select_card"))
            msg.setObjectName("muted")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet("font-size: 12pt;")
            lay.addStretch()
            lay.addWidget(msg)
            if not self.cards:
                b = QPushButton(tr("add_card"))
                b.setObjectName("primary")
                b.clicked.connect(self.add_card)
                h = QHBoxLayout()
                h.addStretch()
                h.addWidget(b)
                h.addStretch()
                lay.addLayout(h)
            lay.addStretch()
            self.scroll.setWidget(w)
            return

        head = QHBoxLayout()
        title = QLabel(card.get("label", ""))
        title.setObjectName("title")
        head.addWidget(title, 1)
        status = expiry_status(card.get("expiry", ""))
        if status in ("expired", "soon"):
            col = C_DANGER if status == "expired" else C_WARN
            badge = QLabel(tr("expired" if status == "expired" else "expires_soon"))
            badge.setStyleSheet(f"color: {col}; font-size: 9pt; font-weight: 600; padding: 0 8px;")
            head.addWidget(badge)
        # one button shows / hides every hidden detail of this card (placed before Edit)
        rb = QPushButton(tr("hide_details") if self.details_shown else tr("show_details"))
        if not self.details_shown:
            rb.setObjectName("primary")
        rb.setCursor(Qt.CursorShape.PointingHandCursor)
        rb.clicked.connect(self.toggle_details)
        head.addWidget(rb)
        eb = QPushButton(tr("edit"))
        eb.clicked.connect(self.edit_card)
        db = QPushButton(tr("delete_card"))
        db.setObjectName("danger")
        db.clicked.connect(self.delete_card)
        head.addWidget(eb)
        head.addWidget(db)
        lay.addLayout(head)

        view = CardView(tr)
        view.set_card(card, reveal=self.details_shown)
        view.setMaximumWidth(420)
        lay.addWidget(view, 0, Qt.AlignmentFlag.AlignLeft)

        if self.details_shown:
            note = QLabel(tr("auto_hide_note", s=DETAILS_AUTO_HIDE_SECONDS))
            note.setObjectName("muted")
            lay.addWidget(note)

        box = QFrame()
        box.setObjectName("box")
        grid = QGridLayout(box)
        grid.setContentsMargins(20, 16, 20, 16)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(1, 1)
        n = card.get("number", "")
        rows = [
            ("holder", card.get("holder", ""), False, None),
            ("number", format_number(n), True, mask_number(n)),
            ("expiry", card.get("expiry", ""), False, None),
            ("cvv", card.get("cvv", ""), True, "•••"),
            ("pin", card.get("pin", ""), True, "••••"),
            ("bank", card.get("bank", ""), False, None),
            ("brand", detect_brand(n), False, None),
        ]
        r = 0
        for key, value, secret, masked in rows:
            if not value:
                continue
            nl = QLabel(tr(key))
            nl.setObjectName("fieldName")
            grid.addWidget(nl, r, 0)
            shown = value if (not secret or self.details_shown) else masked
            vl = QLabel(shown)
            vl.setObjectName("fieldValue")
            if key in ("number", "cvv", "pin", "expiry"):
                vl.setFont(mono_font(11.5))
            grid.addWidget(vl, r, 1)
            # Copy works even while the details are hidden (the value is never shown on screen).
            # The PIN has no Copy button: it is only there to remind you of it.
            if key in ("holder", "number", "expiry", "cvv"):
                cb = QPushButton(tr("copy"))
                cb.setObjectName("small")
                copy_value = digits(value) if key == "number" else value
                cb.clicked.connect(lambda _=False, v=copy_value: self.win.copy_secret(v))
                grid.addWidget(cb, r, 2)
            r += 1
        if card.get("notes"):
            nl = QLabel(tr("notes"))
            nl.setObjectName("fieldName")
            grid.addWidget(nl, r, 0, Qt.AlignmentFlag.AlignTop)
            nv = QLabel(card["notes"])
            nv.setWordWrap(True)
            nv.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(nv, r, 1, 1, 2)
        lay.addWidget(box)
        lay.addStretch()
        self.scroll.setWidget(w)

    def on_selection_changed(self, *_):
        # moving to another card always starts with its details hidden
        self.hide_details()

    def toggle_details(self):
        if self.details_shown:
            self.hide_details()
        else:
            self.details_shown = True
            self.win.activity.last = time.monotonic()
            self.hide_timer.start()
            self.show_details()

    def hide_details(self):
        self.details_shown = False
        self.hide_timer.stop()
        self.show_details()

    def check_auto_hide(self):
        if self.details_shown and time.monotonic() - self.win.activity.last >= DETAILS_AUTO_HIDE_SECONDS:
            self.hide_details()
            self.win.statusBar().showMessage(self.win.tr("details_auto_hidden"), 5000)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Delete and self.current():
            self.delete_card()
        else:
            super().keyPressEvent(e)

    # actions
    def add_card(self):
        dlg = CardDialog(self.win.tr, parent=self.win)
        if dlg.exec() == QDialog.DialogCode.Accepted and self.win.vault.unlocked:
            cid = self.win.vault.save_card(dlg.result_card)
            self.search.clear()
            self.details_shown = False
            self.reload(select_id=cid)

    def edit_card(self):
        card = self.current()
        if not card:
            return
        dlg = CardDialog(self.win.tr, card, parent=self.win)
        if dlg.exec() == QDialog.DialogCode.Accepted and self.win.vault.unlocked:
            cid = self.win.vault.save_card(dlg.result_card)
            self.reload(select_id=cid)

    def delete_card(self):
        card = self.current()
        if not card:
            return
        tr = self.win.tr
        if ask(self.win, tr, tr("confirm_delete", name=card.get("label", ""))) and self.win.vault.unlocked:
            self.win.vault.delete_card(card["id"])
            self.details_shown = False
            self.reload()


# ---------------------------------------------------------------- expiry alert

def expiring_cards(cards, soon_days=EXPIRY_WARNING_DAYS):
    out = [c for c in cards if expiry_status(c.get("expiry", ""), soon_days) in ("expired", "soon")]
    out.sort(key=lambda c: days_left(c.get("expiry", "")))
    return out


class ExpiryAlertDialog(QDialog):
    def __init__(self, tr, cards, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("expiry_alert_title"))
        self.setMinimumWidth(640)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(14)

        head = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning).pixmap(40, 40))
        head.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        texts = QVBoxLayout()
        title = QLabel(tr("expiry_alert_title"))
        title.setStyleSheet("font-size: 15pt; font-weight: 600;")
        texts.addWidget(title)
        intro = QLabel(tr("expiry_alert_intro"))
        intro.setWordWrap(True)
        intro.setObjectName("muted")
        texts.addWidget(intro)
        head.addLayout(texts, 1)
        lay.addLayout(head)

        box = QFrame()
        box.setObjectName("box")
        grid = QGridLayout(box)
        grid.setContentsMargins(16, 12, 16, 12)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        for r, c in enumerate(cards):
            sw = QLabel()
            sw.setPixmap(bank_swatch(c, tr, 54, 34))
            grid.addWidget(sw, r, 0)
            name = QLabel(f"<b>{_html(c.get('label', ''))}</b><br>"
                          f"<span style='color:{C_MUTED}'>{_html(c.get('bank', ''))}  ·  "
                          f"•••• {digits(c.get('number', ''))[-4:]}</span>")
            grid.addWidget(name, r, 1)
            exp = QLabel(c.get("expiry", ""))
            exp.setFont(mono_font(11))
            grid.addWidget(exp, r, 2)
            left = days_left(c.get("expiry", ""))
            if left < 0:
                txt, col = tr("expired_since"), C_DANGER
            elif left == 0:
                txt, col = tr("expires_today"), C_DANGER
            else:
                txt, col = tr("days_left", n=left), C_WARN
            st = QLabel(txt)
            st.setStyleSheet(f"color: {col}; font-weight: 600;")
            st.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(st, r, 3)
        lay.addWidget(box)

        btns = QDialogButtonBox()
        ok = btns.addButton(tr("ok"), QDialogButtonBox.ButtonRole.AcceptRole)
        ok.setObjectName("primary")
        ok.setMinimumWidth(100)
        btns.accepted.connect(self.accept)
        lay.addWidget(btns)


class PrivacyDialog(QDialog):
    """Privacy disclaimer: shown on first launch and from the Help menu."""

    def __init__(self, tr, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("privacy_title"))
        self.setMinimumWidth(600)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(14)

        head = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(QIcon(resource_path(os.path.join("assets", "icon.png"))).pixmap(56, 56))
        head.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        texts = QVBoxLayout()
        title = QLabel(tr("privacy_title"))
        title.setStyleSheet("font-size: 16pt; font-weight: 600;")
        title.setWordWrap(True)
        texts.addWidget(title)
        intro = QLabel(tr("privacy_intro"))
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 11pt;")
        texts.addWidget(intro)
        head.addLayout(texts, 1)
        lay.addLayout(head)

        box = QFrame()
        box.setObjectName("box")
        bl = QVBoxLayout(box)
        bl.setContentsMargins(18, 14, 18, 14)
        bl.setSpacing(9)
        for point in tr("privacy_points").split("\n"):
            row = QHBoxLayout()
            check = QLabel("✓")
            check.setStyleSheet("color: #3ccf91; font-weight: 700; font-size: 12pt;")
            check.setFixedWidth(18)
            row.addWidget(check, 0, Qt.AlignmentFlag.AlignTop)
            lbl = QLabel(point)
            lbl.setWordWrap(True)
            row.addWidget(lbl, 1)
            bl.addLayout(row)
        lay.addWidget(box)

        note = QLabel(tr("privacy_cloud_note"))
        note.setWordWrap(True)
        note.setObjectName("muted")
        lay.addWidget(note)

        btns = QDialogButtonBox()
        ok = btns.addButton(tr("privacy_ok"), QDialogButtonBox.ButtonRole.AcceptRole)
        ok.setObjectName("primary")
        ok.setMinimumWidth(140)
        btns.accepted.connect(self.accept)
        lay.addWidget(btns)


def _html(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- activity / main window

class ActivityFilter(QObject):
    EVENTS = {QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress, QEvent.Type.Wheel, QEvent.Type.MouseMove}

    def __init__(self):
        super().__init__()
        self.last = time.monotonic()

    def eventFilter(self, obj, ev):
        if ev.type() in self.EVENTS:
            self.last = time.monotonic()
        return False


class MainWindow(QMainWindow):
    def __init__(self, vault: Vault, settings: dict, activity: ActivityFilter):
        super().__init__()
        self.vault = vault
        self.settings = settings
        self.activity = activity
        self.clip_value = None
        self.wallet_page = None
        self.setWindowIcon(QIcon(resource_path(os.path.join("assets", "icon.png"))))
        self.resize(1100, 700)
        self.setMinimumSize(900, 580)
        self.apply_language()

        self.lock_timer = QTimer(self)
        self.lock_timer.timeout.connect(self.check_idle)
        self.lock_timer.start(5000)

    # language
    def current_lang(self):
        pref = self.settings.get("language", "auto")
        return detect_system_language() if pref == "auto" else pref

    def apply_language(self):
        self.tr = Translator(self.current_lang())
        install_qt_translator(self.tr.lang)
        self.build_ui()

    def set_language(self, code):
        self.settings["language"] = code
        save_settings(self.settings)
        self.apply_language()

    # ui
    def build_ui(self):
        tr = self.tr
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION} — {copyright_short()}")
        mb = self.menuBar()
        mb.clear()
        m_file = mb.addMenu(tr("menu_file"))
        self.act_add = QAction(tr("add_card"), self, shortcut=QKeySequence.StandardKey.New)
        self.act_add.triggered.connect(lambda: self.wallet_page and self.wallet_page.add_card())
        m_file.addAction(self.act_add)
        self.act_expiry = QAction(tr("check_expiry"), self)
        self.act_expiry.triggered.connect(lambda: self.show_expiry_alert(manual=True))
        m_file.addAction(self.act_expiry)
        m_file.addSeparator()
        self.act_export = QAction(tr("export_vault"), self)
        self.act_export.triggered.connect(self.export_vault)
        m_file.addAction(self.act_export)
        self.act_move = QAction(tr("move_vault"), self)
        self.act_move.triggered.connect(self.move_vault)
        m_file.addAction(self.act_move)
        self.act_open = QAction(tr("open_existing"), self, shortcut=QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self.open_vault)
        m_file.addAction(self.act_open)
        m_file.addSeparator()
        self.act_lock = QAction(tr("lock"), self, shortcut=QKeySequence("Ctrl+L"))
        self.act_lock.triggered.connect(lambda: self.lock())
        m_file.addAction(self.act_lock)
        act_exit = QAction(tr("exit"), self, shortcut=QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        m_file.addAction(act_exit)

        m_set = mb.addMenu(tr("menu_settings"))
        self.act_pw = QAction(tr("change_password"), self)
        self.act_pw.triggered.connect(self.change_password)
        m_set.addAction(self.act_pw)
        m_lang = m_set.addMenu(tr("language"))
        group = QActionGroup(self)
        pref = self.settings.get("language", "auto")
        sys_lang = detect_system_language()
        a = QAction(f"{tr('system_language')} ({T[sys_lang]['lang_name']})", self, checkable=True)
        a.setChecked(pref == "auto")
        a.triggered.connect(lambda: self.set_language("auto"))
        group.addAction(a)
        m_lang.addAction(a)
        m_lang.addSeparator()
        for code in LANGUAGES:
            a = QAction(T[code]["lang_name"], self, checkable=True)
            a.setChecked(pref == code)
            a.triggered.connect(lambda _=False, c=code: self.set_language(c))
            group.addAction(a)
            m_lang.addAction(a)

        m_help = mb.addMenu(tr("menu_help"))
        act_priv = QAction(tr("privacy_menu"), self)
        act_priv.triggered.connect(self.show_privacy)
        m_help.addAction(act_priv)
        act_about = QAction(tr("about"), self)
        act_about.triggered.connect(self.about)
        m_help.addAction(act_about)

        # status bar: left = version + database path; right = offline badge + copyright
        sb = self.statusBar()
        if not hasattr(self, "info_label"):
            self.info_label = QLabel()
            sb.addWidget(self.info_label)
        if not hasattr(self, "offline_label"):
            self.offline_label = QLabel()
            self.offline_label.setObjectName("offline")
            sb.addPermanentWidget(self.offline_label)
        if netguard.is_active():
            self.offline_label.setText("● " + tr("status_offline") + "   ")
            self.offline_label.setToolTip(tr("status_offline_tip"))
        else:
            self.offline_label.setText("")
        if not hasattr(self, "copyright_label"):
            self.copyright_label = QLabel()
            sb.addPermanentWidget(self.copyright_label)
        self.copyright_label.setText(copyright_line() + "   ")
        self.update_status_bar()

        if self.vault.unlocked:
            self.show_wallet(check_expiry=False)
        else:
            self.show_login()

    def set_page(self, page):
        old = self.centralWidget()
        self.setCentralWidget(page)
        if old is not None:
            old.deleteLater()

    def update_actions(self):
        on = self.vault.unlocked
        for a in (self.act_add, self.act_export, self.act_move, self.act_lock, self.act_pw, self.act_expiry):
            a.setEnabled(on)

    def update_status_bar(self):
        if not hasattr(self, "info_label"):
            return
        path = self.vault.path if self.vault else default_db_path()
        self.info_label.setText(
            f"  {self.tr('status_version', v=APP_VERSION)}   ·   {self.tr('status_db', path=path)}  ")
        self.info_label.setToolTip(path)

    def create_wallet(self, path, password):
        """Creates the wallet at the path chosen by the user."""
        path = os.path.abspath(path)
        if path != os.path.abspath(self.vault.path):
            # replace the empty default file with the chosen one
            old = self.vault.path
            was_empty = not self.vault.is_initialized()
            self.vault.close()
            if was_empty:
                try:
                    os.remove(old)
                except OSError:
                    pass
            self.vault = Vault(path)
        self.vault.create(password)
        self.settings["db_path"] = path
        save_settings(self.settings)
        self.update_status_bar()

    def show_login(self):
        self.wallet_page = None
        self.set_page(LoginPage(self, create_mode=not self.vault.is_initialized()))
        self.update_actions()
        self.update_status_bar()

    def show_wallet(self, check_expiry=True):
        self.activity.last = time.monotonic()
        self.wallet_page = WalletPage(self)
        self.set_page(self.wallet_page)
        self.update_actions()
        self.update_status_bar()
        if check_expiry:
            QTimer.singleShot(400, self.show_expiry_alert)

    def show_expiry_alert(self, manual=False):
        if not self.vault.unlocked or not self.wallet_page:
            return
        cards = expiring_cards(self.wallet_page.cards)
        if cards:
            ExpiryAlertDialog(self.tr, cards, self).exec()
        elif manual:
            inform(self, self.tr, self.tr("no_expiring", n=EXPIRY_WARNING_DAYS))

    # security
    def copy_secret(self, value):
        QGuiApplication.clipboard().setText(value)
        self.clip_value = value
        self.statusBar().showMessage(self.tr("copied", s=CLIPBOARD_CLEAR_SECONDS), 4000)
        QTimer.singleShot(CLIPBOARD_CLEAR_SECONDS * 1000, lambda v=value: self.clear_clipboard(v))

    def clear_clipboard(self, value=None):
        cb = QGuiApplication.clipboard()
        target = value if value is not None else self.clip_value
        if target and cb.text() == target:
            cb.clear()
        if value is None or value == self.clip_value:
            self.clip_value = None

    def check_idle(self):
        if self.vault.unlocked and time.monotonic() - self.activity.last > AUTO_LOCK_SECONDS:
            self.lock(auto=True)

    def lock(self, auto=False):
        if not self.vault.unlocked:
            return
        for w in QApplication.topLevelWidgets():
            if isinstance(w, QDialog) and w.isVisible():
                w.reject()
        self.vault.lock()
        self.clear_clipboard()
        self.show_login()
        if auto:
            self.statusBar().showMessage(self.tr("locked_auto"))

    def change_password(self):
        if not self.vault.unlocked:
            return
        dlg = ChangePasswordDialog(self.tr, self)
        while dlg.exec() == QDialog.DialogCode.Accepted:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                self.vault.change_password(dlg.old.text(), dlg.new.text())
            except WrongPassword:
                QApplication.restoreOverrideCursor()
                dlg.error.setText(self.tr("wrong_password"))
                continue
            QApplication.restoreOverrideCursor()
            inform(self, self.tr, self.tr("password_changed"))
            break

    def export_vault(self):
        """Exports a copy of the database (still encrypted); the original stays in place."""
        if not self.vault.unlocked:
            return
        name = f"CardVault-export-{datetime.now():%Y%m%d-%H%M}.cvw"
        path = pick_vault_file(self, self.tr, self.tr("export_db_title"),
                               os.path.join(home_dir(), name), save=True)
        if not path:
            return
        try:
            self.vault.export(path)
            inform(self, self.tr, self.tr("backup_done", path=path))
        except Exception as e:
            QMessageBox.critical(self, self.tr("error"), str(e))

    def move_vault(self):
        """Moves the database file to a new location and remembers it."""
        if not self.vault.unlocked:
            return
        current = os.path.basename(self.vault.path) or "wallet.cvw"
        start = os.path.join(home_dir(), current)
        path = pick_vault_file(self, self.tr, self.tr("move_db_title"), start, save=True)
        if not path:
            return
        if os.path.abspath(path) == os.path.abspath(self.vault.path):
            inform(self, self.tr, self.tr("same_location"))
            return
        try:
            self.vault.relocate(path)
            self.settings["db_path"] = os.path.abspath(path)
            save_settings(self.settings)
            self.update_status_bar()
            inform(self, self.tr, self.tr("vault_moved", path=path))
        except Exception as e:
            QMessageBox.critical(self, self.tr("error"), str(e))

    def open_vault(self):
        """Opens an existing CardVault file (e.g. after reinstalling, or from a USB stick)."""
        tr = self.tr
        start = os.path.dirname(self.vault.path) if self.vault else home_dir()
        path = pick_vault_file(self, tr, tr("open_db_title"), start, save=False)
        if not path:
            return
        if os.path.abspath(path) == os.path.abspath(self.vault.path):
            return
        if not Vault.is_vault_file(path):
            QMessageBox.warning(self, tr("error"), tr("not_a_vault"))
            return
        if self.vault.unlocked:
            self.lock()
        old = self.vault.path
        was_empty = not self.vault.is_initialized()
        self.vault.close()
        if was_empty:  # the empty file created at startup is no longer needed
            try:
                os.remove(old)
                os.rmdir(os.path.dirname(old))
            except OSError:
                pass
        self.vault = Vault(path)
        self.settings["db_path"] = path
        save_settings(self.settings)
        self.show_login()

    def show_privacy(self):
        PrivacyDialog(self.tr, self).exec()

    def maybe_show_privacy(self):
        if not self.settings.get("privacy_ack"):
            self.show_privacy()
            self.settings["privacy_ack"] = True
            save_settings(self.settings)

    def about(self):
        tr = self.tr
        box = QMessageBox(self)
        box.setWindowTitle(tr("about"))
        box.setIconPixmap(self.windowIcon().pixmap(64, 64))
        box.setText(f"<h3>{APP_NAME}</h3>{tr('version')} {APP_VERSION}")
        box.setInformativeText(
            f"{tr('about_text')}\n\n{tr('db_location')}: {self.vault.path}\n\n"
            f"{copyright_line()}")
        box.exec()

    def closeEvent(self, e):
        self.clear_clipboard()
        self.vault.close()
        super().closeEvent(e)


def run():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GabrielDobre.CardVault.1")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(AUTHOR)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setWindowIcon(QIcon(resource_path(os.path.join("assets", "icon.png"))))
    activity = ActivityFilter()
    app.installEventFilter(activity)
    netguard.install()  # idempotent; main.py already enables it before any other import
    settings = load_settings()
    path = settings.get("db_path")
    if not path or is_network_path(path) or not os.path.isfile(path):
        path = default_db_path()
    vault = Vault(path)
    win = MainWindow(vault, settings, activity)
    win.show()
    QTimer.singleShot(250, win.maybe_show_privacy)
    return app.exec()
