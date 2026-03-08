"""
ui/main_window.py
=================
ReVoice GUI の表示スケルトン実装。
実際の処理ロジック接続は行わず、固定 UI のみ提供する。
"""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class ReVoiceMainWindow(QMainWindow):
    def __init__(self, resolve: Any, settings: dict[str, Any]) -> None:
        super().__init__()
        self.resolve = resolve
        self.settings = settings
        self.current_step = 0
        self.step_buttons: list[QPushButton] = []

        self.setWindowTitle("ReVoice v3.0")
        self.resize(1600, 900)
        self._apply_style()
        self._build_ui()
        self._refresh_step_ui()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #0b0f1d;
                color: #dce4ff;
                font-family: 'Segoe UI', 'Noto Sans JP', sans-serif;
            }
            QLabel#titleMain { font-size: 24px; font-weight: 700; color: #64a3ff; }
            QLabel#titleSub { font-size: 14px; color: #7b8bb5; }
            QFrame#panel { background-color: #131a2e; border: 1px solid #212a45; border-radius: 14px; }
            QPushButton#stepBtn {
                text-align: left; padding: 14px; border: 1px solid #273154; border-radius: 12px;
                background-color: #151d33; color: #9fb2e3;
            }
            QPushButton#stepBtn[active="true"] {
                border: 1px solid #4f93ff; background-color: #1b2a4b; color: #dce4ff; font-weight: 700;
            }
            QPushButton#action {
                background-color: #4f93ff; border-radius: 12px; padding: 10px 22px; color: white; font-weight: 700;
            }
            QPushButton#actionSecondary {
                background-color: #232c43; border: 1px solid #3a486f; border-radius: 12px; padding: 10px 22px;
            }
            QFrame#settingsDrawer {
                background-color: rgba(20, 24, 38, 0.98);
                border-left: 1px solid #2b3555;
            }
            """
        )

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        main = QVBoxLayout(root)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(12)

        # Top bar
        top = QFrame()
        top.setObjectName("panel")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(20, 14, 20, 14)
        left = QVBoxLayout()
        title = QLabel("ReVoice")
        title.setObjectName("titleMain")
        subtitle = QLabel("v3.0 | DaVinci Resolve 字幕自動生成")
        subtitle.setObjectName("titleSub")
        left.addWidget(title)
        left.addWidget(subtitle)
        top_layout.addLayout(left)
        top_layout.addStretch()
        self.resolve_badge = QLabel("● Resolve 接続済み" if self.resolve else "● Resolve 未接続")
        self.resolve_badge.setStyleSheet(
            f"color: {'#59d8a1' if self.resolve else '#ff8a8a'}; background:#10252a; border:1px solid #224e53; border-radius:10px; padding:6px 12px;"
        )
        top_layout.addWidget(self.resolve_badge)
        main.addWidget(top)

        # center area
        center = QHBoxLayout()
        center.setSpacing(12)

        sidebar = self._build_sidebar()
        center.addWidget(sidebar, 1)

        content = self._build_content()
        center.addWidget(content, 8)

        main.addLayout(center)
        main.addWidget(self._build_footer())

        # settings drawer (hidden by default)
        self.settings_drawer = self._build_settings_drawer()
        self.settings_drawer.setParent(root)
        self.settings_drawer.hide()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if hasattr(self, "settings_drawer"):
            w = 320
            self.settings_drawer.setGeometry(self.width() - w - 12, 12, w, self.height() - 24)

    def _build_sidebar(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 12, 10, 12)

        steps = [
            ("01", "解析範囲", "範囲・ヒント設定"),
            ("02", "セグメント確認", "テキスト編集"),
            ("03", "配置確認", "内容確認・実行"),
        ]

        for i, (idx, title, desc) in enumerate(steps):
            btn = QPushButton(f"{idx}  {title}\n{desc}")
            btn.setObjectName("stepBtn")
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda _=False, x=i: self._set_step(x))
            self.step_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()
        setting_btn = QPushButton("⚙ 設定")
        setting_btn.setObjectName("actionSecondary")
        setting_btn.clicked.connect(self._toggle_settings)
        layout.addWidget(setting_btn)
        return panel

    def _build_content(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.step_header = QLabel("STEP 01 / 03")
        self.step_header.setStyleSheet("color:#7fa9ff; font-size: 13px; letter-spacing: 1px;")
        layout.addWidget(self.step_header)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._step1_widget())
        self.stack.addWidget(self._step2_widget())
        self.stack.addWidget(self._step3_widget())
        layout.addWidget(self.stack)

        return panel

    def _step1_widget(self) -> QWidget:
        w = QWidget()
        g = QVBoxLayout(w)
        g.addWidget(QLabel("解析範囲と入力設定"))
        g.addWidget(QLabel("タイムラインの解析対象と AI へのヒントを設定します"))
        g.addWidget(self._card("Mark In / Out", "IN 00:00:12;08 / OUT 00:01:44;22"))
        g.addWidget(self._card("PROMPT (任意)", "例: 専門用語を含む技術的な内容..."))
        g.addStretch()
        return w

    def _step2_widget(self) -> QWidget:
        w = QWidget()
        g = QVBoxLayout(w)
        g.addWidget(QLabel("セグメント確認・編集"))
        g.addWidget(QLabel("クリックで直接編集。ダブルクリックで AI インライン編集"))
        for line in [
            "01  00:00:03;12   本日はお越しいただき、ありがとうございます。",
            "02  00:00:07;04   こちらこそ、よろしくお願いします。",
            "03  00:00:12;18   まず最初に、プロジェクトの概要をご説明します。",
        ]:
            g.addWidget(self._line_row(line))
        g.addWidget(self._card("AI CHAT", "全体への指示はここで入力"))
        g.addStretch()
        return w

    def _step3_widget(self) -> QWidget:
        w = QWidget()
        g = QVBoxLayout(w)
        g.addWidget(QLabel("配置の確認"))
        g.addWidget(QLabel("内容を確認して『配置を実行』を押してください"))
        g.addWidget(self._card("方式", "Text+（8 segs ≤ 100）"))
        g.addWidget(self._card("トラック", "ReVoice_Sub"))
        g.addWidget(self._card("SRT ファイル", "/tmp/revoice_out.srt"))
        g.addStretch()
        return w

    def _build_footer(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        h = QHBoxLayout(panel)
        h.setContentsMargins(20, 12, 20, 12)
        self.footer_label = QLabel("Step 1 / 3 - 解析範囲を選択してください")
        self.footer_label.setStyleSheet("color:#8fa0cc;")
        h.addWidget(self.footer_label)
        h.addStretch()
        self.back_btn = QPushButton("‹ 戻る")
        self.back_btn.setObjectName("actionSecondary")
        self.back_btn.clicked.connect(self._prev_step)
        self.next_btn = QPushButton("次へ ›")
        self.next_btn.setObjectName("action")
        self.next_btn.clicked.connect(self._next_step)
        h.addWidget(self.back_btn)
        h.addWidget(self.next_btn)
        return panel

    def _build_settings_drawer(self) -> QWidget:
        drawer = QFrame()
        drawer.setObjectName("settingsDrawer")
        layout = QVBoxLayout(drawer)
        layout.setContentsMargins(20, 20, 20, 20)
        title = QLabel("設定")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)
        for key, value in [
            ("Whisper モデル", self.settings.get("whisper", {}).get("model", "base")),
            ("言語", self.settings.get("whisper", {}).get("language", "自動検出")),
            ("トラック名", self.settings.get("subtitle", {}).get("track_name", "ReVoice_Sub")),
            ("フレームレート", "29.97 DF"),
        ]:
            row = QLabel(f"{key}:  {value}")
            row.setStyleSheet("padding: 8px 0; color:#b8c7f0;")
            layout.addWidget(row)
        layout.addStretch()
        close_btn = QPushButton("閉じる")
        close_btn.setObjectName("actionSecondary")
        close_btn.clicked.connect(self._toggle_settings)
        layout.addWidget(close_btn)
        return drawer

    def _card(self, title: str, value: str) -> QWidget:
        card = QFrame()
        card.setObjectName("panel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        t = QLabel(title)
        t.setStyleSheet("color:#82a2f0;")
        v = QLabel(value)
        v.setStyleSheet("color:#dce4ff;")
        layout.addWidget(t)
        layout.addWidget(v)
        return card

    def _line_row(self, text: str) -> QWidget:
        row = QFrame()
        row.setStyleSheet("background:#141c31; border-radius:8px;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.addWidget(QLabel(text))
        return row

    def _set_step(self, idx: int) -> None:
        self.current_step = idx
        self._refresh_step_ui()

    def _next_step(self) -> None:
        if self.current_step < 2:
            self.current_step += 1
            self._refresh_step_ui()

    def _prev_step(self) -> None:
        if self.current_step > 0:
            self.current_step -= 1
            self._refresh_step_ui()

    def _refresh_step_ui(self) -> None:
        self.stack.setCurrentIndex(self.current_step)
        self.step_header.setText(f"STEP {self.current_step + 1:02d} / 03")
        for i, btn in enumerate(self.step_buttons):
            btn.setProperty("active", "true" if i == self.current_step else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
        messages = [
            "Step 1 / 3 - 解析範囲を選択してください",
            "Step 2 / 3 - セグメントを確認・編集してください",
            "Step 3 / 3 - 配置内容を確認してください",
        ]
        self.footer_label.setText(messages[self.current_step])
        self.back_btn.setEnabled(self.current_step > 0)
        self.next_btn.setText("配置を実行(E) ›" if self.current_step == 2 else "次へ ›")

    def _toggle_settings(self) -> None:
        self.settings_drawer.setVisible(not self.settings_drawer.isVisible())
