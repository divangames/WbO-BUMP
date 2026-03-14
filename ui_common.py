# Общие UI-компоненты: кастомная шапка для диалогов (перетаскивание, закрытие)

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class DialogTitleBar(QFrame):
    """Кастомная шапка диалога: заголовок и кнопка закрытия. Перетаскивание окна за шапку."""

    def __init__(self, parent: QFrame | None, title: str) -> None:
        super().__init__(parent)
        self.setObjectName("dialogTitleBar")
        self._dragging = False
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 6, 4)
        layout.setSpacing(6)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("dialogTitleLabel")
        layout.addWidget(self._title_label)
        layout.addStretch(1)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("dialogTitleClose")
        btn_close.setFixedSize(28, 22)
        btn_close.clicked.connect(self._on_close)
        layout.addWidget(btn_close)

        self.setStyleSheet("""
            #dialogTitleBar { background: transparent; border-radius: 6px 6px 0 0; }
            #dialogTitleLabel { color: #e2e8f0; font-size: 12px; font-weight: 600; background: transparent; }
            #dialogTitleClose {
                background: transparent; border: none; color: #94a3b8;
                font-size: 11px;
            }
            #dialogTitleClose:hover { background: rgba(51, 65, 85, 0.6); color: #f1f5f9; }
        """)

    def _on_close(self) -> None:
        w = self.window()
        if w and hasattr(w, "reject"):
            w.reject()
        else:
            w.close()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            w = self.window()
            if w:
                self._drag_pos = event.globalPosition().toPoint() - w.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging and self._drag_pos is not None:
            w = self.window()
            if w:
                w.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
        super().mouseReleaseEvent(event)
