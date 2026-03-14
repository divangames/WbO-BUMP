import os
import sys
import json
import time  # Для расчёта времени экспорта
from pathlib import Path
import tempfile  # Для временных файлов предпросмотра
import subprocess
import shutil

import numpy as np  # Для математики наложения «Экран»
import cv2  # Для работы с видео и изображениями
from PIL import Image  # Для корректного чтения WEBP и других форматов
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QFileDialog,
    QLabel,
    QSlider,
    QMessageBox,
    QCheckBox,
    QComboBox,
    QAbstractItemView,
    QDialog,
    QProgressBar,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QSizeGrip,
    QSplashScreen,
)
from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QPen,
    QColor,
    QImage,
    QIcon,
    QGuiApplication,
    QAction,
    QKeySequence,
    QShortcut,
    QFont,
    QFontDatabase,
)
from PySide6.QtCore import Qt, QSize, QUrl, QTimer, QByteArray, QCoreApplication, QProcess, QSettings

try:
    from PySide6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from export_settings_dialog import ExportSettingsDialog
from ui_common import DialogTitleBar


# ВАЖНО: комментарии всегда на русском, не удалять при доработках

# Версия приложения (для статус-бара, «О программе» и сплэша)
APP_VERSION = "0.1.2.2"

# Базовая папка приложения:
# - при запуске из Python — корень проекта (рядом с main.py);
# - при запуске из exe (PyInstaller) — папка, где лежит exe.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

# Пути к звуковым файлам (папка Assets/sound, форматы mp3)
SOUND_EXPORT_READY = BASE_DIR / "Assets" / "sound" / "ok.mp3"
SOUND_EXPORT_ERROR = BASE_DIR / "Assets" / "sound" / "error.mp3"
SOUND_CLICK = BASE_DIR / "Assets" / "sound" / "click.mp3"
SOUND_PORTFOLIO = BASE_DIR / "Assets" / "sound" / "portfolio.mp3"
SOUND_OPEN = BASE_DIR / "Assets" / "sound" / "open.mp3"
SOUND_DIALOG = BASE_DIR / "Assets" / "sound" / "dialog.mp3"
SOUND_SPLASH_BANKA = BASE_DIR / "Assets" / "sound" / "banka_01.mp3"

ICONS_DIR = BASE_DIR / "Assets" / "icons"
FONTS_DIR = BASE_DIR / "Assets" / "fonts"
APP_ICON_PATH = BASE_DIR / "Assets" / "images" / "faicon.png"

# Семейства шрифтов после загрузки в main() (для сплэша и шапки)
_google_sans_family = ""
_unbounded_family = ""


def load_phosphor_icon(name: str, size: int = 20, color: str = "#e0e0e0") -> QIcon:
    """
    Загрузка иконки из папки Assets/icons.

    Приоритет:
    1) PNG:  Assets/icons/{name}.png
    2) SVG:  Assets/icons/{name}.svg

    Масштабированием занимается сам Qt через setIconSize, поэтому здесь просто
    возвращаем QIcon от найденного файла без дополнительного рендера, чтобы
    избежать артефактов и «микроскопических» иконок.
    """
    # Сначала пробуем PNG — самый надёжный вариант
    png_path = ICONS_DIR / f"{name}.png"
    if png_path.exists():
        icon = QIcon(str(png_path))
        if not icon.isNull():
            return icon

    # Затем SVG, если он есть
    svg_path = ICONS_DIR / f"{name}.svg"
    if svg_path.exists():
        icon = QIcon(str(svg_path))
        if not icon.isNull():
            return icon

    return QIcon()


# Единая тёмная тема: один фон, одна рамка, аккуратный вид
APP_STYLESHEET = """
    QMainWindow, QWidget {
        background-color: #14181c;
        color: #e6edf3;
        font-size: 13px;
    }
    /* Шапка окна: оболочка и контур в наших цветах */
    #titleBar {
        background-color: #1a1f26;
        border: 1px solid #2a3038;
        border-bottom: none;
        border-top: 2px solid #3d454f;
        border-radius: 8px 8px 0 0;
    }
    #mainContainer {
        background-color: #14181c;
        border: 1px solid #2a3038;
        border-top: none;
        border-bottom: none;
        border-radius: 0;
    }
    #titleButton,
    #titleCloseButton {
        background: transparent;
        border: none;
        color: #9ca3af;
        padding: 0;
        font-size: 12px;
    }
    #titleButton:hover {
        background: rgba(42, 48, 56, 0.8);
        color: #e5e7eb;
    }
    #titleCloseButton:hover {
        background: #b91c1c;
        color: #ffffff;
    }
    /* Нижняя строка статуса (контур сверху в наших цветах) */
    #statusBar {
        background-color: #1a1f26;
        border: 1px solid #2a3038;
        border-top: 2px solid #3d454f;
        border-radius: 0 0 8px 8px;
        padding: 4px 10px;
        color: #8b949e;
        font-size: 12px;
    }
    #statusBar QLabel {
        color: #8b949e;
        font-size: 12px;
        background: transparent;
    }
    #statusState {
        color: #b1b8c2;
    }
    QMenuBar {
        background-color: #1a1f26;
        color: #8b949e;
        padding: 2px 0;
    }
    QMenuBar::item {
        padding: 4px 10px;
        border-radius: 4px;
    }
    QMenuBar::item:selected {
        background-color: #2d3542;
        color: #e6edf3;
    }
    QMenu {
        background-color: #1a1f26;
        color: #e6edf3;
        border: 1px solid #2a3038;
        border-radius: 8px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 12px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background-color: #2d3542;
        color: #e6edf3;
    }
    QLabel {
        color: #e6edf3;
        font-size: 13px;
        background: transparent;
    }
    QLabel#sectionLabel {
        color: #b1b8c2;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    QLabel#stepHint {
        color: #8b949e;
        font-size: 12px;
    }
    QPushButton {
        background: transparent;
        color: #e6edf3;
        border: 1px solid #2a3038;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 13px;
    }
    QPushButton:hover {
        background: rgba(42, 48, 56, 0.6);
        border-color: #3d454f;
    }
    QPushButton:pressed {
        background: rgba(30, 35, 41, 0.9);
    }
    QPushButton:disabled {
        color: #4b5563;
        background: rgba(30, 35, 41, 0.5);
        border-color: #2a3038;
        opacity: 0.85;
    }
    QPushButton[class="primary"] {
        background: transparent;
        border: 1px solid #238636;
        color: #3fb950;
        font-weight: 600;
    }
    QPushButton[class="primary"]:hover {
        background: rgba(35, 134, 54, 0.2);
        border-color: #2ea043;
        color: #56d364;
    }
    QPushButton[class="danger"] {
        background: transparent;
        border: 1px solid #da3633;
        color: #f85149;
    }
    QPushButton[class="danger"]:hover {
        background: rgba(218, 54, 51, 0.2);
        border-color: #f85149;
        color: #ff7b72;
    }
    QPushButton[class="danger"]:disabled,
    QPushButton[class="iconOnly danger"]:disabled {
        border-color: #2a3038;
        color: #4b5563;
    }
    QPushButton[class="iconOnly danger"] {
        background: transparent;
        border: 1px solid #da3633;
        color: #f85149;
    }
    QPushButton[class="iconOnly danger"]:hover {
        background: rgba(218, 54, 51, 0.2);
        border-color: #f85149;
        color: #ff7b72;
    }
    QPushButton[class="iconOnly accent"] {
        background: transparent;
        border: 1px solid #388bfd;
        color: #58a6ff;
        padding: 8px;
        min-width: 32px;
    }
    QPushButton[class="iconOnly accent"]:hover {
        background: rgba(56, 139, 253, 0.2);
        border-color: #58a6ff;
        color: #79c0ff;
    }
    QPushButton[class="iconOnly accent"]:disabled {
        border-color: #2a3038;
        color: #4b5563;
    }
    QPushButton[class="accent"] {
        background: transparent;
        border: 1px solid #388bfd;
        color: #58a6ff;
    }
    QPushButton[class="accent"]:hover {
        background: rgba(56, 139, 253, 0.2);
        border-color: #58a6ff;
        color: #79c0ff;
    }
    QPushButton[class="iconOnly"] {
        padding: 8px;
        min-width: 32px;
    }
    QListWidget {
        background: transparent;
        border: 1px solid #2a3038;
        border-radius: 8px;
        padding: 2px;
        color: #e6edf3;
        font-size: 13px;
    }
    QListWidget::item {
        padding: 0 2px;
        border-radius: 2px;
        background: transparent;
    }
    QListWidget[listMode="true"]::item {
        height: 40px;
        max-height: 40px;
        padding: 0 4px;
        margin: 0;
    }
    QListWidget::item:selected {
        background: #2d3542;
        color: #e6edf3;
    }
    QListWidget::item:hover:!selected {
        background: rgba(42, 48, 56, 0.5);
    }
    /* Ползунки в стиле приложения: мягкие, без яркого синего */
    QSlider::groove:horizontal {
        height: 6px;
        background: #1e2329;
        border: none;
        border-radius: 3px;
    }
    QSlider::sub-page:horizontal {
        background: #3d454f;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        width: 16px;
        height: 16px;
        margin: -5px 0;
        background: #5c636e;
        border: none;
        border-radius: 8px;
    }
    QSlider::handle:horizontal:hover {
        background: #6e7681;
    }
    QSlider::handle:horizontal:pressed {
        background: #8b949e;
    }
    QSlider#curveSlider::groove:horizontal {
        height: 4px;
    }
    QSlider#curveSlider::handle:horizontal {
        width: 12px;
        height: 12px;
        margin: -4px 0;
    }
    QCheckBox {
        color: #e6edf3;
        spacing: 8px;
        font-size: 13px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #2a3038;
        border-radius: 4px;
        background: transparent;
    }
    QCheckBox::indicator:checked {
        background: #3d454f;
        border-color: #4d5a6b;
    }
    /* Чекбокс «Один ролик для всех» — явная синяя галочка */
    QCheckBox#singleVideoCheckbox::indicator {
        width: 18px;
        height: 18px;
        border: 1px solid #2a3038;
        border-radius: 4px;
        background: #1e2329;
    }
    QCheckBox#singleVideoCheckbox::indicator:checked {
        background: #2563eb;
        border-color: #3b82f6;
        image: url("{{CHECK_ICON}}");
    }
    /* Таймлайн превью: пусто — тёмный, пройденное — синее, ползунок видим */
    QSlider#previewTimeline::groove:horizontal {
        height: 8px;
        background: #1e2329;
        border: none;
        border-radius: 4px;
    }
    QSlider#previewTimeline::sub-page:horizontal {
        background: #2563eb;
        border-radius: 4px;
    }
    QSlider#previewTimeline::handle:horizontal {
        width: 14px;
        height: 14px;
        margin: -3px 0;
        background: #e6edf3;
        border: 1px solid #8b949e;
        border-radius: 7px;
    }
    QSlider#previewTimeline::handle:horizontal:hover {
        background: #ffffff;
    }
    QComboBox {
        background: transparent;
        color: #e6edf3;
        border: 1px solid #2a3038;
        border-radius: 6px;
        padding: 6px 12px;
        padding-right: 28px;
        font-size: 13px;
        min-height: 32px;
    }
    QComboBox:hover {
        border-color: #3d454f;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: right;
        width: 24px;
        border-left: 1px solid #2a3038;
        border-top-right-radius: 5px;
        border-bottom-right-radius: 5px;
        background: rgba(42, 48, 56, 0.5);
    }
    QComboBox::down-arrow {
        image: url("{{CHEVRON_DOWN}}");
        width: 14px;
        height: 14px;
    }
    QComboBox QAbstractItemView {
        background: #1a1f26;
        color: #e6edf3;
        selection-background-color: #2d3542;
        selection-color: #e6edf3;
        border: 1px solid #2a3038;
        border-radius: 6px;
    }
    QFrame#panel {
        background: transparent;
        border: 1px solid #2a3038;
        border-radius: 8px;
        margin: 2px 0;
        padding: 10px;
    }
    QScrollArea {
        border: none;
        background: transparent;
    }
    QScrollBar:vertical {
        background: #1e2329;
        width: 12px;
        border-radius: 6px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #424a56;
        border-radius: 5px;
        min-height: 24px;
    }
    QScrollBar::handle:vertical:hover {
        background: #5c636e;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }
    QScrollBar:horizontal {
        background: #1e2329;
        height: 12px;
        border-radius: 6px;
        margin: 0;
    }
    QScrollBar::handle:horizontal {
        background: #424a56;
        border-radius: 5px;
        min-width: 24px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #5c636e;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
    }
    #sizeGripIcon {
        color: #6b7280;
        font-size: 14px;
        background: transparent;
    }
    /* Всплывающие подсказки в стиле приложения */
    QToolTip {
        background-color: #1e2329;
        color: #e6edf3;
        border: 1px solid #3d454f;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }
"""

