from __future__ import annotations

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QFrame, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence

from ui_common import DialogTitleBar


class ExportSettingsDialog(QDialog):
    """Диалог настроек экспорта (кодек, качество, размер, FPS)."""

    def __init__(
        self,
        parent,
        codec: str,
        size_str: str,
        fps: int,
        render_preset: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки экспорта видео")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)

        self._codec = (codec or "h264").lower()
        self._size_str = size_str or "900x1200"
        self._fps = int(fps or 60)
        self._render_preset = render_preset or "balanced"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(DialogTitleBar(self, "Настройки экспорта видео"))

        content = QFrame()
        content.setObjectName("dialogContent")
        content.setStyleSheet("#dialogContent { background: transparent; border-radius: 0 0 6px 6px; padding: 12px; }")
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)

        # Кодек
        row_codec = QHBoxLayout()
        row_codec.addWidget(QLabel("Кодек:"))
        self.combo_codec = QComboBox()
        self.combo_codec.addItem("H.264 (рекомендуется)", "h264")
        self.combo_codec.addItem("MPEG-4 (совместимость)", "mpeg4")
        row_codec.addWidget(self.combo_codec)
        content_layout.addLayout(row_codec)

        # Качество
        row_quality = QHBoxLayout()
        row_quality.addWidget(QLabel("Качество:"))
        self.combo_quality = QComboBox()
        self.combo_quality.addItem("Высокое (медленно)", "quality")
        self.combo_quality.addItem("Среднее (рекомендуется)", "balanced")
        self.combo_quality.addItem("Самое быстрое", "fast")
        row_quality.addWidget(self.combo_quality)
        content_layout.addLayout(row_quality)

        # Размер
        row_size = QHBoxLayout()
        row_size.addWidget(QLabel("Размер кадра:"))
        self.combo_size = QComboBox()
        self.combo_size.addItem("900×1200 (вертикальный стандарт)", "900x1200")
        self.combo_size.addItem("819×1080 (альтернативный)", "819x1080")
        row_size.addWidget(self.combo_size)
        content_layout.addLayout(row_size)

        # FPS
        row_fps = QHBoxLayout()
        row_fps.addWidget(QLabel("Частота кадров:"))
        self.combo_fps = QComboBox()
        self.combo_fps.addItem("24 fps (кино)", 24)
        self.combo_fps.addItem("30 fps", 30)
        self.combo_fps.addItem("60 fps (по умолчанию)", 60)
        row_fps.addWidget(self.combo_fps)
        content_layout.addLayout(row_fps)

        # Кнопки
        row_btns = QHBoxLayout()
        row_btns.addStretch(1)
        self.btn_reset = QPushButton("Сбросить")
        self.btn_ok = QPushButton("ОК")
        self.btn_cancel = QPushButton("Отмена")
        row_btns.addWidget(self.btn_reset)
        row_btns.addWidget(self.btn_ok)
        row_btns.addWidget(self.btn_cancel)
        content_layout.addLayout(row_btns)

        layout.addWidget(content)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_reset.clicked.connect(self._reset_defaults)
        QShortcut(QKeySequence("Escape"), self, self.reject)

        self._apply_initial_values()

    def _apply_initial_values(self) -> None:
        self._set_combo_by_data(self.combo_codec, self._codec, default="h264")
        self._set_combo_by_data(self.combo_quality, self._render_preset, default="balanced")
        self._set_combo_by_data(self.combo_size, self._size_str, default="900x1200")
        self._set_combo_by_data(self.combo_fps, self._fps, default=60)

    @staticmethod
    def _set_combo_by_data(combo: QComboBox, data, default) -> None:
        index = combo.findData(data)
        if index < 0:
            index = combo.findData(default)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _reset_defaults(self) -> None:
        """Сброс настроек к заводским значениям."""
        self._codec = "h264"
        self._render_preset = "balanced"
        self._size_str = "900x1200"
        self._fps = 60
        self._apply_initial_values()

    def get_values(self) -> tuple[str, str, int, str]:
        """Возвращает (codec, size_str, fps, render_preset)."""
        codec = self.combo_codec.currentData()
        size = self.combo_size.currentData()
        fps = int(self.combo_fps.currentData())
        quality = self.combo_quality.currentData()
        return str(codec), str(size), fps, str(quality)

