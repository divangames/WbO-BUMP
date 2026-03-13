import os
import sys
import json
import time  # Для расчёта времени экспорта
from pathlib import Path
import tempfile  # Для временных файлов предпросмотра

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
)
from PySide6.QtCore import Qt, QSize, QUrl, QTimer, QByteArray

try:
    from PySide6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


# ВАЖНО: комментарии всегда на русском, не удалять при доработках

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

ICONS_DIR = BASE_DIR / "Assets" / "icons"


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


# Стиль в духе Figma: плоский тёмный интерфейс, минималистичные контролы
APP_STYLESHEET = """
    QMainWindow, QWidget {
        background-color: #1F2125;
        color: #F9FAFB;
        font-size: 12px;
    }
    QMenuBar {
        background-color: #18191C;
        color: #E5E7EB;
    }
    QMenuBar::item {
        padding: 4px 10px;
        background: transparent;
    }
    QMenuBar::item:selected {
        background: #272B33;
    }
    QMenu {
        background-color: #18191C;
        color: #E5E7EB;
        border: 1px solid #2D323B;
    }
    QMenu::item {
        padding: 6px 16px;
    }
    QMenu::item:selected {
        background: #2D323B;
    }
    QLabel {
        color: #E5E7EB;
        font-size: 12px;
    }
    QLabel#sectionLabel {
        color: #9CA3AF;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    QPushButton {
        background-color: #2D323B;
        color: #E5E7EB;
        border: 1px solid #3B4250;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 12px;
    }
    QPushButton:hover {
        background-color: #353B47;
        border-color: #4B5563;
    }
    QPushButton:pressed {
        background-color: #23262F;
    }
    QPushButton:disabled {
        color: #6B7280;
        background-color: #1F2933;
        border-color: #374151;
    }
    QPushButton[class=\"primary\"] {
        background-color: #0ea5e9;
        border-color: #0ea5e9;
        color: #020617;
        font-weight: 500;
    }
    QPushButton[class=\"primary\"]:hover {
        background-color: #38bdf8;
        border-color: #38bdf8;
    }
    QListWidget {
        background-color: #181B20;
        border: 1px solid #272B33;
        border-radius: 8px;
        padding: 6px;
        color: #E5E7EB;
        font-size: 12px;
    }
    QListWidget::item {
        padding: 6px;
        border-radius: 4px;
    }
    QListWidget::item:selected {
        background-color: #0ea5e9;
        color: #020617;
    }
    QListWidget::item:hover:!selected {
        background-color: #272B33;
    }
    QSlider::groove:horizontal {
        height: 4px;
        background: #111827;
        border-radius: 2px;
    }
    QSlider::sub-page:horizontal {
        background: #0ea5e9;
        border-radius: 2px;
    }
    QSlider::handle:horizontal {
        width: 14px;
        height: 14px;
        margin: -5px 0;
        background: #F9FAFB;
        border-radius: 7px;
        border: 1px solid #0ea5e9;
    }
    QSlider::handle:horizontal:hover {
        background: #E5E7EB;
    }
    QCheckBox {
        color: #E5E7EB;
        spacing: 6px;
        font-size: 12px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #4B5563;
        border-radius: 4px;
        background: #111827;
    }
    QCheckBox::indicator:checked {
        background: #0ea5e9;
        border-color: #0ea5e9;
    }
    QComboBox {
        background-color: #181B20;
        color: #E5E7EB;
        border: 1px solid #3B4250;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
        min-height: 24px;
    }
    QComboBox:hover {
        border-color: #4B5563;
    }
    QComboBox::drop-down {
        border: none;
        width: 22px;
    }
    QComboBox QAbstractItemView {
        background: #111827;
        color: #E5E7EB;
        selection-background-color: #0ea5e9;
        selection-color: #020617;
        border-radius: 6px;
    }
    QFrame#panel {
        background-color: #181B20;
        border: 1px solid #272B33;
        border-radius: 10px;
        margin: 4px 0;
        padding: 12px;
    }
    QScrollArea {
        border: none;
        background: transparent;
    }
"""


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


CONFIG_FILE = "wbo_config.json"