# Общий стиль для диалогов из меню «Помощь» (О программе, Справка, История, Автор)
HELP_DIALOG_STYLE = """
    QDialog { background-color: #16181c; border-radius: 8px; border: 1px solid #2a3038; }
    QLabel { color: #e2e8f0; font-size: 13px; background: transparent; }
    QScrollArea { border: none; background: transparent; }
    QPushButton { background: transparent; color: #e2e8f0; border: 1px solid #475569; border-radius: 4px; padding: 6px 12px; font-size: 13px; }
    QPushButton:hover { background: rgba(71, 85, 105, 0.5); }
"""


def _format_readme_for_display(raw: str) -> str:
    """Убирает markdown-разметку из README для читаемого отображения в диалоге."""
    lines = raw.split("\n")
    result: list[str] = []
    in_code_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if stripped.startswith("## "):
            result.append("")
            result.append(stripped[3:].strip())
            result.append("")
            continue
        if stripped.startswith("# "):
            result.append(stripped[2:].strip())
            result.append("")
            continue
        result.append(line)
    return "\n".join(result).strip()


class SoundPlayer:
    """Простой проигрыватель звуков на базе Qt (поддержка mp3)."""

    _player: QMediaPlayer | None = None
    _audio_output: QAudioOutput | None = None

    @classmethod
    def play(cls, path: Path) -> None:
        # Комментарий: если файла нет — просто выходим без ошибок
        if not path.exists():
            return
        try:
            if cls._player is None:
                cls._player = QMediaPlayer()
                cls._audio_output = QAudioOutput()
                cls._player.setAudioOutput(cls._audio_output)

            # Останавливаем предыдущее воспроизведение и запускаем новое
            cls._player.stop()
            cls._player.setSource(QUrl.fromLocalFile(str(path)))
            if cls._audio_output is not None:
                cls._audio_output.setVolume(1.0)
            cls._player.play()
        except Exception:
            # Нам важно не уронить приложение, даже если аудио не воспроизвелось
            pass

    @classmethod
    def stop(cls) -> None:
        """Остановить текущее воспроизведение, если оно есть."""
        try:
            if cls._player is not None:
                cls._player.stop()
        except Exception:
            pass


CONFIG_FILE = "wbo_config.json"


def load_config() -> dict:
    """Загрузка конфигурации приложения (последний путь экспорта и т.п.)."""
    # Комментарии на русском: если файл не найден, возвращаем конфиг по умолчанию
    if not os.path.exists(CONFIG_FILE):
        return {
            "last_export_path": str(Path.cwd()),
            "last_images_path": str(Path("Assets/demo").resolve()),
            "last_video_path": str(Path("Assets/video").resolve()),
            # Качество рендера: quality / balanced / fast
            "render_preset": "balanced",
            # Настройки экспорта (сохраняются между запусками)
            # codec: h264, mpeg4 (по умолчанию h264)
            "export_codec": "h264",
            # size: "900x1200" или "819x1080" (строка, чтобы было проще хранить)
            "export_size": "900x1200",
            # целевой FPS экспорта: 24 / 30 / 60
            "export_fps": 60,
        }
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # Если не удалось прочитать конфиг — используем значения по умолчанию
        data = {}
    data.setdefault("last_export_path", str(Path.cwd()))
    data.setdefault("last_images_path", str(Path("Assets/demo").resolve()))
    data.setdefault("last_video_path", str(Path("Assets/video").resolve()))
    data.setdefault("render_preset", "balanced")
    data.setdefault("export_codec", "h264")
    data.setdefault("export_size", "900x1200")
    data.setdefault("export_fps", 60)
    return data


