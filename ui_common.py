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

        btn_close = QPushButton("×")
        btn_close.setObjectName("dialogTitleClose")
        btn_close.setToolTip("Закрыть")
        btn_close.setFixedSize(28, 24)
        btn_close.clicked.connect(self._on_close)
        layout.addWidget(btn_close)

        self.setStyleSheet("""
            #dialogTitleBar {
                background: rgba(30, 35, 41, 0.92);
                border-bottom: 1px solid #2a3038;
                border-radius: 8px 8px 0 0;
            }
            #dialogTitleLabel {
                color: #e6edf3;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }
            #dialogTitleClose {
                background: rgba(71, 85, 105, 0.35);
                border: 1px solid #475569;
                color: #e2e8f0;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 700;
                padding-bottom: 1px;
            }
            #dialogTitleClose:hover {
                background: rgba(185, 28, 28, 0.4);
                border-color: #ef4444;
                color: #ffffff;
            }
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