def load_config() -> dict:
    """Загрузка конфигурации приложения (последний путь экспорта и т.п.)."""
    # Комментарии на русском: если файл не найден, возвращаем конфиг по умолчанию
    if not os.path.exists(CONFIG_FILE):
        return {
            "last_export_path": str(Path.cwd()),
            "last_images_path": str(Path("Assets/demo").resolve()),
            "last_video_path": str(Path("Assets/video").resolve()),
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

        # Конфигурация (пути и т.п.)
        self.config = load_config()

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
        self.preview_last_frame: np.ndarray | None = None  # последний кадр для перерисовки при паузе
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._on_preview_tick)

        # Режимы предпросмотра (разрешение превью, влияет только на скорость и качество просмотра)
        # Экспорт по-прежнему делается в 900x1200.
        self.preview_target_w = 540
        self.preview_target_h = 720

        self.setWindowTitle("WBO Animation - генератор видео-карточек")
        self.resize(1000, 600)

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
        """При закрытии окна останавливаем превью-видео и освобождаем ресурсы."""
        self._stop_preview_video()
        super().closeEvent(event)

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

    def load_video_list(self) -> None:
        """Загрузка списка видео из папки Assets/video."""
        video_dir = BASE_DIR / "Assets" / "video"
        self.video_list.clear()
        if not video_dir.exists():
            # Комментарий: если папки пока нет, просто не показываем элементы
            return

        for p in sorted(video_dir.iterdir()):
            if p.suffix.lower() == ".mp4":
                item = QListWidgetItem(p.name)
                item.setData(Qt.UserRole, str(p.resolve()))
                self.video_list.addItem(item)

        # Если есть элементы и глобальное видео ещё не выбрано — выбираем первый
        if self.video_list.count() > 0 and not self.global_video_path:
            self.video_list.setCurrentRow(0)

    def _build_ui(self) -> None:
        """Построение интерфейса в стиле Adobe: панели, иконки Phosphor, тёмная тема."""
        central = QWidget(self)
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Левая панель — карточки
        self.left_panel = QFrame()
        self.left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        section_cards = QLabel("Карточки")
        section_cards.setObjectName("sectionLabel")
        header_layout.addWidget(section_cards)

        self.cards_view_mode = QComboBox()
        self.cards_view_mode.addItems(["Сетка превью", "Список"])
        self.cards_view_mode.currentIndexChanged.connect(self.on_cards_view_mode_changed)
        header_layout.addWidget(self.cards_view_mode)

        header_layout.addStretch(1)

        # Компактный тулбар с иконками: загрузка / экспорт / удаление
        btn_load_images = QPushButton()
        btn_load_images.setToolTip("Загрузить изображения...")
        btn_load_images.setIcon(load_phosphor_icon("folder-open", 18))
        btn_load_images.setIconSize(QSize(18, 18))
        btn_load_images.clicked.connect(self.on_load_images_clicked)
        header_layout.addWidget(btn_load_images)

        btn_export_selected = QPushButton()
        btn_export_selected.setToolTip("Экспортировать выбранные карточки")
        btn_export_selected.setIcon(load_phosphor_icon("export", 18))
        btn_export_selected.setIconSize(QSize(18, 18))
        btn_export_selected.clicked.connect(self.on_export_selected_clicked)
        header_layout.addWidget(btn_export_selected)

        self.btn_delete_selected = QPushButton()
        self.btn_delete_selected.setToolTip("Удалить выбранные карточки")
        self.btn_delete_selected.setIcon(load_phosphor_icon("trash", 18))
        self.btn_delete_selected.setIconSize(QSize(18, 18))
        self.btn_delete_selected.clicked.connect(self.on_delete_selected_clicked)
        self.btn_delete_selected.setVisible(False)
        header_layout.addWidget(self.btn_delete_selected)

        left_layout.addLayout(header_layout)

        self.list_widget = ImageListWidget(self)
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(96, 96))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Static)
        left_layout.addWidget(self.list_widget, 1)

        main_layout.addWidget(self.left_panel, 2)

        # Центральная колонка — большое превью карточки
        self.center_panel = QFrame()
        self.center_panel.setObjectName("panel")
        center_layout = QVBoxLayout(self.center_panel)
        center_layout.setSpacing(8)

        # Заголовок + режим предпросмотра (разрешение)
        header_preview = QHBoxLayout()
        lbl_preview_sec = QLabel("Превью карточки")
        lbl_preview_sec.setObjectName("sectionLabel")
        header_preview.addWidget(lbl_preview_sec)
        header_preview.addStretch(1)

        self.preview_mode_combo = QComboBox()
        self.preview_mode_combo.addItem("540x720 (быстрый просмотр)", (540, 720))
        self.preview_mode_combo.addItem("720x960 (стандартный просмотр)", (720, 960))
        self.preview_mode_combo.addItem("900x1200 (исходный материал)", (900, 1200))
        self.preview_mode_combo.setCurrentIndex(0)  # по умолчанию быстрый просмотр
        self.preview_mode_combo.currentIndexChanged.connect(self._on_preview_mode_changed)
        header_preview.addWidget(self.preview_mode_combo)

        center_layout.addLayout(header_preview)
        self.lbl_image_preview = QLabel()
        # Превью должно масштабироваться при разворачивании окна, поэтому
        # задаём минимальный размер и разрешаем растягивание.
        self.lbl_image_preview.setMinimumSize(300, 400)
        self.lbl_image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_image_preview.setStyleSheet("background-color: #1e1e1e; border: 1px solid #3d3d3d; border-radius: 4px;")
        self.lbl_image_preview.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.lbl_image_preview)
        center_layout.addSpacing(4)
        self.btn_preview_play_pause = QPushButton()
        self.btn_preview_play_pause.setToolTip("Пауза / пуск предпросмотра")
        # Иконки: pause.svg для паузы, video-camera.svg для воспроизведения
        self.btn_preview_play_pause.setIcon(load_phosphor_icon("pause", 18))
        self.btn_preview_play_pause.setIconSize(QSize(18, 18))
        self.btn_preview_play_pause.setFixedSize(32, 28)
        self.btn_preview_play_pause.clicked.connect(self._toggle_preview_play_pause)
        center_layout.addWidget(self.btn_preview_play_pause, alignment=Qt.AlignHCenter)
        center_layout.addStretch(1)
        main_layout.addWidget(self.center_panel, 3)

        # Правая часть — скроллируемая область с настройками
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.setSpacing(12)

        # Панель видео
        video_panel = QFrame()
        video_panel.setObjectName("panel")
        video_pl = QVBoxLayout(video_panel)

        # Заголовок + кнопка обновления в правом углу
        video_header = QHBoxLayout()
        lbl_video = QLabel("Список видео (Assets/video)")
        lbl_video.setObjectName("sectionLabel")
        video_header.addWidget(lbl_video)
        video_header.addStretch(1)
        btn_refresh_videos = QPushButton()
        btn_refresh_videos.setToolTip("Обновить список видео")
        btn_refresh_videos.setIcon(load_phosphor_icon("arrows-clock", 18))
        btn_refresh_videos.setIconSize(QSize(18, 18))
        btn_refresh_videos.clicked.connect(self.on_refresh_videos_clicked)
        video_header.addWidget(btn_refresh_videos)
        video_pl.addLayout(video_header)

        self.video_list = QListWidget()
        self.video_list.setMaximumHeight(140)
        self.video_list.currentItemChanged.connect(self.on_video_selected)
        video_pl.addWidget(self.video_list)
        self.chk_single_video = QCheckBox("Один ролик для всех карточек")
        self.chk_single_video.setChecked(True)
        video_pl.addWidget(self.chk_single_video)
        video_pl.addWidget(QLabel("Общее видео:"))
        self.lbl_global_video = QLabel("Не выбрано")
        self.lbl_global_video.setWordWrap(True)
        video_pl.addWidget(self.lbl_global_video)
        right_layout.addWidget(video_panel)

        # Панель настроек карточки
        card_panel = QFrame()
        card_panel.setObjectName("panel")
        card_pl = QVBoxLayout(card_panel)
        card_pl.addWidget(QLabel("Выбранная карточка"))
        self.lbl_selected_image = QLabel("Карточка не выбрана")
        self.lbl_selected_image.setWordWrap(True)
        card_pl.addWidget(self.lbl_selected_image)
        self.lbl_selected_video = QLabel("Видео: общее")
        self.lbl_selected_video.setWordWrap(True)
        card_pl.addWidget(self.lbl_selected_video)
        right_layout.addWidget(card_panel)

        # Панель кривой
        curve_panel = QFrame()
        curve_panel.setObjectName("panel")
        curve_pl = QVBoxLayout(curve_panel)
        curve_sec = QLabel("Кривая (тени / средние / света)")
        curve_sec.setObjectName("sectionLabel")
        curve_pl.addWidget(curve_sec)

        # Верхний ряд: график слева, ползунки справа — как в профессиональных панелях
        curve_top = QHBoxLayout()
        self.lbl_curve_preview = QLabel()
        self.lbl_curve_preview.setFixedSize(200, 200)
        self.lbl_curve_preview.setStyleSheet("background-color: #1e1e1e; border: 1px solid #3d3d3d; border-radius: 4px;")
        self.lbl_curve_preview.setAlignment(Qt.AlignCenter)
        curve_top.addWidget(self.lbl_curve_preview)

        sliders_col = QVBoxLayout()
        self.lbl_curve_shadows = QLabel("Тени: 64")
        sliders_col.addWidget(self.lbl_curve_shadows)
        self.slider_curve_shadows = QSlider(Qt.Horizontal)
        self.slider_curve_shadows.setMinimum(0)
        self.slider_curve_shadows.setMaximum(255)
        self.slider_curve_shadows.setValue(64)
        self.slider_curve_shadows.valueChanged.connect(self.on_curve_shadows_changed)
        sliders_col.addWidget(self.slider_curve_shadows)

        self.lbl_curve_midtones = QLabel("Средние: 128")
        sliders_col.addWidget(self.lbl_curve_midtones)
        self.slider_curve_midtones = QSlider(Qt.Horizontal)
        self.slider_curve_midtones.setMinimum(0)
        self.slider_curve_midtones.setMaximum(255)
        self.slider_curve_midtones.setValue(128)
        self.slider_curve_midtones.valueChanged.connect(self.on_curve_midtones_changed)
        sliders_col.addWidget(self.slider_curve_midtones)

        self.lbl_curve_highlights = QLabel("Света: 192")
        sliders_col.addWidget(self.lbl_curve_highlights)
        self.slider_curve_highlights = QSlider(Qt.Horizontal)
        self.slider_curve_highlights.setMinimum(0)
        self.slider_curve_highlights.setMaximum(255)
        self.slider_curve_highlights.setValue(192)
        self.slider_curve_highlights.valueChanged.connect(self.on_curve_highlights_changed)
        sliders_col.addWidget(self.slider_curve_highlights)

        curve_top.addLayout(sliders_col, 1)
        curve_pl.addLayout(curve_top)

        # Кнопка предпросмотра — иконка без текста, с подсказкой
        btn_preview = QPushButton()
        btn_preview.setToolTip("Предпросмотр выбранной карточки")
        btn_preview.setIcon(load_phosphor_icon("image", 18))
        btn_preview.setIconSize(QSize(18, 18))
        btn_preview.clicked.connect(self.on_preview_clicked)
        curve_pl.addWidget(btn_preview, alignment=Qt.AlignRight)
        right_layout.addWidget(curve_panel)

        right_layout.addStretch(1)

        self.right_scroll.setWidget(right_content)
        main_layout.addWidget(self.right_scroll, 2)

        self.list_widget.currentRowChanged.connect(self.on_current_item_changed)
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)

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

        help_menu = menu_bar.addMenu("Помощь")

        act_about = QAction("О программе", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

        act_history = QAction("История изменений", self)
        act_history.triggered.connect(self._show_history)
        help_menu.addAction(act_history)

        act_author = QAction("Автор", self)
        act_author.triggered.connect(self._show_author)
        help_menu.addAction(act_author)

        # Горячие клавиши (основные операции)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self.on_load_images_clicked)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self.on_export_selected_clicked)
        QShortcut(QKeySequence("Ctrl+Shift+E"), self, activated=self.on_export_clicked)
        QShortcut(QKeySequence("Space"), self, activated=self._toggle_preview_play_pause)
        QShortcut(QKeySequence("Delete"), self, activated=self.on_delete_selected_clicked)

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
        # При открытии подменю проигрываем собственный клик вместо системного звука
        SoundPlayer.play(SOUND_CLICK)
        text = (
            "WBO Animation — генератор видео-карточек.\n\n"
            "Основной сценарий работы:\n"
            "1. Слева загрузите изображения карточек (иконка папки).\n"
            "2. Выберите видео в блоке 'Список видео' справа.\n"
            "3. Настройте кривую (тени / средние / света).\n"
            "4. Для предпросмотра используйте большую область в центре — видео\n"
            "   накладывается в реальном времени в режиме 'Экран'.\n"
            "5. Экспортируйте карточки в MP4 кнопкой внизу справа.\n\n"
            "Горячие клавиши:\n"
            "  Ctrl+O        — загрузить изображения\n"
            "  Ctrl+E        — экспортировать только выбранные карточки\n"
            "  Ctrl+Shift+E  — экспортировать все карточки в MP4\n"
            "  Delete        — удалить выбранные карточки\n"
            "  Space         — пауза / пуск предпросмотра\n\n"
            "Поддерживаются форматы изображений: JPG, PNG, WEBP.\n"
            "Видео — MP4 (кодеки H.264, H.265, AV1, если установлены в системе)."
        )
        box = QMessageBox(self)
        box.setWindowTitle("О программе")
        box.setText(text)
        box.setIcon(QMessageBox.NoIcon)
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()

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
        box = QMessageBox(self)
        box.setWindowTitle("История изменений")
        box.setText(text)
        box.setIcon(QMessageBox.NoIcon)
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()

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
        dlg.setStyleSheet(
            "QDialog { background-color: #1f1f1f; }"
            "QLabel { color: #e8e8e8; font-size: 12px; }"
            "QLabel#nameLabel { font-size: 16px; font-weight: bold; margin-bottom: 4px; }"
            "QLabel#subtitleLabel { color: #9ca3af; font-size: 11px; margin-bottom: 8px; }"
        )
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Аудио-плеер с треком портфолио, останавливается при закрытии диалога
        if SOUND_PORTFOLIO.exists():
            try:
                player = QMediaPlayer(dlg)
                audio = QAudioOutput(dlg)
                player.setAudioOutput(audio)
                audio.setVolume(0.35)
                player.setSource(QUrl.fromLocalFile(str(SOUND_PORTFOLIO)))
                # В новых версиях Qt есть свойство loops, но на всякий случай
                # перезапускаем трек при завершении.
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

        # Аватар в круге, если файл существует
        avatar_path = BASE_DIR / "Assets" / "images" / "ivan.jpg"
        if avatar_path.exists():
            raw = QPixmap(str(avatar_path))
            if not raw.isNull():
                size = 96
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
                layout.addWidget(avatar_lbl)

        name_lbl = QLabel("Радыгин Иван Олегович")
        name_lbl.setObjectName("nameLabel")
        name_lbl.setAlignment(Qt.AlignHCenter)
        layout.addWidget(name_lbl)

        subtitle_lbl = QLabel("Нейросети, вайбкодинг и проекты, которые приносят пользу")
        subtitle_lbl.setObjectName("subtitleLabel")
        subtitle_lbl.setAlignment(Qt.AlignHCenter)
        subtitle_lbl.setWordWrap(True)
        layout.addWidget(subtitle_lbl)

        text_lbl = QLabel(full_text)
        text_lbl.setWordWrap(True)
        layout.addWidget(text_lbl)

        dlg.resize(520, 420)
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
            # Делаем иконку-превью для карточки
            pixmap = QPixmap(str(p.resolve()))
            if not pixmap.isNull():
                icon_pixmap = pixmap.scaled(
                    self.list_widget.iconSize(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                item.setIcon(icon_pixmap)

            self.list_widget.addItem(item)

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

        # Сначала загружаем превью с видео; если видео нет или не открылось — покажем исходное изображение
        video_started = self._load_preview_frames_for_current()
        if not video_started:
            self.update_image_preview(item.image_path)

    def on_selection_changed(self) -> None:
        """
        Обработка изменения выделения карточек.

        Здесь мы управляем видимостью кнопки удаления.
        """
        has_selection = bool(self.list_widget.selectedIndexes())
        self.btn_delete_selected.setVisible(has_selection)

    def on_refresh_videos_clicked(self) -> None:
        """Ручное обновление списка видео из папки Assets/video."""
        self.load_video_list()

    def on_cards_view_mode_changed(self, index: int) -> None:
        """
        Переключение вида карточек:
        - 0: сетка превью (иконки);
        - 1: список (строки с иконкой и именем).
        """
        if index == 0:
            # Сетка превью
            self.list_widget.setViewMode(QListWidget.IconMode)
            self.list_widget.setIconSize(QSize(96, 96))
        else:
            # Список
            self.list_widget.setViewMode(QListWidget.ListMode)
            self.list_widget.setIconSize(QSize(32, 32))

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
        w, h = 200, 200
        pixmap = QPixmap(w, h)
        pixmap.fill(QColor("#2a2a2a"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Сетка и оси: вход по X, выход по Y (0 внизу)
        margin = 20
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
            # x: 0..255 -> margin .. margin+graph_w; y: 0..255 -> margin+graph_h .. margin
            px = margin + (x_in / 255.0) * graph_w
            py = margin + graph_h - (y_out / 255.0) * graph_h
            pts.append((px, py))
        painter.setPen(QPen(QColor("#0cf"), 2))
        for i in range(len(pts) - 1):
            painter.drawLine(int(pts[i][0]), int(pts[i][1]), int(pts[i + 1][0]), int(pts[i + 1][1]))

        # Точки управления (кружки)
        for x_in, y_out in [(64, shadows), (128, midtones), (192, highlights)]:
            px = margin + (x_in / 255.0) * graph_w
            py = margin + graph_h - (y_out / 255.0) * graph_h
            painter.setPen(QPen(QColor("#fff"), 1))
            painter.setBrush(QColor("#0cf"))
            painter.drawEllipse(int(px - 4), int(py - 4), 8, 8)

        painter.end()
        self.lbl_curve_preview.setPixmap(pixmap)

    def _stop_preview_video(self) -> None:
        """Остановка таймера и освобождение видеопотока превью."""
        self._preview_timer.stop()
        if self.preview_cap is not None:
            self.preview_cap.release()
            self.preview_cap = None

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

        if self.preview_playing:
            self._preview_timer.start()
        # Без текста, только иконки: pause.svg и video-camera.svg
        self.btn_preview_play_pause.setIcon(
            load_phosphor_icon("pause" if self.preview_playing else "video-camera", 18)
        )
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

    def _toggle_preview_play_pause(self) -> None:
        """Переключение пауза/пуск зацикленного превью видео."""
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
            render_card_video(
                image_path=item.image_path,
                video_path=video_path,
                curve_shadows=item.curve_shadows,
                curve_midtones=item.curve_midtones,
                curve_highlights=item.curve_highlights,
                output_path=str(preview_path),
                max_duration=3.0,
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

    def on_export_selected_clicked(self) -> None:
        """Явный экспорт только выбранных карточек."""
        if not self.list_widget.selectedIndexes():
            QMessageBox.information(
                self,
                "Нет выбранных карточек",
                "Сначала выделите одну или несколько карточек слева.",
            )
            return
        # Просто переиспользуем общий обработчик экспорта,
        # который уже учитывает текущее выделение.
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

        self.config["last_export_path"] = export_dir
        save_config(self.config)

        # Реальная обработка видео с наложением «Экран»
        # Комментарий: здесь выполняем рендер для каждой выбранной карточки по очереди
        # и показываем прогресс в отдельном окне, похожем на Adobe Media Encoder
        errors: list[str] = []
        success_count = 0

        # Окно прогресса экспорта
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Экспорт видео-карточек")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setStyleSheet(
            "QDialog { background-color: #1f1f1f; }"
            "QLabel { color: #e8e8e8; font-size: 12px; }"
            "QProgressBar { background-color: #252525; border: 1px solid #3d3d3d; "
            "border-radius: 4px; text-align: center; color: #e8e8e8; }"
            "QProgressBar::chunk { background-color: #0d7377; border-radius: 4px; }"
            "QPushButton { background-color: #404040; color: #e8e8e8; border: 1px solid #505050; "
            "border-radius: 4px; padding: 6px 10px; }"
            "QPushButton:hover { background-color: #4a4a4a; border-color: #606060; }"
        )

        vbox = QVBoxLayout(progress_dialog)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(8)

        lbl_current = QLabel("Подготовка экспорта...")
        vbox.addWidget(lbl_current)

        row_overall = QHBoxLayout()
        lbl_overall = QLabel("Общий прогресс:")
        row_overall.addWidget(lbl_overall)
        bar_overall = QProgressBar()
        bar_overall.setRange(0, 100)
        bar_overall.setTextVisible(True)
        row_overall.addWidget(bar_overall)
        vbox.addLayout(row_overall)

        row_item = QHBoxLayout()
        lbl_item = QLabel("Текущая карточка:")
        row_item.addWidget(lbl_item)
        bar_item = QProgressBar()
        bar_item.setRange(0, 100)
        bar_item.setTextVisible(True)
        row_item.addWidget(bar_item)
        vbox.addLayout(row_item)

        lbl_time = QLabel("Прошло: 00:00    Осталось ~--:--")
        vbox.addWidget(lbl_time)

        btn_cancel = QPushButton("Отмена после текущей карточки")
        vbox.addWidget(btn_cancel)

        cancel_requested = False

        def on_cancel_clicked() -> None:
            nonlocal cancel_requested
            cancel_requested = True

        btn_cancel.clicked.connect(on_cancel_clicked)

        progress_dialog.resize(420, 200)
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

                render_card_video(
                    image_path=item.image_path,
                    video_path=video_path,
                    curve_shadows=item.curve_shadows,
                    curve_midtones=item.curve_midtones,
                    curve_highlights=item.curve_highlights,
                    output_path=out_path,
                    progress_callback=progress_callback,
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

        # Показываем итог
        if errors:
            # Если были ошибки — показываем их отдельно (без системного звука Windows)
            msg = f"Успешно экспортировано карточек: {success_count}.\n"
            msg += "Часть карточек не удалось обработать:\n\n"
            msg += "\n".join(errors)
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.NoIcon)
            msg_box.setWindowTitle("Экспорт завершён с ошибками")
            msg_box.setText(msg)
            msg_box.addButton("ОК", QMessageBox.AcceptRole)
            msg_box.exec()
        else:
            # При успешном экспорте даём выбор: просто закрыть окно или открыть папку
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.NoIcon)
            msg_box.setWindowTitle("Экспорт завершён")
            msg_box.setText(f"Успешно экспортировано карточек: {success_count}.")
            btn_ok = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            btn_open = msg_box.addButton("Открыть папку", QMessageBox.ActionRole)
            msg_box.setDefaultButton(btn_open)
            msg_box.exec()

            if msg_box.clickedButton() == btn_open:
                try:
                    os.startfile(export_dir)
                except Exception:
                    # Если не удалось открыть проводник — просто игнорируем
                    pass


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


def render_card_video(
    image_path: str,
    video_path: str,
    curve_shadows: int,
    curve_midtones: int,
    curve_highlights: int,
    output_path: str,
    max_duration: float = 8.0,
    progress_callback=None,
) -> None:
    """
    Рендер одной видео-карточки на базе OpenCV:
    - ограничиваем видео максимум 8 секундами;
    - приводим размер к 900x1200 px;
    - накладываем видео на картинку в режиме «Экран»;
    - применяем кривую по трём точкам (тени/средние/света);
    - сохраняем результат в .mp4.
    """
    # Размер итогового кадра согласно ТЗ (OpenCV использует (ширина, высота))
    target_w, target_h = 900, 1200

    # Загружаем фон-картинку через Pillow, чтобы уверенно поддерживать WEBP и другие форматы
    try:
        with Image.open(image_path) as img:
            # Приводим к RGB и нужному размеру
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

    # Получаем FPS исходного видео, по умолчанию 25
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 25.0

    # Считаем максимальное число кадров (не более 8 секунд и не более max_duration)
    effective_duration = min(8.0, max_duration)
    max_frames = int(fps * effective_duration)

    # Настраиваем видеозапись в MP4
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (target_w, target_h))
    if not out.isOpened():
        cap.release()
        raise RuntimeError(f"Не удалось открыть файл для записи: {output_path}")

    # Строим LUT кривой один раз для всего ролика
    curve_lut = build_curve_lut(curve_shadows, curve_midtones, curve_highlights)

    frames_written = 0

    while frames_written < max_frames:
        ret, frame_bgr = cap.read()
        if not ret:
            # Дошли до конца видео
            break

        # Приводим кадр к нужному размеру
        frame_bgr = cv2.resize(frame_bgr, (target_w, target_h), interpolation=cv2.INTER_AREA)
        # Переводим в RGB для обработки
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # Применяем кривую (LUT) и наложение «Экран»
        curved = apply_curve_lut(frame_rgb, curve_lut)
        blended_rgb = screen_blend(base_frame, curved)

        # Возвращаемся в BGR для записи через OpenCV
        blended_bgr = cv2.cvtColor(blended_rgb, cv2.COLOR_RGB2BGR)
        out.write(blended_bgr)
        frames_written += 1
        # Сообщаем о прогрессе рендера текущего ролика
        if progress_callback is not None:
            try:
                progress_callback(frames_written, max_frames)
            except Exception:
                # Комментарий: ошибки колбэка не должны ломать рендер
                pass

    cap.release()
    out.release()

    if frames_written == 0:
        # Если не было записано ни одного кадра — считаем это ошибкой
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
    app.setStyleSheet(APP_STYLESHEET)

    # Прелоад-окно (splash): фон из Assets/images/bg.webp, поверх — логотип и логи.
    splash_w, splash_h = 520, 300
    splash_pix = QPixmap(splash_w, splash_h)
    splash_pix.fill(QColor("#111111"))
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
    try:
        painter = QPainter(splash_pix)
        painter.setRenderHint(QPainter.Antialiasing)

        # Логотип: берём ivan.jpg, если есть; размещаем слева
        avatar_path = BASE_DIR / "Assets" / "images" / "ivan.jpg"
        if avatar_path.exists():
            raw = QPixmap(str(avatar_path))
            if not raw.isNull():
                raw = raw.scaled(120, 120, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                circle = QPixmap(120, 120)
                circle.fill(Qt.transparent)
                p2 = QPainter(circle)
                p2.setRenderHint(QPainter.Antialiasing)
                p2.setRenderHint(QPainter.SmoothPixmapTransform)
                p2.setBrush(Qt.white)
                p2.setPen(Qt.NoPen)
                p2.drawEllipse(0, 0, 120, 120)
                p2.setCompositionMode(QPainter.CompositionMode_SourceIn)
                p2.drawPixmap(0, 0, raw)
                p2.end()
                painter.drawPixmap(40, 90, circle)

        # Текст справа от логотипа
        painter.setPen(QColor("#e5e7eb"))
        painter.drawText(190, 130, "WBO Animation")
        painter.setPen(QColor("#9ca3af"))
        painter.drawText(190, 155, "Генератор видео-карточек")
        painter.setPen(QColor("#4b5563"))
        painter.drawText(40, 230, "Initializing UI…")
        painter.drawText(40, 250, "Loading assets…")
        painter.drawText(40, 270, "Preparing preview engine…")
        painter.setPen(QColor("#0ea5e9"))
        painter.drawText(
            splash_pix.rect().adjusted(0, 0, -40, -20),
            Qt.AlignBottom | Qt.AlignRight,
            "Loading  //  please wait"
        )
        painter.end()
    except Exception:
        pass

    splash = QSplashScreen(splash_pix)
    splash.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    splash.show()
    app.processEvents()

    # Кастомный прелоад на 6 секунд:
    # просто держим сплэш, пока основное окно «греется».
    start_ts = time.monotonic()
    while time.monotonic() - start_ts < 6.0:
        app.processEvents()
        time.sleep(0.01)

    window = MainWindow()
    # При запуске показываем обычное окно (не full-screen),
    # пользователь сам решает, разворачивать ли приложение.
    window.show()
    splash.finish(window)
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
            QMessageBox.critical(None, "WBO Animation — ошибка запуска", str(e) + "\n\n" + err)
        except Exception:
            print(err)
            input("Press Enter to close...")
        raise