def save_config(data: dict) -> None:
    """Сохранение конфигурации приложения."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        # Нам важно не падать, если конфиг не сохранился
        pass


class ImageItemData:
    """Модель данных для одной карточки (изображения)."""

    def __init__(self, image_path: str):
        # Путь к изображению карточки
        self.image_path: str = image_path
        # Индивидуальное видео для наложения (если None — используется общее)
        self.video_path: str | None = None
        # Кривая: три точки (тени / средние / света), каждая 0–255 (выход в этой точке)
        # Входные позиции фиксированы: 64, 128, 192. Концы (0,0) и (255,255) зафиксированы.
        self.curve_shadows: int = 64
        self.curve_midtones: int = 128
        self.curve_highlights: int = 192


class CurvePreviewLabel(QLabel):
    """Превью графика кривой с возможностью изменения точек по клику/перетаскиванию."""

    def __init__(self, parent: "MainWindow", size: int = 128) -> None:
        super().__init__(parent)
        self._main = parent
        self._size = size
        self._margin = 14
        self.setFixedSize(size, size)
        self.setStyleSheet(
            "background: transparent; border: 1px solid #30363d; border-radius: 6px;"
        )
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self.setToolTip("Клик или перетаскивание по графику меняет точку (тени / средние / света)")

    def _widget_to_curve(self, x: int, y: int) -> tuple[int, int]:
        """Преобразование координат виджета в (x_in 0–255, y_out 0–255)."""
        m = self._margin
        g = self._size - 2 * m
        if g <= 0:
            return 128, 128
        x_in = int(255 * (x - m) / g)
        y_out = int(255 * (m + g - y) / g)
        return max(0, min(255, x_in)), max(0, min(255, y_out))

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self._main is not None:
            x_in, y_out = self._widget_to_curve(event.position().x(), event.position().y())
            self._main._on_curve_preview_clicked(x_in, y_out)

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        if event.buttons() & Qt.MouseButton.LeftButton and self._main is not None:
            x_in, y_out = self._widget_to_curve(event.position().x(), event.position().y())
            self._main._on_curve_preview_clicked(x_in, y_out)


class ImageListWidget(QListWidget):
    """Кастомный список карточек, поддерживающий drag & drop файлов."""

    def __init__(self, owner: "MainWindow") -> None:
        # owner — главное окно, которому передаём список добавленных файлов
        super().__init__(owner)
        self.owner = owner
        # Разрешаем перетаскивание файлов из проводника
        self.setAcceptDrops(True)
        # Режим drop-only: внутренние перетаскивания нас не интересуют
        self.setDragDropMode(QAbstractItemView.DropOnly)

    def dragEnterEvent(self, event) -> None:
        """Разрешаем drag, если в данных есть файлы."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        """Обработка перемещения drag-события (оставляем простую реализацию)."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        """Добавление изображений, перетащенных в окно карточек."""
        urls = event.mimeData().urls()
        file_paths: list[str] = []
        for url in urls:
            local_path = url.toLocalFile()
            if local_path:
                file_paths.append(local_path)

        if file_paths:
            # Передаём список файлов в главное окно для добавления карточек
            self.owner.add_images_from_files(file_paths)
        event.acceptProposedAction()

    def keyPressEvent(self, event) -> None:
        """Обработка нажатия клавиш в списке карточек."""
        if event.key() == Qt.Key_Delete and self.owner is not None:
            # Удаляем выбранные карточки через метод главного окна
            self.owner.on_delete_selected_clicked()
            return
        super().keyPressEvent(event)


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self) -> None:
        super().__init__()

        # Стандартная оболочка окна Windows (рамка и заголовок) —
        # оставляем поведение Windows, а внутри настраиваем оформление.
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self._drag_active = False
        self._drag_pos = None

        # Конфигурация (пути и т.п.)
        self.config = load_config()
        # Режим рендера: "quality" | "balanced" | "fast"
        self.render_preset: str = self.config.get("render_preset", "balanced")
        # Настройки экспорта (сохраняются между запусками)
        self.export_codec: str = self.config.get("export_codec", "h264")
        self.export_size_str: str = self.config.get("export_size", "900x1200")
        self.export_fps: int = int(self.config.get("export_fps", 60) or 60)

        # Текущее выбранное общее видео для наложения
        self.global_video_path: str | None = None

        # Список данных по изображениям
        self.items: list[ImageItemData] = []

        # Кэш базового изображения для превью наложения (уменьшенный кадр карточки)
        self.preview_base_frame: np.ndarray | None = None
        # Видеопоток для зацикленного превью и таймер кадров
        self.preview_cap: cv2.VideoCapture | None = None
        self.preview_playing: bool = True
        self.preview_fps: float = 25.0
        self.preview_total_frames: int = 1
        self.preview_last_frame: np.ndarray | None = None  # последний кадр для перерисовки при паузе
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._on_preview_tick)

        # Режимы предпросмотра (уменьшенное превью, чтобы не занимало весь центр).
        # Экспорт по-прежнему делается в 900x1200.
        self.preview_target_w = 320
        self.preview_target_h = 426

        self.setWindowTitle("Wbo BAMP — генератор видео-карточек")
        # Размер окна: при первом запуске — крупнее; потом восстанавливаем последний
        settings = QSettings("WboBAMP", "WboBAMP")
        saved_geom = settings.value("mainWindow/geometry")
        if saved_geom and isinstance(saved_geom, QByteArray):
            self.restoreGeometry(saved_geom)
        else:
            self.resize(1100, 720)

        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))

        # Разрешаем drag & drop на всё окно, чтобы было проще попадать
        self.setAcceptDrops(True)

        self._build_ui()
        self._setup_actions_and_menu()

        # Загружаем список доступных видео из папки Assets/video
        self.load_video_list()

        # При старте загружаем демо-изображения, если есть; выбираем первую карточку, чтобы превью с видео сразу показывалось
        demo_dir = BASE_DIR / "Assets" / "demo"
        if demo_dir.exists():
            self.load_images_from_dir(str(demo_dir.resolve()))
        if self.list_widget.count() > 0 and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)

    def dragEnterEvent(self, event) -> None:
        """Разрешаем drag & drop файлов на всё окно, прокидываем в список карточек."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def closeEvent(self, event) -> None:
        """При закрытии окна сохраняем размер/позицию и останавливаем превью."""
        settings = QSettings("WboBAMP", "WboBAMP")
        settings.setValue("mainWindow/geometry", self.saveGeometry())
        self._stop_preview_video()
        super().closeEvent(event)

    # --- Перезапуск приложения (используется после установки FFmpeg) ---
    def _restart_app(self) -> None:
        """Перезапуск текущего приложения (работает и для .py, и для .exe)."""
        try:
            if getattr(sys, "frozen", False):
                exe_path = sys.executable
                QProcess.startDetached(exe_path, [])
            else:
                script = Path(__file__).resolve()
                QProcess.startDetached(sys.executable, [str(script)])
        except Exception:
            return
        QCoreApplication.quit()

    def mousePressEvent(self, event) -> None:
        """Перетаскивание окна за кастомный заголовок."""
        if event.button() == Qt.LeftButton and self._title_bar is not None:
            if self._title_bar.geometry().contains(event.pos()):
                self._drag_active = True
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_active and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_active = False
        super().mouseReleaseEvent(event)

    def dropEvent(self, event) -> None:
        """Обрабатываем drop на окне и перенаправляем файлы в список карточек."""
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        urls = event.mimeData().urls()
        file_paths: list[str] = []
        for url in urls:
            local_path = url.toLocalFile()
            if local_path:
                file_paths.append(local_path)

        if file_paths:
            self.add_images_from_files(file_paths)
        event.acceptProposedAction()

    def set_status_state(self, text: str) -> None:
        """Обновить текст состояния в нижней строке статуса."""
        if hasattr(self, "status_state_label") and self.status_state_label:
            self.status_state_label.setText(text)

    def _update_status_state(self) -> None:
        """Вычислить и установить состояние: что работает, что нет."""
        parts = []
        if self.list_widget.count() == 0:
            parts.append("нет карточек")
        else:
            parts.append(f"карточки: {self.list_widget.count()}")
        if self.video_list.count() == 0:
            parts.append("нет видео")
        else:
            parts.append(f"видео: {self.video_list.count()}")
        self.set_status_state("  •  ".join(parts) if parts else "Готов")

    def load_video_list(self) -> None:
        """Загрузка списка видео из папки Assets/video."""
        video_dir = BASE_DIR / "Assets" / "video"
        self.video_list.clear()
        if not video_dir.exists():
            self._update_status_state()
            return

        for p in sorted(video_dir.iterdir()):
            if p.suffix.lower() == ".mp4":
                item = QListWidgetItem(p.name)
                item.setData(Qt.UserRole, str(p.resolve()))
                self.video_list.addItem(item)

        if self.video_list.count() > 0:
            if self.global_video_path:
                path_str = str(Path(self.global_video_path).resolve())
                for i in range(self.video_list.count()):
                    if self.video_list.item(i).data(Qt.UserRole) == path_str:
                        self.video_list.setCurrentRow(i)
                        break
                else:
                    self.video_list.setCurrentRow(0)
            else:
                self.video_list.setCurrentRow(0)
        self._update_status_state()

    def _build_ui(self) -> None:
        """Современный интерфейс: кастомный заголовок, удобные панели, акцент на экспорт."""
        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        main_container = QFrame()
        main_container.setObjectName("mainContainer")
        main_layout = QHBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        root_layout.addWidget(main_container, 1)

        # —— Нижняя строка: статусы и информация ——
        status_bar = QFrame()
        status_bar.setObjectName("statusBar")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(10, 4, 10, 4)
        status_layout.setSpacing(12)
        self.status_name_label = QLabel(f"Wbo BAMP  |  v{APP_VERSION}")
        self.status_name_label.setObjectName("statusName")
        status_layout.addWidget(self.status_name_label)
        status_layout.addStretch(1)
        self.status_state_label = QLabel("Готов")
        self.status_state_label.setObjectName("statusState")
        status_layout.addWidget(self.status_state_label)
        root_layout.addWidget(status_bar)

        # —— 1. Карточки ——
        self.left_panel = QFrame()
        self.left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setSpacing(6)

        row1 = QHBoxLayout()
        step1 = QLabel("1. Карточки")
        step1.setObjectName("sectionLabel")
        row1.addWidget(step1)
        row1.addStretch(1)
        left_layout.addLayout(row1)
        hint1 = QLabel("Добавьте изображения или перетащите в окно")
        hint1.setObjectName("stepHint")
        left_layout.addWidget(hint1)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        btn_load_images = QPushButton(" Загрузить ")
        btn_load_images.setToolTip("Загрузить изображения из папки (Ctrl+O)")
        btn_load_images.setIcon(load_phosphor_icon("folder-open", 14))
        btn_load_images.setIconSize(QSize(14, 14))
        btn_load_images.clicked.connect(self.on_load_images_clicked)
        toolbar.addWidget(btn_load_images)
        self.btn_duplicate = QPushButton()
        self.btn_duplicate.setToolTip("Дублировать выбранные карточки (Ctrl+J)")
        self.btn_duplicate.setIcon(load_phosphor_icon("Files", 14))
        self.btn_duplicate.setIconSize(QSize(14, 14))
        self.btn_duplicate.setProperty("class", "iconOnly accent")
        self.btn_duplicate.clicked.connect(self.on_duplicate_selected_clicked)
        self.btn_duplicate.setEnabled(False)
        toolbar.addWidget(self.btn_duplicate)
        self.btn_delete_selected = QPushButton()
        self.btn_delete_selected.setToolTip("Удалить выбранные (Delete)")
        self.btn_delete_selected.setIcon(load_phosphor_icon("trash", 14))
        self.btn_delete_selected.setIconSize(QSize(14, 14))
        self.btn_delete_selected.setProperty("class", "iconOnly danger")
        self.btn_delete_selected.clicked.connect(self.on_delete_selected_clicked)
        self.btn_delete_selected.setEnabled(False)
        toolbar.addWidget(self.btn_delete_selected)
        toolbar.addStretch(1)
        left_layout.addLayout(toolbar)

        self.list_widget = ImageListWidget(self)
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.setProperty("listMode", False)
        self.list_widget.setViewMode(QListWidget.IconMode)
        # Сетка: крупные превью с нормальным расстоянием между карточками
        self.list_widget.setIconSize(QSize(88, 88))
        self.list_widget.setGridSize(QSize(100, 128))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Static)
        left_layout.addWidget(self.list_widget, 1)

        main_layout.addWidget(self.left_panel, 2)

        # —— 2. Превью ——
        self.center_panel = QFrame()
        self.center_panel.setObjectName("panel")
        center_layout = QVBoxLayout(self.center_panel)
        center_layout.setSpacing(6)
        hint2 = QLabel("Карточка + видео → наложение в реальном времени")
        hint2.setObjectName("stepHint")
        center_layout.addWidget(hint2)

        self.lbl_image_preview = QLabel()
        self.lbl_image_preview.setMinimumSize(140, 186)
        self.lbl_image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_image_preview.setStyleSheet(
            "background: transparent; border: 1px solid #30363d; border-radius: 8px;"
        )
        self.lbl_image_preview.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.lbl_image_preview)

        # Таймлайн превью: ползунок + одна кнопка Play/Pause (без надписей)
        self._preview_slider_syncing = False
        preview_controls = QHBoxLayout()
        preview_controls.setSpacing(8)
        self.btn_preview_play_pause = QPushButton()
        self.btn_preview_play_pause.setToolTip("Пауза / воспроизведение (Space)")
        self.btn_preview_play_pause.setIcon(load_phosphor_icon("pause", 18))
        self.btn_preview_play_pause.setIconSize(QSize(18, 18))
        self.btn_preview_play_pause.setProperty("class", "iconOnly")
        self.btn_preview_play_pause.clicked.connect(self._toggle_preview_play_pause)
        self.slider_preview_timeline = QSlider(Qt.Horizontal)
        self.slider_preview_timeline.setObjectName("previewTimeline")
        self.slider_preview_timeline.setMinimum(0)
        self.slider_preview_timeline.setMaximum(100)
        self.slider_preview_timeline.setValue(0)
        self.slider_preview_timeline.setMinimumHeight(28)
        self.slider_preview_timeline.valueChanged.connect(self._on_preview_timeline_slider_changed)
        preview_controls.addWidget(self.btn_preview_play_pause)
        preview_controls.addWidget(self.slider_preview_timeline, 1)
        center_layout.addLayout(preview_controls)
        center_layout.addStretch(1)
        main_layout.addWidget(self.center_panel, 3)

        # —— 3. Видео и настройки ——
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.setSpacing(6)

        step3 = QLabel("Видео и настройки")
        step3.setObjectName("sectionLabel")
        right_layout.addWidget(step3)

        video_panel = QFrame()
        video_panel.setObjectName("panel")
        video_pl = QVBoxLayout(video_panel)
        video_pl.setSpacing(6)

        video_header = QHBoxLayout()
        lbl_video = QLabel("Ролики (Assets/video)")
        lbl_video.setObjectName("stepHint")
        video_header.addWidget(lbl_video)
        video_header.addStretch(1)
        btn_refresh_videos = QPushButton()
        btn_refresh_videos.setToolTip("Обновить список")
        btn_refresh_videos.setIcon(load_phosphor_icon("arrows-clock", 12))
        btn_refresh_videos.setIconSize(QSize(12, 12))
        btn_refresh_videos.setProperty("class", "iconOnly accent")
        btn_refresh_videos.clicked.connect(self.on_refresh_videos_clicked)
        video_header.addWidget(btn_refresh_videos)
        video_pl.addLayout(video_header)

        # Перенесён выбор разрешения предпросмотра рядом с видео
        res_row = QHBoxLayout()
        res_row.addWidget(QLabel("Разрешение предпросмотра:"))
        res_row.addStretch(1)
        self.preview_mode_combo = QComboBox()
        self.preview_mode_combo.addItem("200×266", (200, 266))
        self.preview_mode_combo.addItem("260×346", (260, 346))
        self.preview_mode_combo.addItem("320×426", (320, 426))
        self.preview_mode_combo.setCurrentIndex(2)  # по умолчанию 320×426
        self.preview_mode_combo.currentIndexChanged.connect(self._on_preview_mode_changed)
        res_row.addWidget(self.preview_mode_combo)
        video_pl.addLayout(res_row)
        self.video_list = QListWidget()
        self.video_list.setMaximumHeight(100)
        self.video_list.currentItemChanged.connect(self.on_video_selected)
        video_pl.addWidget(self.video_list)
        self.chk_single_video = QCheckBox("Один ролик для всех карточек")
        self.chk_single_video.setObjectName("singleVideoCheckbox")
        self.chk_single_video.setChecked(True)
        video_pl.addWidget(self.chk_single_video)
        self.lbl_global_video = QLabel("Не выбрано")
        self.lbl_global_video.setObjectName("stepHint")
        self.lbl_global_video.setWordWrap(True)
        video_pl.addWidget(self.lbl_global_video)
        right_layout.addWidget(video_panel)

        card_panel = QFrame()
        card_panel.setObjectName("panel")
        card_pl = QVBoxLayout(card_panel)
        card_pl.setSpacing(4)
        card_pl.addWidget(QLabel("Текущая карточка"))
        self.lbl_selected_image = QLabel("—")
        self.lbl_selected_image.setObjectName("stepHint")
        self.lbl_selected_image.setWordWrap(True)
        card_pl.addWidget(self.lbl_selected_image)
        self.lbl_selected_video = QLabel("Видео: общее")
        self.lbl_selected_video.setObjectName("stepHint")
        self.lbl_selected_video.setWordWrap(True)
        card_pl.addWidget(self.lbl_selected_video)
        right_layout.addWidget(card_panel)

        curve_panel = QFrame()
        curve_panel.setObjectName("panel")
        curve_pl = QVBoxLayout(curve_panel)
        curve_pl.setSpacing(4)
        curve_sec = QLabel("Кривая: тени / средние / света")
        curve_sec.setObjectName("sectionLabel")
        curve_pl.addWidget(curve_sec)
        curve_top = QHBoxLayout()
        self.lbl_curve_preview = CurvePreviewLabel(self, 128)
        curve_top.addWidget(self.lbl_curve_preview)
        sliders_col = QVBoxLayout()
        sliders_col.setSpacing(2)
        self.lbl_curve_shadows = QLabel("Тени: 64")
        sliders_col.addWidget(self.lbl_curve_shadows)
        self.slider_curve_shadows = QSlider(Qt.Horizontal)
        self.slider_curve_shadows.setObjectName("curveSlider")
        self.slider_curve_shadows.setMaximumHeight(20)
        self.slider_curve_shadows.setMinimum(0)
        self.slider_curve_shadows.setMaximum(255)
        self.slider_curve_shadows.setValue(64)
        self.slider_curve_shadows.valueChanged.connect(self.on_curve_shadows_changed)
        sliders_col.addWidget(self.slider_curve_shadows)
        self.lbl_curve_midtones = QLabel("Средние: 128")
        sliders_col.addWidget(self.lbl_curve_midtones)
        self.slider_curve_midtones = QSlider(Qt.Horizontal)
        self.slider_curve_midtones.setObjectName("curveSlider")
        self.slider_curve_midtones.setMaximumHeight(20)
        self.slider_curve_midtones.setMinimum(0)
        self.slider_curve_midtones.setMaximum(255)
        self.slider_curve_midtones.setValue(128)
        self.slider_curve_midtones.valueChanged.connect(self.on_curve_midtones_changed)
        sliders_col.addWidget(self.slider_curve_midtones)
        self.lbl_curve_highlights = QLabel("Света: 192")
        sliders_col.addWidget(self.lbl_curve_highlights)
        self.slider_curve_highlights = QSlider(Qt.Horizontal)
        self.slider_curve_highlights.setObjectName("curveSlider")
        self.slider_curve_highlights.setMaximumHeight(20)
        self.slider_curve_highlights.setMinimum(0)
        self.slider_curve_highlights.setMaximum(255)
        self.slider_curve_highlights.setValue(192)
        self.slider_curve_highlights.valueChanged.connect(self.on_curve_highlights_changed)
        sliders_col.addWidget(self.slider_curve_highlights)
        curve_top.addLayout(sliders_col, 1)
        curve_pl.addLayout(curve_top)
        right_layout.addWidget(curve_panel)

        self.btn_export_main = QPushButton(" Экспорт ")
        self.btn_export_main.setProperty("class", "primary")
        self.btn_export_main.setToolTip("Экспорт выбранных или всех карточек в MP4 (Ctrl+Shift+E)")
        self.btn_export_main.setIcon(load_phosphor_icon("export", 16))
        self.btn_export_main.setIconSize(QSize(16, 16))
        self.btn_export_main.clicked.connect(self.on_export_clicked)
        right_layout.addWidget(self.btn_export_main)

        right_layout.addStretch(1)
        self.right_scroll.setWidget(right_content)
        main_layout.addWidget(self.right_scroll, 2)

        self.list_widget.currentRowChanged.connect(self.on_current_item_changed)
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.on_selection_changed()

    def _setup_actions_and_menu(self) -> None:
        """Меню сверху и горячие клавиши."""
        # Меню
        menu_bar = self.menuBar()
        view_menu = menu_bar.addMenu("Вид")
        self.act_view_left = QAction("Левая панель (карточки)", self, checkable=True, checked=True)
        self.act_view_left.triggered.connect(self._toggle_left_panel)
        view_menu.addAction(self.act_view_left)

        self.act_view_center = QAction("Центральная панель (превью)", self, checkable=True, checked=True)
        self.act_view_center.triggered.connect(self._toggle_center_panel)
        view_menu.addAction(self.act_view_center)

        self.act_view_right = QAction("Правая панель (настройки)", self, checkable=True, checked=True)
        self.act_view_right.triggered.connect(self._toggle_right_panel)
        view_menu.addAction(self.act_view_right)

        # Подменю «Режим рендера»: качество vs скорость экспорта (без QActionGroup — совместимость)
        export_menu = menu_bar.addMenu("Экспорт")
        render_sub = export_menu.addMenu("Режим рендера")
        self._render_preset_actions: list[tuple[QAction, str]] = []

        def _make_render_preset_action(label: str, preset: str) -> QAction:
            act = QAction(label, self, checkable=True)
            act.setChecked(self.render_preset == preset)
            act.triggered.connect(lambda checked, p=preset: self._on_render_preset_changed(p))
            self._render_preset_actions.append((act, preset))
            return act

        render_sub.addAction(_make_render_preset_action("Высокое качество (медленный рендер)", "quality"))
        render_sub.addAction(_make_render_preset_action("Среднее качество (быстрый рендер)", "balanced"))
        render_sub.addAction(_make_render_preset_action("Очень быстрый рендер", "fast"))

        help_menu = menu_bar.addMenu("Помощь")

        act_about = QAction("О программе", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

        act_readme = QAction("Справка", self)
        act_readme.triggered.connect(self._show_readme)
        help_menu.addAction(act_readme)

        act_history = QAction("История изменений", self)
        act_history.triggered.connect(self._show_history)
        help_menu.addAction(act_history)

        act_author = QAction("Автор", self)
        act_author.triggered.connect(self._show_author)
        help_menu.addAction(act_author)

        # Горячие клавиши: один источник правды для регистрации и для «О программе»
        self._hotkey_specs: list[tuple[str, object]] = [
            ("Ctrl+O", self.on_load_images_clicked, "загрузить изображения из папки"),
            ("Ctrl+E", self.on_export_current_clicked, "экспорт карточки, выбранной в превью"),
            ("Ctrl+Shift+E", self.on_export_clicked, "экспорт выбранных или всех карточек в MP4"),
            ("Ctrl+J", self.on_duplicate_selected_clicked, "дублировать выбранные карточки (с настройками)"),
            ("Delete", self.on_delete_selected_clicked, "удалить выбранные карточки"),
            ("Space", self._toggle_preview_play_pause, "пауза / воспроизведение превью"),
        ]
        for key_str, callback, _ in self._hotkey_specs:
            QShortcut(QKeySequence(key_str), self, activated=callback)

    def _toggle_left_panel(self, checked: bool) -> None:
        """Скрытие/показ левой панели карточек через меню 'Вид'."""
        if hasattr(self, "left_panel"):
            self.left_panel.setVisible(checked)

    def _toggle_center_panel(self, checked: bool) -> None:
        """Скрытие/показ центральной панели превью."""
        if hasattr(self, "center_panel"):
            self.center_panel.setVisible(checked)

    def _toggle_right_panel(self, checked: bool) -> None:
        """Скрытие/показ правой панели настроек."""
        if hasattr(self, "right_scroll"):
            self.right_scroll.setVisible(checked)

    def _on_render_preset_changed(self, preset: str) -> None:
        """Смена режима рендера (качество / скорость). Оставляем отмеченным только выбранный пункт."""
        self.render_preset = preset
        self.config["render_preset"] = preset
        save_config(self.config)
        for act, p in getattr(self, "_render_preset_actions", []):
            act.setChecked(p == preset)

    def _on_preview_mode_changed(self, index: int) -> None:
        """Изменение режима предпросмотра (разрешения превью)."""
        data = self.preview_mode_combo.itemData(index)
        if isinstance(data, tuple) and len(data) == 2:
            w, h = data
            self.preview_target_w = int(w)
            self.preview_target_h = int(h)
            # Перезагружаем превью для текущей карточки с новым разрешением
            self._load_preview_frames_for_current()

    def _show_about(self) -> None:
        """Диалог 'О программе' с краткой инструкцией и горячими клавишами."""
        SoundPlayer.play(SOUND_CLICK)
        hotkeys_lines = [f"  {key:<16} — {desc}" for key, _, desc in self._hotkey_specs]
        hotkeys_text = "\n".join(hotkeys_lines)
        text = (
            "Wbo BAMP — генератор видео-карточек.\n\n"
            "Основной сценарий работы:\n"
            "1. Слева загрузите изображения карточек (иконка папки).\n"
            "2. Выберите видео в блоке «Список видео» справа.\n"
            "3. Настройте кривую (тени / средние / света).\n"
            "4. Для предпросмотра используйте большую область в центре — видео\n"
            "   накладывается в реальном времени в режиме «Экран».\n"
            "5. Экспортируйте карточки в MP4 кнопкой внизу справа.\n\n"
            "Горячие клавиши:\n"
            f"{hotkeys_text}\n\n"
            "Поддерживаются форматы изображений: JPG, PNG, WEBP.\n"
            "Видео — MP4 (кодеки H.264, H.265, AV1, если установлены в системе)."
        )
        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dlg.setStyleSheet(HELP_DIALOG_STYLE)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(DialogTitleBar(dlg, "О программе"))
        content = QWidget()
        content_ly = QVBoxLayout(content)
        content_ly.setContentsMargins(12, 8, 12, 12)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        content_ly.addWidget(lbl)
        btn_ok = QPushButton("ОК")
        btn_ok.clicked.connect(dlg.accept)
        content_ly.addWidget(btn_ok, alignment=Qt.AlignRight)
        layout.addWidget(content)
        QShortcut(QKeySequence("Escape"), dlg, dlg.reject)
        dlg.resize(420, 380)
        SoundPlayer.play(SOUND_DIALOG)
        dlg.exec()

    def _show_readme(self) -> None:
        """Показать содержимое README.md в диалоге (без сырой markdown-разметки)."""
        SoundPlayer.play(SOUND_CLICK)
        readme_path = BASE_DIR / "README.md"
        try:
            raw = readme_path.read_text(encoding="utf-8") if readme_path.exists() else "Файл README не найден."
            text = _format_readme_for_display(raw)
        except Exception:
            text = "Не удалось прочитать README."
        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dlg.setStyleSheet(HELP_DIALOG_STYLE)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(DialogTitleBar(dlg, "Справка"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setMinimumWidth(420)
        scroll.setWidget(lbl)
        layout.addWidget(scroll, 1)
        btn_ok = QPushButton("ОК")
        btn_ok.clicked.connect(dlg.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)
        QShortcut(QKeySequence("Escape"), dlg, dlg.reject)
        dlg.resize(480, 420)
        SoundPlayer.play(SOUND_DIALOG)
        dlg.exec()

    def _show_history(self) -> None:
        """Диалог с краткой историей изменений интерфейса и функционала."""
        SoundPlayer.play(SOUND_CLICK)
        text = (
            "История изменений (кратко):\n\n"
            "• Добавлен предпросмотр видео-наложения в реальном времени в центре окна.\n"
            "• Реализована кривая (тени / средние / света) с LUT и мини-графиком.\n"
            "• Переработан интерфейс в стиле Adobe: тёмная тема, панели, иконки Phosphor.\n"
            "• Введены зацикленный предпросмотр, пауза/пуск и горячие клавиши.\n"
            "• Левая колонка стала панелью карточек с компактным тулбаром.\n"
            "• Правая колонка разделена на панели: видео, выбранная карточка, кривая, экспорт.\n"
            "• Добавлена поддержка иконок из папки Assets/icons (SVG/PNG).\n"
        )
        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dlg.setStyleSheet(HELP_DIALOG_STYLE)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(DialogTitleBar(dlg, "История изменений"))
        content = QWidget()
        content_ly = QVBoxLayout(content)
        content_ly.setContentsMargins(12, 8, 12, 12)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        content_ly.addWidget(lbl)
        btn_ok = QPushButton("ОК")
        btn_ok.clicked.connect(dlg.accept)
        content_ly.addWidget(btn_ok, alignment=Qt.AlignRight)
        layout.addWidget(content)
        QShortcut(QKeySequence("Escape"), dlg, dlg.reject)
        dlg.resize(440, 320)
        SoundPlayer.play(SOUND_DIALOG)
        dlg.exec()

    def _show_author(self) -> None:
        """Диалог с информацией об авторе."""
        # Вместо системного звука запускаем фоновый трек портфолио,
        # который играет, пока открыто окно автора.
        full_text = (
            "Я — Радыгин Иван Олегович.\n\n"
            "Занимаюсь тем, что изучаю нейросети и заставляю их работать на деньги. "
            "Не на красивые презентации, а на реальную пользу: изображения, дизайн, видео, "
            "автоматизация и всякие странные штуки, которые раньше требовали команду из десяти человек.\n\n"
            "Последнее время меня затянуло в вайбкодинг.\n"
            "Если коротко: это когда ты не сидишь неделями над синтаксисом, а задаёшь направление, "
            "идею и архитектуру, а ИИ пишет код вместе с тобой. Ты управляешь процессом, как дирижёр. "
            "Код появляется быстрее, чем успеваешь заварить кофе.\n\n"
            "Пока многие прохлаждались на выходных, я ковырялся в этом самом вайбкодинге — "
            "с почти базовыми знаниями фронтенда и нулевыми знаниями бэкенда.\n\n"
            "В итоге:\n"
            "— разработал мессенджер для студии Mundfish;\n"
            "— сделал большой вклад в лендинг и рекламу;\n"
            "— теперь занимаюсь интернет-магазинами и проектами компании — официального представителя CDEK.\n\n"
            "Следов своих я ещё оставлю много. В разных проектах, местах и продуктах.\n\n"
            "А дальше — посмотрим.\n"
            "Надеюсь только вовремя свалить из мест, где идеи принимают бесплатно, как будто это воздух. "
            "Мой альтруизм уже давно вышел из чата.\n\n"
            "Приятного."
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Автор")
        dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dlg.setStyleSheet(
            HELP_DIALOG_STYLE
            + " QWidget#authorContent { background: transparent; }"
            " QLabel#authorName { color: #e6edf3; font-size: 15px; font-weight: 600; }"
            " QLabel#authorSubtitle { color: #8b949e; font-size: 13px; }"
        )
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(DialogTitleBar(dlg, "Об авторе"))
        content = QWidget()
        content.setObjectName("authorContent")
        layout_inner = QVBoxLayout(content)
        layout_inner.setSpacing(12)
        layout_inner.setContentsMargins(16, 16, 16, 16)

        # Фоновый трек портфолио (без визуала)
        if SOUND_PORTFOLIO.exists():
            try:
                player = QMediaPlayer(dlg)
                audio = QAudioOutput(dlg)
                player.setAudioOutput(audio)
                audio.setVolume(0.35)
                player.setSource(QUrl.fromLocalFile(str(SOUND_PORTFOLIO)))
                try:
                    player.setLoops(-1)
                except Exception:
                    def _restart_on_end(status: QMediaPlayer.MediaStatus) -> None:
                        if status == QMediaPlayer.EndOfMedia:
                            player.setPosition(0)
                            player.play()
                    player.mediaStatusChanged.connect(_restart_on_end)
                player.play()
            except Exception:
                pass

        # Аватар в круге
        avatar_path = BASE_DIR / "Assets" / "images" / "ivan.jpg"
        if avatar_path.exists():
            raw = QPixmap(str(avatar_path))
            if not raw.isNull():
                size = 80
                raw = raw.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                circle = QPixmap(size, size)
                circle.fill(Qt.transparent)
                painter = QPainter(circle)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)
                painter.setBrush(Qt.white)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(0, 0, size, size)
                painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
                painter.drawPixmap(0, 0, raw)
                painter.end()
                avatar_lbl = QLabel()
                avatar_lbl.setPixmap(circle)
                avatar_lbl.setAlignment(Qt.AlignHCenter)
                layout_inner.addWidget(avatar_lbl)

        name_lbl = QLabel("Радыгин Иван Олегович")
        name_lbl.setObjectName("authorName")
        layout_inner.addWidget(name_lbl)

        subtitle_lbl = QLabel("Нейросети, вайбкодинг и проекты, которые приносят пользу")
        subtitle_lbl.setObjectName("authorSubtitle")
        subtitle_lbl.setWordWrap(True)
        layout_inner.addWidget(subtitle_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #2a3038; max-height: 1px; border: none;")
        layout_inner.addWidget(sep)

        text_lbl = QLabel(full_text)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet("color: #b1b8c2; font-size: 13px;")
        scroll = QScrollArea()
        scroll.setWidget(text_lbl)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout_inner.addWidget(scroll, 1)

        layout.addWidget(content)
        QShortcut(QKeySequence("Escape"), dlg, dlg.reject)
        dlg.resize(420, 400)
        SoundPlayer.play(SOUND_DIALOG)
        dlg.exec()

    # ====================== Работа с изображениями ==========================

    def load_images_from_dir(self, directory: str) -> None:
        """Загрузка изображений из указанной папки."""
        # Комментарий: сюда можно добавить фильтрацию по расширениям
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        dir_path = Path(directory)
        if not dir_path.exists():
            QMessageBox.warning(self, "Папка не найдена", f"Папка не существует:\n{directory}")
            return

        # Полностью очищаем текущий список и загружаем заново
        self.list_widget.clear()
        self.items.clear()

        files: list[str] = []
        for p in sorted(dir_path.iterdir()):
            if p.suffix.lower() in exts:
                files.append(str(p.resolve()))

        # Добавляем найденные файлы через общий метод
        self.add_images_from_files(files, clear_existing=False)

        if not self.items:
            QMessageBox.information(
                self,
                "Нет изображений",
                "В выбранной папке не найдено подходящих изображений (jpg, png, webp).",
            )
            return

        # Выбираем первую карточку, чтобы превью наложения и видео сразу отобразились
        self.list_widget.setCurrentRow(0)

        # Сохраняем путь в конфиг
        self.config["last_images_path"] = directory
        save_config(self.config)

    def add_images_from_files(self, file_paths: list[str], clear_existing: bool = False) -> None:
        """
        Добавление изображений по списку путей.

        clear_existing=False — добавляем к уже существующим карточкам.
        """
        exts = {".jpg", ".jpeg", ".png", ".webp", ".png"}

        if clear_existing:
            self.list_widget.clear()
            self.items.clear()

        for path in file_paths:
            p = Path(path)
            if not p.exists():
                continue
            if p.suffix.lower() not in exts:
                continue

            item_data = ImageItemData(str(p.resolve()))
            self.items.append(item_data)

            item = QListWidgetItem(p.name)
            # Иконка всегда в размере сетки (88×88), чтобы при переключении вид Сетка/Список превью было чётким
            pixmap = QPixmap(str(p.resolve()))
            if not pixmap.isNull():
                icon_pixmap = pixmap.scaled(
                    QSize(88, 88),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                item.setIcon(icon_pixmap)

            self.list_widget.addItem(item)

        self._update_status_state()
        # Если добавляли файлы из разных папок, запоминаем путь первой
        if file_paths:
            first_dir = str(Path(file_paths[0]).resolve().parent)
            self.config["last_images_path"] = first_dir
            save_config(self.config)

    # ====================== Обработчики UI-событий =========================

    def on_load_images_clicked(self) -> None:
        """Выбор папки с изображениями."""
        start_dir = self.config.get("last_images_path", str(Path.cwd()))
        directory = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку с изображениями",
            start_dir,
        )
        if directory:
            self.load_images_from_dir(directory)

    def get_current_item(self) -> ImageItemData | None:
        """Возврат данных по текущей выбранной карточке."""
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.items):
            return None
        return self.items[row]

    def on_current_item_changed(self, row: int) -> None:
        """Обновление правой панели при смене выбранной карточки."""
        item = self.get_current_item()
        if not item:
            self._stop_preview_video()
            self.preview_base_frame = None
            self.lbl_image_preview.setPixmap(QPixmap())
            self.lbl_image_preview.setText("Нет предпросмотра наложения")
            self.lbl_selected_image.setText("Карточка не выбрана")
            self.lbl_selected_video.setText("Видео не выбрано (используется общее)")
            self.update_image_preview(None)
            self._draw_curve_preview(64, 128, 192)  # нейтральная кривая в превью
            return

        self.lbl_selected_image.setText(item.image_path)
        if item.video_path:
            self.lbl_selected_video.setText(item.video_path)
        else:
            self.lbl_selected_video.setText("Видео не выбрано (используется общее)")

        # Обновляем слайдеры кривой из данных карточки
        self.slider_curve_shadows.blockSignals(True)
        self.slider_curve_midtones.blockSignals(True)
        self.slider_curve_highlights.blockSignals(True)
        self.slider_curve_shadows.setValue(item.curve_shadows)
        self.slider_curve_midtones.setValue(item.curve_midtones)
        self.slider_curve_highlights.setValue(item.curve_highlights)
        self.slider_curve_shadows.blockSignals(False)
        self.slider_curve_midtones.blockSignals(False)
        self.slider_curve_highlights.blockSignals(False)
        self._update_curve_labels_and_preview()

        # Синхронизируем список видео: выделяем то видео, которое используется этой карточкой
        self._sync_video_list_to_card(item)

        # Сначала загружаем превью с видео; если видео нет или не открылось — покажем исходное изображение
        video_started = self._load_preview_frames_for_current()
        if not video_started:
            self.update_image_preview(item.image_path)

    def _sync_video_list_to_card(self, item: ImageItemData) -> None:
        """Выделить в списке видео то ролик, который используется карточкой (общее или своё)."""
        video_path = item.video_path or self.global_video_path
        if not video_path:
            return
        path_str = str(Path(video_path).resolve())
        for i in range(self.video_list.count()):
            vi = self.video_list.item(i)
            if vi and vi.data(Qt.UserRole) == path_str:
                self.video_list.blockSignals(True)
                self.video_list.setCurrentRow(i)
                self.video_list.blockSignals(False)
                return
        # Если видео из другой папки — сравниваем как строки
        for i in range(self.video_list.count()):
            vi = self.video_list.item(i)
            if vi and vi.data(Qt.UserRole) == video_path:
                self.video_list.blockSignals(True)
                self.video_list.setCurrentRow(i)
                self.video_list.blockSignals(False)
                return

    def on_selection_changed(self) -> None:
        """
        Обработка изменения выделения карточек.

        Кнопка «Удалить» активна только при выборе; кнопка «Экспорт» показывает число выбранных.
        """
        indexes = self.list_widget.selectedIndexes()
        count = len(indexes)
        has_selection = count > 0
        self.btn_delete_selected.setEnabled(has_selection)
        self.btn_duplicate.setEnabled(has_selection)
        # Экспорт: без выбора — «Экспорт», 1 — «Экспорт», больше 1 — «Экспорт (N)»
        if count <= 1:
            self.btn_export_main.setText(" Экспорт ")
        else:
            self.btn_export_main.setText(f" Экспорт ({count}) ")

    def on_refresh_videos_clicked(self) -> None:
        """Ручное обновление списка видео из папки Assets/video."""
        self.load_video_list()

    def on_video_selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        """Обработка выбора видео из списка."""
        if not current:
            return

        video_path = current.data(Qt.UserRole)
        if not video_path:
            return

        if self.chk_single_video.isChecked():
            # Режим одного видео для всех карточек
            self.global_video_path = video_path
            self.lbl_global_video.setText(video_path)
        else:
            # Режим отдельных видео: привязываем к текущей карточке
            item = self.get_current_item()
            if not item:
                QMessageBox.information(
                    self,
                    "Нет карточки",
                    "Сначала выберите карточку в списке, затем выбирайте видео.",
                )
                return
            item.video_path = video_path
            self.lbl_selected_video.setText(video_path)

        # После смены видео для общего режима или карточки — обновляем предпросмотр наложения
        self._load_preview_frames_for_current()

    def on_curve_shadows_changed(self, value: int) -> None:
        """Обновление точки «Тени» для текущей карточки."""
        item = self.get_current_item()
        if item:
            item.curve_shadows = value
        self._update_curve_labels_and_preview()

    def on_curve_midtones_changed(self, value: int) -> None:
        """Обновление точки «Средние» для текущей карточки."""
        item = self.get_current_item()
        if item:
            item.curve_midtones = value
        self._update_curve_labels_and_preview()

    def on_curve_highlights_changed(self, value: int) -> None:
        """Обновление точки «Света» для текущей карточки."""
        item = self.get_current_item()
        if item:
            item.curve_highlights = value
        self._update_curve_labels_and_preview()

    def _update_curve_labels_and_preview(self) -> None:
        """Обновление подписей слайдеров и мини-графика кривой."""
        s = self.slider_curve_shadows.value()
        m = self.slider_curve_midtones.value()
        h = self.slider_curve_highlights.value()
        self.lbl_curve_shadows.setText(f"Тени: {s}")
        self.lbl_curve_midtones.setText(f"Средние: {m}")
        self.lbl_curve_highlights.setText(f"Света: {h}")
        self._draw_curve_preview(s, m, h)
        # Обновляем быстрое превью наложения
        self._update_overlay_preview(s, m, h)

    def _draw_curve_preview(self, shadows: int, midtones: int, highlights: int) -> None:
        """Отрисовка мини-графика кривой по трём точкам (тени/средние/света)."""
        w = h = self.lbl_curve_preview._size if hasattr(self.lbl_curve_preview, "_size") else 128
        pixmap = QPixmap(w, h)
        pixmap.fill(QColor("#2a2a2a"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Сетка и оси: вход по X, выход по Y (0 внизу)
        margin = self.lbl_curve_preview._margin if hasattr(self.lbl_curve_preview, "_margin") else 14
        graph_w = w - 2 * margin
        graph_h = h - 2 * margin
        painter.setPen(QPen(QColor("#555"), 1))
        painter.drawRect(margin, margin, graph_w, graph_h)
        # Диагональ (линейная кривая)
        painter.setPen(QPen(QColor("#444"), 1))
        painter.drawLine(margin, margin + graph_h, margin + graph_w, margin)

        # Строим LUT и рисуем кривую
        lut = build_curve_lut(shadows, midtones, highlights)
        pts = []
        for x_in in range(256):
            y_out = int(lut[x_in])
            px = margin + (x_in / 255.0) * graph_w
            py = margin + graph_h - (y_out / 255.0) * graph_h
            pts.append((px, py))
        painter.setPen(QPen(QColor("#0cf"), 1))
        for i in range(len(pts) - 1):
            painter.drawLine(int(pts[i][0]), int(pts[i][1]), int(pts[i + 1][0]), int(pts[i + 1][1]))

        # Точки управления (кружки)
        for x_in, y_out in [(64, shadows), (128, midtones), (192, highlights)]:
            px = margin + (x_in / 255.0) * graph_w
            py = margin + graph_h - (y_out / 255.0) * graph_h
            painter.setPen(QPen(QColor("#fff"), 1))
            painter.setBrush(QColor("#0cf"))
            painter.drawEllipse(int(px - 2), int(py - 2), 4, 4)

        painter.end()
        self.lbl_curve_preview.setPixmap(pixmap)

    def _on_curve_preview_clicked(self, x_in: int, y_out: int) -> None:
        """Реакция на клик/перетаскивание по графику кривой: обновляем ближайшую точку управления."""
        points = [(64, 0), (128, 1), (192, 2)]
        nearest = min(points, key=lambda p: abs(p[0] - x_in))
        idx = nearest[1]
        value = max(0, min(255, y_out))
        if idx == 0:
            self.slider_curve_shadows.setValue(value)
        elif idx == 1:
            self.slider_curve_midtones.setValue(value)
        else:
            self.slider_curve_highlights.setValue(value)

    def _stop_preview_video(self) -> None:
        """Остановка таймера и освобождение видеопотока превью."""
        self._preview_timer.stop()
        if self.preview_cap is not None:
            self.preview_cap.release()
            self.preview_cap = None
        self.slider_preview_timeline.setMaximum(100)
        self.slider_preview_timeline.setValue(0)
        self.slider_preview_timeline.setEnabled(False)

    def _load_preview_frames_for_current(self) -> bool:
        """Подготовка превью: загрузка базового кадра и открытие видео для зацикленного воспроизведения. Возвращает True, если видео превью запущено."""
        item = self.get_current_item()
        self._stop_preview_video()
        self.preview_last_frame = None
        if not item:
            self.preview_base_frame = None
            self.lbl_image_preview.setPixmap(QPixmap())
            self.lbl_image_preview.setText("Нет предпросмотра наложения")
            return False

        # Загружаем базовое изображение под выбранный режим предпросмотра.
        # Пропорции всегда 3:4 (как у экспортируемого ролика), но разрешение
        # может быть ниже для быстрого просмотра.
        try:
            with Image.open(item.image_path) as img:
                img = img.convert("RGB")
                target_w, target_h = self.preview_target_w, self.preview_target_h
                img = img.resize((target_w, target_h), Image.LANCZOS)
                self.preview_base_frame = np.array(img)
        except Exception:
            self.preview_base_frame = None
            self.lbl_image_preview.setPixmap(QPixmap())
            self.lbl_image_preview.setText("Не удалось загрузить карточку")
            self.update_image_preview(item.image_path)
            return False

        video_path = item.video_path or self.global_video_path
        if not video_path:
            self.lbl_image_preview.setPixmap(QPixmap())
            self.lbl_image_preview.setText("Выберите видео в списке ниже")
            self.update_image_preview(item.image_path)
            return False

        # Пробуем открыть по абсолютному пути; если путь относительный — от BASE_DIR
        path_to_open = Path(video_path)
        if not path_to_open.is_absolute():
            path_to_open = BASE_DIR / path_to_open
        self.preview_cap = cv2.VideoCapture(str(path_to_open))
        if not self.preview_cap.isOpened():
            self.preview_cap = None
            self.lbl_image_preview.setPixmap(QPixmap())
            self.lbl_image_preview.setText("Не удалось открыть видео")
            self.update_image_preview(item.image_path)
            return False

        fps = self.preview_cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 25.0
        self.preview_fps = fps
        interval_ms = max(20, int(1000.0 / fps))
        self._preview_timer.setInterval(interval_ms)

        total_frames = int(self.preview_cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        self.preview_total_frames = max(1, total_frames)
        self._preview_slider_syncing = True
        self.slider_preview_timeline.setMaximum(self.preview_total_frames)
        self.slider_preview_timeline.setValue(0)
        self._preview_slider_syncing = False
        self.slider_preview_timeline.setEnabled(True)
        if self.preview_playing:
            self._preview_timer.start()
            self.btn_preview_play_pause.setIcon(load_phosphor_icon("pause", 18))
        else:
            self.btn_preview_play_pause.setIcon(load_phosphor_icon("video-camera", 18))
        self._on_preview_tick()
        return True

    def _on_preview_tick(self) -> None:
        """Чтение следующего кадра видео, наложение и отображение в превью (вызывается по таймеру)."""
        if self.preview_base_frame is None or self.preview_cap is None or not self.preview_cap.isOpened():
            return
        item = self.get_current_item()
        if not item:
            return

        ret, frame_bgr = self.preview_cap.read()
        if not ret:
            # Конец ролика — перематываем в начало (зацикливание)
            self.preview_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame_bgr = self.preview_cap.read()
        if not ret:
            return

        # Подгоняем кадр видео под размер базового изображения (3:4), чтобы
        # сохранить точные пропорции экспортируемого кадра.
        base_h, base_w = self.preview_base_frame.shape[:2]
        frame_bgr = cv2.resize(frame_bgr, (base_w, base_h), interpolation=cv2.INTER_AREA)
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        self.preview_last_frame = frame_rgb.copy()
        s = self.slider_curve_shadows.value()
        m = self.slider_curve_midtones.value()
        h = self.slider_curve_highlights.value()
        lut = build_curve_lut(s, m, h)
        curved = apply_curve_lut(frame_rgb, lut)
        blended = screen_blend(self.preview_base_frame, curved)
        try:
            height, width, _ = blended.shape
            bytes_per_line = 3 * width
            blob = np.ascontiguousarray(blended)
            image = QImage(blob.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(image.copy())

            # Важно: сохраняем пропорции карточки.
            # Масштабируем готовый кадр под размер превью с KeepAspectRatio,
            # чтобы картинка не растягивалась по ширине/высоте.
            target_size = self.lbl_image_preview.size()
            if target_size.width() > 0 and target_size.height() > 0:
                pixmap = pixmap.scaled(
                    target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )

            self.lbl_image_preview.setPixmap(pixmap)
            self.lbl_image_preview.setText("")
        except Exception:
            pass
        # Синхронизация ползунка таймлайна с текущим кадром (без рекурсии в valueChanged)
        if not self._preview_slider_syncing and self.preview_cap is not None:
            cur = int(self.preview_cap.get(cv2.CAP_PROP_POS_FRAMES))
            self._preview_slider_syncing = True
            self.slider_preview_timeline.setValue(min(cur, self.slider_preview_timeline.maximum()))
            self._preview_slider_syncing = False

    def _on_preview_timeline_slider_changed(self, value: int) -> None:
        """Перемотка превью по таймлайну (перетаскивание ползунка)."""
        if self._preview_slider_syncing or self.preview_cap is None or not self.preview_cap.isOpened():
            return
        self.preview_cap.set(cv2.CAP_PROP_POS_FRAMES, value)
        self._on_preview_tick()

    def _toggle_preview_play_pause(self) -> None:
        """Переключение пауза/пуск зацикленного превью видео (горячая клавиша Space)."""
        self.preview_playing = not self.preview_playing
        if self.preview_playing:
            self._preview_timer.start()
            self.btn_preview_play_pause.setIcon(load_phosphor_icon("pause", 18))
        else:
            self._preview_timer.stop()
            self.btn_preview_play_pause.setIcon(load_phosphor_icon("video-camera", 18))

    def _update_overlay_preview(self, shadows: int, midtones: int, highlights: int) -> None:
        """Однокадровое обновление превью (при смене слайдеров кривой). При воспроизведении следующий тик применит новую кривую; при паузе перерисовываем текущий кадр."""
        if self.preview_base_frame is None or self.preview_cap is None or not self.preview_cap.isOpened():
            return
        if not self.preview_playing and self.preview_last_frame is not None:
            lut = build_curve_lut(shadows, midtones, highlights)
            curved = apply_curve_lut(self.preview_last_frame, lut)
            blended = screen_blend(self.preview_base_frame, curved)
            blob = np.ascontiguousarray(blended)
            h, w, _ = blended.shape
            image = QImage(blob.data, w, h, 3 * w, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(image.copy())
            target_size = self.lbl_image_preview.size()
            if target_size.width() > 0 and target_size.height() > 0:
                pixmap = pixmap.scaled(
                    target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            self.lbl_image_preview.setPixmap(pixmap)

    def update_image_preview(self, path: str | None) -> None:
        """Обновление превью изображения для выбранной карточки."""
        if not path:
            self.lbl_image_preview.setPixmap(QPixmap())
            self.lbl_image_preview.setText("Нет превью")
            return

        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.lbl_image_preview.setPixmap(QPixmap())
            self.lbl_image_preview.setText("Не удалось загрузить изображение")
            return

        scaled = pixmap.scaled(
            self.lbl_image_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.lbl_image_preview.setPixmap(scaled)
        self.lbl_image_preview.setText("")

    def on_preview_clicked(self) -> None:
        """Предпросмотр видео-карточки для текущей карточки."""
        item = self.get_current_item()
        if not item:
            QMessageBox.information(self, "Нет карточки", "Сначала выберите карточку в списке.")
            return

        # Определяем видео: индивидуальное или общее
        video_path = item.video_path or self.global_video_path
        if not video_path:
            QMessageBox.information(
                self,
                "Нет видео",
                "Для предпросмотра нужно выбрать видео (общее или для этой карточки).",
            )
            return

        try:
            # Создаём временную папку и файл для предпросмотра
            tmp_dir = Path(tempfile.gettempdir()) / "wbo_preview"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            img_name = Path(item.image_path).stem
            preview_path = tmp_dir / f"{img_name}_preview.mp4"

            # Рендерим короткий ролик (например, до 3 секунд)
            try:
                w_str, h_str = self.export_size_str.lower().split("x")
                export_size = (int(w_str), int(h_str))
            except Exception:
                export_size = (900, 1200)

            render_card_video(
                image_path=item.image_path,
                video_path=video_path,
                curve_shadows=item.curve_shadows,
                curve_midtones=item.curve_midtones,
                curve_highlights=item.curve_highlights,
                output_path=str(preview_path),
                max_duration=3.0,
                render_preset=self.render_preset,
                export_size=export_size,
                export_fps=float(self.export_fps),
                export_codec=self.export_codec,
            )

            # Открываем ролик стандартным плеером Windows
            os.startfile(str(preview_path))
        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка предпросмотра",
                f"Не удалось создать предпросмотр:\n{e}",
            )

    def on_preview_video_only_clicked(self) -> None:
        """Просмотр выбранного видео из списка без наложения."""
        current = self.video_list.currentItem()
        if not current:
            QMessageBox.information(self, "Нет видео", "Сначала выберите видео в списке.")
            return

        video_path = current.data(Qt.UserRole)
        if not video_path:
            QMessageBox.information(self, "Нет видео", "Не удалось определить путь к видео.")
            return

        try:
            os.startfile(str(video_path))
        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка открытия видео",
                f"Не удалось открыть видео:\n{e}",
            )

    def on_export_current_clicked(self) -> None:
        """Экспорт только карточки, которая сейчас выбрана в превью (Ctrl+E)."""
        item = self.get_current_item()
        if not item:
            QMessageBox.information(
                self,
                "Нет карточки",
                "Выберите карточку в списке слева (та, что отображается в превью).",
            )
            return
        current_row = self.list_widget.currentRow()
        if current_row < 0:
            return
        self.list_widget.clearSelection()
        self.list_widget.item(current_row).setSelected(True)
        self.on_export_clicked()

    def on_export_selected_clicked(self) -> None:
        """Явный экспорт только выбранных карточек."""
        if not self.list_widget.selectedIndexes():
            QMessageBox.information(
                self,
                "Нет выбранных карточек",
                "Сначала выделите одну или несколько карточек слева.",
            )
            return
        self.on_export_clicked()

    def on_delete_selected_clicked(self) -> None:
        """Удаление выбранных карточек с подтверждением."""
        selected_rows = sorted({idx.row() for idx in self.list_widget.selectedIndexes()})
        if not selected_rows:
            QMessageBox.information(
                self,
                "Нет выбранных карточек",
                "Сначала выделите одну или несколько карточек слева.",
            )
            return

        count = len(selected_rows)
        reply = QMessageBox.question(
            self,
            "Удалить карточки",
            f"Вы действительно хотите удалить {count} выбранн(ую/ые) карточк(у/и)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Удаляем элементы снизу вверх, чтобы индексы не сдвигались
        for row in reversed(selected_rows):
            if 0 <= row < len(self.items):
                del self.items[row]
            item = self.list_widget.takeItem(row)
            del item

        # Обновляем правую панель и превью
        if self.items:
            self.list_widget.setCurrentRow(0)
        else:
            self.lbl_selected_image.setText("Карточка не выбрана")
            self.lbl_selected_video.setText("Видео не выбрано (используется общее)")
            self.update_image_preview(None)
        # После удаления, если выделения нет — прячем кнопку удаления
        self.on_selection_changed()
        self._update_status_state()

    def on_duplicate_selected_clicked(self) -> None:
        """Дублирование выбранных карточек с сохранением настроек (видео, кривая)."""
        selected_rows = sorted({idx.row() for idx in self.list_widget.selectedIndexes()})
        if not selected_rows:
            QMessageBox.information(
                self,
                "Нет выбранных карточек",
                "Выберите одну или несколько карточек для дублирования.",
            )
            return
        start_count = len(self.items)
        for row in selected_rows:
            if row < 0 or row >= len(self.items):
                continue
            orig = self.items[row]
            dup = ImageItemData(orig.image_path)
            dup.video_path = orig.video_path
            dup.curve_shadows = orig.curve_shadows
            dup.curve_midtones = orig.curve_midtones
            dup.curve_highlights = orig.curve_highlights
            self.items.append(dup)
            list_item = QListWidgetItem(Path(dup.image_path).name)
            pixmap = QPixmap(dup.image_path)
            if not pixmap.isNull():
                # Иконка всегда 88×88, чтобы при переключении в вид «Сетка» превью не было размытым
                icon_pixmap = pixmap.scaled(
                    QSize(88, 88),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                list_item.setIcon(icon_pixmap)
            self.list_widget.addItem(list_item)
        # Выделяем добавленные копии
        self.list_widget.clearSelection()
        for i in range(start_count, len(self.items)):
            self.list_widget.item(i).setSelected(True)
        self.on_selection_changed()
        self._update_status_state()

    def _get_items_to_export(self) -> list[ImageItemData]:
        """
        Возвращает список карточек для экспорта.

        Если есть выделенные элементы — берём только их.
        Если выделения нет — берём все карточки.
        """
        if not self.items:
            return []

        selected_rows = sorted({idx.row() for idx in self.list_widget.selectedIndexes()})
        if not selected_rows:
            return list(self.items)

        result: list[ImageItemData] = []
        for row in selected_rows:
            if 0 <= row < len(self.items):
                result.append(self.items[row])
        return result

    def on_export_clicked(self) -> None:
        """Запуск пакетного экспорта видео-карточек."""
        if not self.items:
            QMessageBox.information(self, "Нет карточек", "Сначала загрузите изображения.")
            return
        # Определяем, какие карточки экспортировать: если есть выделение —
        # экспортируем только выбранные, иначе все.
        target_items = self._get_items_to_export()
        if not target_items:
            QMessageBox.information(
                self,
                "Нет выбранных карточек",
                "Нет карточек для экспорта. Выберите карточки или загрузите изображения.",
            )
            return

        if not self.global_video_path and not any(i.video_path for i in target_items):
            QMessageBox.information(
                self,
                "Нет видео",
                "Нужно выбрать хотя бы одно видео (общее или для отдельных карточек).",
            )
            return

        start_dir = self.config.get("last_export_path", str(Path.cwd()))
        export_dir = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для экспорта MP4",
            start_dir,
        )
        if not export_dir:
            return

        # Перед началом экспорта даём пользователю выбрать параметры рендера/кодека.
        settings_dialog = ExportSettingsDialog(
            self, self.export_codec, self.export_size_str, self.export_fps, self.render_preset
        )
        SoundPlayer.play(SOUND_DIALOG)
        if settings_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.export_codec, self.export_size_str, self.export_fps, self.render_preset = settings_dialog.get_values()

        # Если выбран кодек H.264, но ffmpeg не установлен — предлагаем установить через winget.
        if self.export_codec.lower() == "h264" and _find_ffmpeg() is None:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("FFmpeg не найден")
            msg.setText(
                "Для кодека H.264 нужен установленный FFmpeg.\n\n"
                "Можно установить его командой:\n"
                "winget install Gyan.FFmpeg\n\n"
                "Установить FFmpeg сейчас через PowerShell?\n"
                "После установки можно перезапустить приложение."
            )
            btn_install = msg.addButton("Установить через winget", QMessageBox.AcceptRole)
            btn_continue = msg.addButton("Продолжить без H.264", QMessageBox.DestructiveRole)
            btn_cancel = msg.addButton("Отмена", QMessageBox.RejectRole)
            SoundPlayer.play(SOUND_DIALOG)
            msg.exec()

            clicked = msg.clickedButton()
            if clicked == btn_install:
                try:
                    # Открываем PowerShell от имени обычного пользователя
                    os.system(
                        'start "" powershell -NoExit -Command "winget install Gyan.FFmpeg"'
                    )
                except Exception:
                    pass

                restart = QMessageBox.question(
                    self,
                    "Перезапуск приложения",
                    "После успешной установки FFmpeg перезапустить Wbo BAMP?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if restart == QMessageBox.Yes:
                    self._restart_app()
                # Текущий экспорт не выполняем
                return
            elif clicked == btn_cancel:
                return
            else:
                # Продолжить без H.264: принудительно переключаемся на MPEG-4
                self.export_codec = "mpeg4"

        self.config["last_export_path"] = export_dir
        self.config["export_codec"] = self.export_codec
        self.config["export_size"] = self.export_size_str
        self.config["export_fps"] = self.export_fps
        self.config["render_preset"] = self.render_preset
        save_config(self.config)

        # Реальная обработка видео с наложением «Экран»
        # Комментарий: здесь выполняем рендер для каждой выбранной карточки по очереди
        # и показываем прогресс в отдельном окне, похожем на Adobe Media Encoder
        errors: list[str] = []
        success_count = 0

        # Окно прогресса экспорта (кастомная шапка, перетаскивание)
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Экспорт видео-карточек")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        progress_dialog.setStyleSheet(
            "QDialog { background-color: #16181c; border-radius: 6px; }"
            "QLabel { color: #e2e8f0; font-size: 12px; background: transparent; }"
            "QProgressBar { background: transparent; border: 1px solid #334155; "
            "border-radius: 4px; text-align: center; color: #e2e8f0; }"
            "QProgressBar::chunk { background-color: #0ea5e9; border-radius: 4px; }"
            "QPushButton { background: transparent; color: #e2e8f0; border: 1px solid #475569; "
            "border-radius: 4px; padding: 6px 10px; }"
            "QPushButton:hover { background: rgba(71, 85, 105, 0.5); border-color: #64748b; }"
        )

        vbox = QVBoxLayout(progress_dialog)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        vbox.addWidget(DialogTitleBar(progress_dialog, "Экспорт видео-карточек"))

        content_wrap = QWidget()
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(12, 8, 12, 12)
        content_layout.setSpacing(8)

        lbl_current = QLabel("Подготовка экспорта...")
        content_layout.addWidget(lbl_current)

        row_overall = QHBoxLayout()
        lbl_overall = QLabel("Общий прогресс:")
        row_overall.addWidget(lbl_overall)
        bar_overall = QProgressBar()
        bar_overall.setRange(0, 100)
        bar_overall.setTextVisible(True)
        row_overall.addWidget(bar_overall)
        content_layout.addLayout(row_overall)

        row_item = QHBoxLayout()
        lbl_item = QLabel("Текущая карточка:")
        row_item.addWidget(lbl_item)
        bar_item = QProgressBar()
        bar_item.setRange(0, 100)
        bar_item.setTextVisible(True)
        row_item.addWidget(bar_item)
        content_layout.addLayout(row_item)

        lbl_time = QLabel("Прошло: 00:00    Осталось ~--:--")
        content_layout.addWidget(lbl_time)

        btn_cancel = QPushButton("Отмена после текущей карточки")
        content_layout.addWidget(btn_cancel)

        vbox.addWidget(content_wrap)
        QShortcut(QKeySequence("Escape"), progress_dialog, progress_dialog.reject)

        cancel_requested = False

        def on_cancel_clicked() -> None:
            nonlocal cancel_requested
            cancel_requested = True

        btn_cancel.clicked.connect(on_cancel_clicked)

        progress_dialog.resize(340, 180)
        SoundPlayer.play(SOUND_DIALOG)
        progress_dialog.show()

        total_items = len(target_items)
        export_start = time.monotonic()

        for idx, item in enumerate(target_items, start=1):
            if cancel_requested:
                break

            # Определяем, какое видео использовать для этой карточки
            video_path = item.video_path or self.global_video_path
            if not video_path:
                # Если вообще нет видео — пропускаем карточку
                errors.append(
                    f"Карточка {item.image_path}: видео не выбрано (ни общее, ни индивидуальное)."
                )
                continue

            try:
                # Имя выходного файла: имя картинки + _anim.mp4
                img_name = Path(item.image_path).stem
                out_path = build_unique_output_path(export_dir, img_name)

                # Обновляем информацию по текущей карточке
                lbl_current.setText(f"Экспорт карточки {idx}/{total_items}:\n{item.image_path}")
                bar_item.setValue(0)
                QApplication.processEvents()

                # Вызываем функцию рендера одной карточки с колбэком прогресса
                def progress_callback(done_frames: int, total_frames: int) -> None:
                    if total_frames <= 0:
                        return
                    fraction_item = done_frames / float(total_frames)
                    bar_item.setValue(int(fraction_item * 100))

                    # Общий прогресс по всем карточкам
                    overall_fraction = ((idx - 1) + fraction_item) / float(total_items)
                    bar_overall.setValue(int(overall_fraction * 100))

                    # Оценка времени
                    elapsed = time.monotonic() - export_start
                    if overall_fraction > 0:
                        total_estimated = elapsed / overall_fraction
                        remaining = max(0.0, total_estimated - elapsed)
                        remaining_str = format_time(remaining)
                    else:
                        remaining_str = "--:--"
                    lbl_time.setText(
                        f"Прошло: {format_time(elapsed)}    Осталось ~{remaining_str}"
                    )

                    # Даем Qt возможность обновить окно
                    QApplication.processEvents()

                # Преобразуем строковый размер "WxH" в числовой кортеж
                try:
                    w_str, h_str = self.export_size_str.lower().split("x")
                    export_size = (int(w_str), int(h_str))
                except Exception:
                    export_size = (900, 1200)

                render_card_video(
                    image_path=item.image_path,
                    video_path=video_path,
                    curve_shadows=item.curve_shadows,
                    curve_midtones=item.curve_midtones,
                    curve_highlights=item.curve_highlights,
                    output_path=out_path,
                    max_duration=8.0,
                    progress_callback=progress_callback,
                    render_preset=self.render_preset,
                    export_size=export_size,
                    export_fps=float(self.export_fps),
                    export_codec=self.export_codec,
                )
                success_count += 1
            except Exception as e:
                # Не прерываем весь процесс, просто копим ошибки
                errors.append(f"Карточка {item.image_path}: ошибка рендера: {e}")

        progress_dialog.close()

        # Воспроизводим звук по результату, когда общий прогресс уже дошёл до конца
        if not cancel_requested:
            if errors:
                SoundPlayer.play(SOUND_EXPORT_ERROR)
            else:
                SoundPlayer.play(SOUND_EXPORT_READY)

        # Показываем итог в кастомном диалоге с шапкой
        if errors:
            msg = f"Успешно экспортировано карточек: {success_count}.\n\n"
            msg += "Часть карточек не удалось обработать:\n\n"
            msg += "\n".join(errors)
            result_dlg = QDialog(self)
            result_dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
            result_dlg.setStyleSheet(
                "QDialog { background-color: #16181c; border-radius: 6px; }"
                "QLabel { color: #e2e8f0; font-size: 12px; background: transparent; }"
                "QPushButton { background: transparent; color: #e2e8f0; border: 1px solid #475569; border-radius: 4px; padding: 6px 12px; }"
                "QPushButton:hover { background: rgba(71, 85, 105, 0.5); }"
            )
            rly = QVBoxLayout(result_dlg)
            rly.setContentsMargins(0, 0, 0, 0)
            rly.setSpacing(0)
            rly.addWidget(DialogTitleBar(result_dlg, "Экспорт завершён с ошибками"))
            r_content = QWidget()
            r_ly = QVBoxLayout(r_content)
            r_ly.setContentsMargins(12, 8, 12, 12)
            r_lbl = QLabel(msg)
            r_lbl.setWordWrap(True)
            r_ly.addWidget(r_lbl)
            r_btn = QPushButton("ОК")
            r_btn.clicked.connect(result_dlg.accept)
            r_ly.addWidget(r_btn, alignment=Qt.AlignRight)
            rly.addWidget(r_content)
            QShortcut(QKeySequence("Escape"), result_dlg, result_dlg.accept)
            result_dlg.resize(420, 280)
            SoundPlayer.play(SOUND_DIALOG)
            result_dlg.exec()
        else:
            result_dlg = QDialog(self)
            result_dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
            result_dlg.setStyleSheet(
                "QDialog { background-color: #16181c; border-radius: 6px; }"
                "QLabel { color: #e2e8f0; font-size: 12px; background: transparent; }"
                "QPushButton { background: transparent; color: #e2e8f0; border: 1px solid #475569; border-radius: 4px; padding: 6px 12px; }"
                "QPushButton:hover { background: rgba(71, 85, 105, 0.5); }"
                "QPushButton[class=primary] { border-color: #0d7377; color: #0d7377; }"
                "QPushButton[class=primary]:hover { background: rgba(13, 115, 119, 0.25); border-color: #0e8a8f; color: #0e8a8f; }"
            )
            rly = QVBoxLayout(result_dlg)
            rly.setContentsMargins(0, 0, 0, 0)
            rly.setSpacing(0)
            rly.addWidget(DialogTitleBar(result_dlg, "Экспорт завершён"))
            r_content = QWidget()
            r_ly = QVBoxLayout(r_content)
            r_ly.setContentsMargins(12, 8, 12, 12)
            r_ly.addWidget(QLabel(f"Успешно экспортировано карточек: {success_count}."))
            r_btns = QHBoxLayout()
            r_btns.addStretch(1)
            btn_ok = QPushButton("ОК")
            btn_ok.clicked.connect(result_dlg.accept)
            btn_open = QPushButton("Открыть папку")
            btn_open.setProperty("class", "primary")
            def _open_and_close() -> None:
                try:
                    os.startfile(export_dir)
                except Exception:
                    pass
                result_dlg.accept()
            btn_open.clicked.connect(_open_and_close)
            r_btns.addWidget(btn_ok)
            r_btns.addWidget(btn_open)
            r_ly.addLayout(r_btns)
            rly.addWidget(r_content)
            QShortcut(QKeySequence("Escape"), result_dlg, result_dlg.accept)
            result_dlg.resize(360, 140)
            SoundPlayer.play(SOUND_DIALOG)
            SoundPlayer.play(SOUND_EXPORT_READY)
            result_dlg.exec()


def screen_blend(base_frame: np.ndarray, overlay_frame: np.ndarray) -> np.ndarray:
    """
    Наложение двух кадров в режиме «Экран».

    base_frame  — фон (карточка, изображение)
    overlay_frame — накладываемое видео

    Формула Screen в нормализованном виде:
    result = 1 - (1 - A) * (1 - B)
    где A — фон, B — накладываемый слой.
    """
    # Переводим в float и нормализуем к [0, 1]
    a = base_frame.astype(np.float32) / 255.0
    b = overlay_frame.astype(np.float32) / 255.0
    # Применяем формулу Screen
    result = 1.0 - (1.0 - a) * (1.0 - b)
    # Возвращаем в uint8
    result = np.clip(result * 255.0, 0, 255).astype(np.uint8)
    return result


def _screen_blend_fast(base_frame: np.ndarray, overlay_frame: np.ndarray) -> np.ndarray:
    """
    Быстрое наложение «Экран» в целочисленной арифметике (для экспорта).
    Формула: R = A + B - (A*B)//255. Визуально почти не отличается от точной.
    """
    a = base_frame.astype(np.uint16)
    b = overlay_frame.astype(np.uint16)
    r = a + b - (a * b // 255)
    return np.minimum(r, 255).astype(np.uint8)


def build_curve_lut(shadows: int, midtones: int, highlights: int) -> np.ndarray:
    """
    Построение LUT (256 значений) по трём точкам кривой.

    Точки: вход 0 -> 0; 64 -> shadows; 128 -> midtones; 192 -> highlights; 255 -> 255.
    Между точками — линейная интерполяция (как базовая кривая в стиле Photoshop).
    """
    x = np.array([0, 64, 128, 192, 255], dtype=np.float64)
    y = np.array(
        [0, max(0, min(255, shadows)), max(0, min(255, midtones)), max(0, min(255, highlights)), 255],
        dtype=np.float64,
    )
    lut = np.interp(np.arange(256), x, y).astype(np.uint8)
    return lut


def apply_curve_lut(frame: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Применение LUT кривой к кадру (RGB, uint8). Каждый канал прогоняем через LUT."""
    return lut[frame]


def format_time(seconds: float) -> str:
    """Форматирование секунд в строку MM:SS."""
    total_seconds = max(0, int(seconds))
    minutes, secs = divmod(total_seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


def build_unique_output_path(export_dir: str, img_name: str) -> str:
    """
    Построение уникального пути для файла экспорта.

    Правила:
    - если файла `<name>_anim.mp4` ещё нет — используем его;
    - если есть — пробуем `<name>_anim_2.mp4`, потом `_3` и т.д.,
      пока не найдём свободное имя.
    """
    base = Path(export_dir) / f"{img_name}_anim.mp4"
    if not base.exists():
        return str(base)

    counter = 2
    while True:
        candidate = Path(export_dir) / f"{img_name}_anim_{counter}.mp4"
        if not candidate.exists():
            return str(candidate)
        counter += 1


def _find_ffmpeg() -> str | None:
    """
    Путь к ffmpeg, если установлен (для быстрого кодирования H.264).

    Важно: winget-пакет Gyan.FFmpeg устанавливает ffmpeg как портативное
    приложение в папку WinGet Packages и не всегда прописывает путь в PATH,
    поэтому одного shutil.which здесь недостаточно.
    """
    # 1. Обычный поиск в PATH
    exe = shutil.which("ffmpeg")
    if exe:
        return exe

    # 2. Если не нашли, пробуем стандартный путь winget-пакета Gyan.FFmpeg
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        base = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
        try:
            if base.exists():
                # Ищем каталог пакета Gyan.FFmpeg_*
                for pkg_dir in base.glob("Gyan.FFmpeg_*"):
                    # Внутри пакета лежит папка вида ffmpeg-*-full_build/bin/ffmpeg.exe
                    for ff_dir in pkg_dir.glob("ffmpeg-*full_build"):
                        candidate = ff_dir / "bin" / "ffmpeg.exe"
                        if candidate.exists():
                            return str(candidate)
        except Exception:
            # Любые проблемы при обходе WinGet-папок не должны ломать приложение
            pass

    # 3. Попытка угадать типичные ручные пути установки
    common_paths = [
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
    ]
    for p in common_paths:
        try:
            if p.exists():
                return str(p)
        except Exception:
            continue

    return None


def render_card_video(
    image_path: str,
    video_path: str,
    curve_shadows: int,
    curve_midtones: int,
    curve_highlights: int,
    output_path: str,
    max_duration: float = 8.0,
    progress_callback=None,
    render_preset: str = "balanced",
    *,
    export_size: tuple[int, int] = (900, 1200),
    export_fps: float = 60.0,
    export_codec: str = "h264",
) -> None:
    """
    Рендер одной видео-карточки на базе OpenCV.

    render_preset: "quality" (медленно, лучше картинка), "balanced", "fast" (максимально быстро).
    export_size: итоговый размер кадра (ширина, высота), по умолчанию 900x1200.
    export_fps: целевая частота кадров (24 / 30 / 60), по умолчанию 60.
    export_codec: логическое имя кодека ("h264", "mpeg4" и т.п.).

    В режиме "fast" обработка идёт в половинном разрешении, затем апскейл до export_size.
    """
    # Итоговый размер вывода (OpenCV: ширина, высота)
    out_w, out_h = export_size

    if render_preset == "quality":
        interp = cv2.INTER_AREA
        use_fast_blend = False
        ffmpeg_preset = "medium"
        progress_interval = 5
        process_w, process_h = out_w, out_h
        upscale_output = False
    elif render_preset == "fast":
        interp = cv2.INTER_NEAREST
        use_fast_blend = True
        ffmpeg_preset = "ultrafast"
        progress_interval = 40
        # Обработка в половинном разрешении — в ~4 раза меньше пикселей, затем апскейл
        process_w, process_h = max(1, out_w // 2), max(1, out_h // 2)
        upscale_output = True
    else:
        interp = cv2.INTER_LINEAR
        use_fast_blend = True
        ffmpeg_preset = "veryfast"
        progress_interval = 12
        process_w, process_h = out_w, out_h
        upscale_output = False

    target_w, target_h = process_w, process_h

    # Загружаем фон-картинку через Pillow
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            img = img.resize((target_w, target_h), Image.LANCZOS)
            base_frame = np.array(img)
    except Exception as e:
        # Комментарий: если картинка не прочиталась, считаем это ошибкой
        raise RuntimeError(f"Не удалось прочитать изображение: {image_path}. Детали: {e}")

    # Открываем видео
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Не удалось открыть видео: {video_path}")

    # Для экспорта всегда используем фиксированный FPS (24 / 30 / 60),
    # чтобы ролики были единообразными независимо от исходного видео.
    fps = float(export_fps) if export_fps and export_fps > 0 else 60.0

    # Считаем максимальное число кадров (не более 8 секунд и не более max_duration)
    effective_duration = min(8.0, max_duration)
    max_frames = int(fps * effective_duration)

    # Строим LUT кривой один раз для всего ролика
    curve_lut = build_curve_lut(curve_shadows, curve_midtones, curve_highlights)

    # Кодирование в H.264 (AVC) или альтернативный кодек.
    ffmpeg_exe = _find_ffmpeg()
    use_ffmpeg = ffmpeg_exe is not None

    write_w, write_h = out_w, out_h
    # Подбираем реальные параметры кодека под выбранное логическое имя
    codec = (export_codec or "h264").lower()
    if codec == "mpeg4":
        ffmpeg_codec = "mpeg4"
        fourcc_candidates = ("mp4v", "XVID", "DIVX")
    else:
        # По умолчанию H.264
        ffmpeg_codec = "libx264"
        fourcc_candidates = ("avc1", "H264", "mp4v")

    if use_ffmpeg:
        cmd = [
            ffmpeg_exe,
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{write_w}x{write_h}",
            "-r",
            str(fps),
            "-i",
            "pipe:0",
            "-c:v",
            ffmpeg_codec,
            "-profile:v",
            "main",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            ffmpeg_preset,
            "-crf",
            "23",
            "-y",
            output_path,
        ]
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
            )
        except Exception as e:
            use_ffmpeg = False
            proc = None
    else:
        proc = None

    if not use_ffmpeg or proc is None:
        # Запись через OpenCV: подбираем fourcc под выбранный кодек
        for fourcc_code in fourcc_candidates:
            fourcc = cv2.VideoWriter_fourcc(*fourcc_code)
            out = cv2.VideoWriter(output_path, fourcc, fps, (write_w, write_h))
            if out.isOpened():
                break
        else:
            cap.release()
            raise RuntimeError(f"Не удалось открыть файл для записи: {output_path}")
    else:
        out = None

    frames_written = 0

    try:
        while frames_written < max_frames:
            ret, frame_bgr = cap.read()
            if not ret:
                break

            # Приводим кадр к нужному размеру (интерполяция по режиму)
            frame_bgr = cv2.resize(frame_bgr, (target_w, target_h), interpolation=interp)
            # Переводим в RGB для обработки
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

            curved = apply_curve_lut(frame_rgb, curve_lut)
            blended_rgb = (
                _screen_blend_fast(base_frame, curved)
                if use_fast_blend
                else screen_blend(base_frame, curved)
            )

            blended_bgr = cv2.cvtColor(blended_rgb, cv2.COLOR_RGB2BGR)
            if upscale_output:
                blended_bgr = cv2.resize(blended_bgr, (write_w, write_h), interpolation=cv2.INTER_LINEAR)

            if use_ffmpeg and proc is not None and proc.stdin is not None:
                proc.stdin.write(np.ascontiguousarray(blended_bgr).tobytes())
            elif out is not None:
                out.write(blended_bgr)

            frames_written += 1
            # Обновляем прогресс раз в N кадров (N зависит от режима рендера)
            if progress_callback is not None and (
                frames_written % progress_interval == 0 or frames_written == max_frames
            ):
                try:
                    progress_callback(frames_written, max_frames)
                except Exception:
                    pass

        # Финальное обновление прогресса (на случай раннего выхода из цикла)
        if progress_callback is not None and frames_written > 0:
            try:
                progress_callback(frames_written, max_frames)
            except Exception:
                pass
    finally:
        cap.release()
        if out is not None:
            out.release()
        if use_ffmpeg and proc is not None and proc.stdin is not None:
            proc.stdin.close()
            _, stderr = proc.communicate(timeout=60)
            if proc.returncode != 0:
                raise RuntimeError(
                    f"Ошибка ffmpeg при кодировании: {stderr.decode(errors='replace') if stderr else 'unknown'}"
                )

    if frames_written == 0:
        raise RuntimeError("Видео не содержит ни одного кадра для записи.")


def main() -> None:
    """Точка входа в приложение."""
    # Важно: политику масштабирования DPI задаём до создания QApplication,
    # иначе Qt выводит предупреждение в консоль.
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        # Если по какой-то причине метод недоступен в текущей версии Qt — просто игнорируем.
        pass

    app = QApplication([])
    # Путь к стрелке комбобокса (в кавычках для стилей; Qt на Windows лучше грузит по пути с /)
    _chevron = (ICONS_DIR / "chevron-down.svg").resolve()
    chevron_path = str(_chevron).replace("\\", "/") if _chevron.exists() else ""
    _check = (ICONS_DIR / "check.svg").resolve()
    check_path = str(_check).replace("\\", "/") if _check.exists() else ""
    app.setStyleSheet(
        APP_STYLESHEET.replace("{{CHEVRON_DOWN}}", chevron_path).replace("{{CHECK_ICON}}", check_path)
    )
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))

    # Загрузка шрифтов из Assets/fonts
    global _google_sans_family, _unbounded_family
    for name, key in [
        ("GoogleSans-VariableFont_GRAD,opsz,wght.ttf", "_google_sans_family"),
        ("Unbounded-VariableFont_wght.ttf", "_unbounded_family"),
    ]:
        path = FONTS_DIR / name
        if path.exists():
            fid = QFontDatabase.addApplicationFont(str(path))
            if fid != -1:
                families = QFontDatabase.applicationFontFamilies(fid)
                if families:
                    globals()[key] = families[0]
    if _google_sans_family:
        app.setFont(QFont(_google_sans_family, 13))

    # Прелоад-окно (splash): фирменный арт + информация, как на референсе
    splash_w, splash_h = 1024, 584
    splash_pix = QPixmap(splash_w, splash_h)
    splash_pix.fill(QColor("#020617"))
    # Основной арт для сплэша (как на референсе); если его нет — используем старый фон
    bg_path = BASE_DIR / "Assets" / "images" / "splash_banka.png"
    if not bg_path.exists():
        bg_path = BASE_DIR / "Assets" / "images" / "bg.webp"
    if bg_path.exists():
        try:
            with Image.open(bg_path) as img:
                img = img.convert("RGB")
                img = img.resize((splash_w, splash_h), Image.LANCZOS)
                arr = np.array(img)
                h, w, _ = arr.shape
                blob = np.ascontiguousarray(arr)
                qimg = QImage(blob.data, w, h, 3 * w, QImage.Format.Format_RGB888)
                bg_pix = QPixmap.fromImage(qimg.copy())
                if not bg_pix.isNull():
                    painter_bg = QPainter(splash_pix)
                    painter_bg.drawPixmap(0, 0, bg_pix)
                    painter_bg.end()
        except Exception:
            pass
    # На сплэше больше нет текста — только сам арт и лоадбар.
    # Оставляем try/except на случай проблем с изображением.
    try:
        _ = splash_pix.width()  # заглушка, чтобы блок не был пустым
    except Exception:
        pass

    # Базовое изображение сплэша для анимации прогресс-бара
    base_splash = splash_pix.copy()

    # Звук запуска бренда на время показа сплэш-экрана
    SoundPlayer.play(SOUND_SPLASH_BANKA)

    splash = QSplashScreen(base_splash)
    splash.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    splash.show()
    app.processEvents()

    start_ts = time.monotonic()
    duration = 6.0
    while True:
        elapsed = time.monotonic() - start_ts
        progress = max(0.0, min(1.0, elapsed / duration))

        # Рисуем анимированный прогресс-бар снизу с лёгким свечением
        frame = base_splash.copy()
        try:
            p = QPainter(frame)
            p.setRenderHint(QPainter.Antialiasing)
            bar_margin = 40
            bar_height = 6
            bar_y = frame.height() - 28
            bar_rect_w = frame.width() - 2 * bar_margin
            # фон бара
            p.fillRect(bar_margin, bar_y, bar_rect_w, bar_height, QColor(15, 23, 42, 180))
            # заполненная часть
            fill_w = max(0, int(bar_rect_w * progress) - 2)
            if fill_w > 0:
                # Свечение вокруг активной части: чуть выше/ниже и шире, полупрозрачное
                glow_alpha = int(80 + 70 * progress)
                glow_color = QColor(14, 165, 233, glow_alpha)  # голубой с альфой
                p.fillRect(
                    bar_margin - 2,
                    bar_y - 3,
                    fill_w + 6,
                    bar_height + 6,
                    glow_color,
                )
                # Основная полоса прогресса
                p.fillRect(bar_margin + 1, bar_y + 1, fill_w, bar_height - 2, QColor("#0ea5e9"))
            p.end()
        except Exception:
            frame = base_splash

        splash.setPixmap(frame)
        app.processEvents()

        if elapsed >= duration:
            break
        time.sleep(0.01)

    # Останавливаем брендовый звук, даже если он длиннее, чем сплэш
    SoundPlayer.stop()

    window = MainWindow()
    window.show()
    splash.finish(window)
    # Звук старта интерфейса после прелоада
    SoundPlayer.play(SOUND_OPEN)
    app.exec()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication([])
            QMessageBox.critical(None, "Wbo BAMP — ошибка запуска", str(e) + "\n\n" + err)
        except Exception:
            print(err)
            input("Press Enter to close...")
        raise

