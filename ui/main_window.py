"""
ui/main_window.py
=================
PySide6 GUI メインウィンドウ (revoice_v5.html のデザインベース)
"""

import os
import threading
from typing import Any, Dict, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QStackedWidget, QTextEdit,
    QRadioButton, QButtonGroup, QProgressBar, QScrollArea,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QPalette, QColor

from config.settings_manager import SettingsManager
from ui.worker import SubtitleWorker


class DarkPalette:
    """HTML mock の CSS 変数に対応する色定義"""
    BG = "#1a1a1f"
    SIDEBAR = "#14141a"
    PANEL = "#22222a"
    SURF = "#2a2a34"
    SURF2 = "#32323e"
    B1 = "#42424f"
    B2 = "#2e2e3a"
    ACCENT = "#5b9cf6"
    ACD = "#3a6fd4"
    GREEN = "#4ec9a8"
    YELLOW = "#e8d48b"
    ORANGE = "#e8a87c"
    PURPLE = "#c896d4"
    RED = "#f07070"
    DIM = "#8888a0"
    FAINT = "#44445a"
    TXT = "#dddde8"


class StepIndicator(QWidget):
    """サイドバーのステップインジケーター"""
    clicked = Signal()
    
    def __init__(self, number: int, label: str, desc: str, parent=None):
        super().__init__(parent)
        self.number = number
        self.active = False
        self.done = False
        self.clickable = False
        self.setup_ui(label, desc)
    
    def setup_ui(self, label: str, desc: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        
        # 番号表示
        self.num_label = QLabel(str(self.number))
        self.num_label.setFixedSize(22, 22)
        self.num_label.setAlignment(Qt.AlignCenter)
        self.num_label.setStyleSheet(f"""
            QLabel {{
                border: 1.5px solid {DarkPalette.FAINT};
                border-radius: 11px;
                color: {DarkPalette.FAINT};
                font-family: 'Monospace';
                font-size: 9px;
                font-weight: 600;
            }}
        """)
        layout.addWidget(self.num_label)
        
        # テキスト部分
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        self.label_text = QLabel(label)
        self.label_text.setStyleSheet(f"""
            QLabel {{
                color: {DarkPalette.FAINT};
                font-size: 11px;
                font-weight: 500;
            }}
        """)
        text_layout.addWidget(self.label_text)
        
        self.desc_text = QLabel(desc)
        self.desc_text.setStyleSheet(f"""
            QLabel {{
                color: #383848;
                font-size: 9px;
            }}
        """)
        text_layout.addWidget(self.desc_text)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        self.update_style()
    
    def set_active(self, active: bool):
        self.active = active
        self.update_style()
    
    def set_done(self, done: bool):
        self.done = done
        self.update_style()
    
    def set_clickable(self, clickable: bool):
        self.clickable = clickable
        self.setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)
        self.update_style()
    
    def update_style(self):
        bg_color = DarkPalette.SURF if self.active else "transparent"
        if self.active:
            bg_color = f"rgba(91, 156, 246, 0.08)"
            num_border = DarkPalette.ACCENT
            num_color = DarkPalette.ACCENT
            num_bg = "rgba(91, 156, 246, 0.12)"
            label_color = DarkPalette.TXT
            desc_color = DarkPalette.DIM
        elif self.done:
            num_border = DarkPalette.ACD
            num_color = DarkPalette.ACD
            num_bg = "rgba(58, 111, 212, 0.14)"
            label_color = DarkPalette.DIM
            desc_color = "#383848"
        else:
            num_border = DarkPalette.FAINT
            num_color = DarkPalette.FAINT
            num_bg = "transparent"
            label_color = DarkPalette.FAINT
            desc_color = "#383848"
        
        self.setStyleSheet(f"""
            QWidget {{
                background: {bg_color};
                border-radius: 12px;
            }}
            QWidget:hover {{
                background: rgba(255, 255, 255, 0.03);
            }}
        """)
        
        self.num_label.setStyleSheet(f"""
            QLabel {{
                border: 1.5px solid {num_border};
                border-radius: 11px;
                color: {num_color};
                background: {num_bg};
                font-family: 'Monospace';
                font-size: 9px;
                font-weight: 600;
            }}
        """)
        
        self.label_text.setStyleSheet(f"QLabel {{ color: {label_color}; font-size: 11px; font-weight: 500; }}")
        self.desc_text.setStyleSheet(f"QLabel {{ color: {desc_color}; font-size: 9px; }}")
    
    def mousePressEvent(self, event):
        if self.clickable:
            self.clicked.emit()
        super().mousePressEvent(event)


class LoadingOverlay(QWidget):
    """Loading overlay with phase-based progress (Step 2)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QWidget {{
                background: {DarkPalette.BG};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        # タイトル
        title = QLabel("ReVoice <span style='color: #44445a; font-weight: 300'>AI</span>")
        title.setTextFormat(Qt.RichText)
        title.setStyleSheet(f"""
            QLabel {{
                font-family: 'Monospace';
                font-size: 13px;
                font-weight: 600;
                color: {DarkPalette.ACCENT};
                letter-spacing: 2px;
            }}
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("解析が完了するまでお待ちください")
        subtitle.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                color: {DarkPalette.DIM};
                font-weight: 300;
            }}
        """)
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        # フェーズ進捗 (3つ)
        phases_widget = QWidget()
        phases_widget.setFixedWidth(420)
        phases_layout = QVBoxLayout(phases_widget)
        phases_layout.setSpacing(12)
        phases_layout.setContentsMargins(0, 0, 0, 0)
        
        self.phase_widgets = []
        phase_info = [
            ("FFmpeg", "音声抽出・正規化"),
            ("Whisper", "音声転写"),
            ("Gemini", "AI リファイン")
        ]
        
        for name, tag in phase_info:
            phase = self.create_phase_widget(name, tag)
            phases_layout.addWidget(phase)
            self.phase_widgets.append(phase)
        
        layout.addWidget(phases_widget)
        
        # 中止ボタン
        self.cancel_button = QPushButton("✕  解析を中止する")
        self.cancel_button.setStyleSheet(f"""
            QPushButton {{
                padding: 10px 22px;
                border-radius: 12px;
                background: rgba(240, 112, 112, 0.08);
                border: 1.5px solid rgba(240, 112, 112, 0.22);
                color: {DarkPalette.RED};
                font-family: 'Monospace';
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: rgba(240, 112, 112, 0.16);
                border-color: rgba(240, 112, 112, 0.4);
            }}
            QPushButton:disabled {{
                opacity: 0.4;
            }}
        """)
        layout.addWidget(self.cancel_button, alignment=Qt.AlignCenter)
        
        layout.addStretch()
        self.hide()
    
    def create_phase_widget(self, name: str, tag: str):
        """個別のフェーズウィジェット作成"""
        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background: {DarkPalette.SURF};
                border: 1.5px solid {DarkPalette.B2};
                border-radius: 12px;
                padding: 14px 16px;
            }}
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        
        # ヘッダー行
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # ドット
        dot = QLabel("●")
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"""
            QLabel {{
                color: {DarkPalette.FAINT};
                font-size: 10px;
            }}
        """)
        header_layout.addWidget(dot)
        widget.dot = dot
        
        # 名前
        name_label = QLabel(f"{name} <span style='font-weight: 300; font-size: 10px; color: {DarkPalette.FAINT}'>{tag}</span>")
        name_label.setTextFormat(Qt.RichText)
        name_label.setStyleSheet(f"""
            QLabel {{
                font-family: 'Monospace';
                font-size: 11px;
                font-weight: 600;
                color: {DarkPalette.DIM};
            }}
        """)
        header_layout.addWidget(name_label, 1)
        widget.name_label = name_label
        
        # パーセント
        pct_label = QLabel("待機中")
        pct_label.setStyleSheet(f"""
            QLabel {{
                font-family: 'Monospace';
                font-size: 11px;
                color: {DarkPalette.FAINT};
            }}
        """)
        header_layout.addWidget(pct_label)
        widget.pct_label = pct_label
        
        layout.addLayout(header_layout)
        
        # プログレスバー
        progress = QProgressBar()
        progress.setFixedHeight(4)
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setTextVisible(False)
        progress.setStyleSheet(f"""
            QProgressBar {{
                background: {DarkPalette.B2};
                border-radius: 2px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {DarkPalette.ACD}, stop:1 {DarkPalette.ACCENT});
                border-radius: 2px;
            }}
        """)
        layout.addWidget(progress)
        widget.progress = progress
        
        # ログメッセージ
        log_label = QLabel("")
        log_label.setStyleSheet(f"""
            QLabel {{
                font-family: 'Monospace';
                font-size: 10px;
                color: {DarkPalette.FAINT};
                min-height: 14px;
            }}
        """)
        layout.addWidget(log_label)
        widget.log_label = log_label
        
        widget.state = "idle"
        return widget
    
    def set_phase(self, phase_idx: int, state: str, progress: int, message: str = ""):
        """フェーズの状態を更新"""
        if phase_idx < 0 or phase_idx >= len(self.phase_widgets):
            return
        
        widget = self.phase_widgets[phase_idx]
        widget.state = state
        
        # スタイル更新
        if state == "active":
            border_color = DarkPalette.ACCENT
            bg_color = "rgba(91, 156, 246, 0.04)"
            dot_color = DarkPalette.ACCENT
            name_color = DarkPalette.TXT
            pct_color = DarkPalette.ACCENT
            widget.pct_label.setText(f"{progress}%")
        elif state == "done":
            border_color = "rgba(78, 201, 168, 0.3)"
            bg_color = "rgba(78, 201, 168, 0.03)"
            dot_color = DarkPalette.GREEN
            name_color = DarkPalette.DIM
            pct_color = DarkPalette.GREEN
            widget.pct_label.setText("完了")
        elif state == "error":
            border_color = "rgba(240, 112, 112, 0.3)"
            bg_color = "rgba(240, 112, 112, 0.04)"
            dot_color = DarkPalette.RED
            name_color = DarkPalette.DIM
            pct_color = DarkPalette.RED
            widget.pct_label.setText("エラー")
        else:  # idle
            border_color = DarkPalette.B2
            bg_color = DarkPalette.SURF
            dot_color = DarkPalette.FAINT
            name_color = DarkPalette.DIM
            pct_color = DarkPalette.FAINT
            widget.pct_label.setText("待機中")
        
        widget.setStyleSheet(f"""
            QFrame {{
                background: {bg_color};
                border: 1.5px solid {border_color};
                border-radius: 12px;
            }}
        """)
        
        widget.dot.setStyleSheet(f"QLabel {{ color: {dot_color}; font-size: 10px; }}")
        widget.pct_label.setStyleSheet(f"QLabel {{ font-family: 'Monospace'; font-size: 11px; color: {pct_color}; }}")
        
        widget.progress.setValue(progress)
        widget.log_label.setText(message)


class MainWindow(QMainWindow):
    """ReVoice Pro メインウィンドウ"""
    
    def __init__(self, video_path: Optional[str] = None, fps: float = 29.97, 
                 resolve_obj: Optional[Any] = None):
        super().__init__()
        self.video_path = video_path
        self.fps = fps
        self.resolve = resolve_obj
        self.settings_mgr = SettingsManager()
        self.worker: Optional[SubtitleWorker] = None
        self.stop_event = threading.Event()
        self.current_step = 0
        self.analyzed = False
        
        self.setup_window()
        self.setup_ui()
        self.apply_dark_theme()
    
    def setup_window(self):
        """ウィンドウの基本設定"""
        self.setWindowTitle("ReVoice Pro v2.11")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
    
    def setup_ui(self):
        """UI コンポーネントの構築"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # タイトルバー
        titlebar = self.create_titlebar()
        main_layout.addWidget(titlebar)
        
        # メインコンテンツエリア
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(14, 14, 14, 14)
        content_layout.setSpacing(12)
        
        # サイドバー
        sidebar = self.create_sidebar()
        content_layout.addWidget(sidebar)
        
        # コンテンツエリア (ページスタック)
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet(f"""
            QStackedWidget {{
                background: {DarkPalette.PANEL};
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        
        # Step 1: セットアップ
        self.page_setup = self.create_setup_page()
        self.content_stack.addWidget(self.page_setup)
        
        # Step 2: Loading (overlay として別管理)
        
        # Step 3: 完了確認
        self.page_confirm = self.create_confirm_page()
        self.content_stack.addWidget(self.page_confirm)
        
        content_layout.addWidget(self.content_stack, 1)
        
        main_layout.addLayout(content_layout, 1)
        
        # フッター
        footer = self.create_footer()
        main_layout.addWidget(footer)
        
        # Loading overlay (最前面)
        self.loading_overlay = LoadingOverlay(central)
        self.loading_overlay.setGeometry(0, 0, self.width(), self.height())
        self.loading_overlay.cancel_button.clicked.connect(self.cancel_workflow)
    
    def create_titlebar(self) -> QWidget:
        """タイトルバー作成"""
        titlebar = QFrame()
        titlebar.setFixedHeight(46)
        titlebar.setStyleSheet(f"""
            QFrame {{
                background: {DarkPalette.SIDEBAR};
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            }}
        """)
        
        layout = QHBoxLayout(titlebar)
        layout.setContentsMargins(20, 0, 20, 0)
        
        # 左側: ロゴ + プロダクト名
        logo = QLabel("ReVoice <em style='color: #44445a; font-weight: 300'>v2.11</em>")
        logo.setTextFormat(Qt.RichText)
        logo.setStyleSheet(f"""
            QLabel {{
                font-family: 'Monospace';
                font-size: 13px;
                font-weight: 600;
                color: {DarkPalette.ACCENT};
                letter-spacing: 2px;
            }}
        """)
        layout.addWidget(logo)
        
        divider = QFrame()
        divider.setFixedSize(1, 16)
        divider.setStyleSheet(f"background: {DarkPalette.FAINT}; opacity: 0.4;")
        layout.addWidget(divider)
        
        product = QLabel("DaVinci Resolve 字幕自動生成")
        product.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                color: {DarkPalette.DIM};
                font-weight: 300;
            }}
        """)
        layout.addWidget(product)
        
        layout.addStretch()
        
        # 右側: Resolve 接続ステータス
        self.status_pill = QLabel("● Resolve 接続済み")
        self.status_pill.setStyleSheet(f"""
            QLabel {{
                background: rgba(78, 201, 168, 0.08);
                border: 1px solid rgba(78, 201, 168, 0.18);
                border-radius: 10px;
                padding: 5px 12px;
                font-family: 'Monospace';
                font-size: 10px;
                color: {DarkPalette.GREEN};
            }}
        """)
        layout.addWidget(self.status_pill)
        
        return titlebar
    
    def create_sidebar(self) -> QWidget:
        """サイドバー作成"""
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background: {DarkPalette.PANEL};
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 18, 10, 12)
        layout.setSpacing(0)
        
        # ステップインジケーター
        self.step_indicators = []
        steps_info = [
            (1, "解析範囲", "範囲・ヒント設定"),
            (2, "セグメント確認", "テキスト編集"),
            (3, "配置確認", "内容確認・実行")
        ]
        
        for num, label, desc in steps_info:
            indicator = StepIndicator(num, label, desc)
            indicator.clicked.connect(lambda idx=num-1: self.jump_to_step(idx))
            layout.addWidget(indicator)
            self.step_indicators.append(indicator)
        
        layout.addStretch()
        
        # フッター
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(16, 12, 16, 12)
        
        ver_tag = QLabel("FREE · 2026.03")
        ver_tag.setStyleSheet(f"""
            QLabel {{
                font-family: 'Monospace';
                font-size: 8px;
                color: #303040;
                letter-spacing: 1px;
            }}
        """)
        footer_layout.addWidget(ver_tag)
        footer_layout.addStretch()
        
        layout.addLayout(footer_layout)
        
        # 初期状態: Step 1 が active
        self.step_indicators[0].set_active(True)
        
        return sidebar
    
    def create_setup_page(self) -> QWidget:
        """Step 1: セットアップページ"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ヘッダー
        header = QFrame()
        header.setStyleSheet(f"background: transparent; border-bottom: 1px solid rgba(255, 255, 255, 0.05);")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 20, 24, 16)
        header_layout.setSpacing(5)
        
        step_ind = QLabel("STEP 01 / 03")
        step_ind.setStyleSheet(f"""
            QLabel {{
                font-family: 'Monospace';
                font-size: 9px;
                color: {DarkPalette.ACCENT};
                letter-spacing: 2px;
            }}
        """)
        header_layout.addWidget(step_ind)
        
        title = QLabel("解析範囲と入力設定")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: 18px;
                font-weight: 500;
                color: {DarkPalette.TXT};
            }}
        """)
        header_layout.addWidget(title)
        
        subtitle = QLabel("タイムラインの解析対象と AI へのヒントを設定します")
        subtitle.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                color: {DarkPalette.DIM};
                font-weight: 300;
            }}
        """)
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header)
        
        # ボディ (スクロール可能)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 20, 24, 20)
        body_layout.setSpacing(16)
        
        # 解析範囲選択
        range_label = QLabel("解析範囲")
        range_label.setStyleSheet(f"""
            QLabel {{
                font-family: 'Monospace';
                font-size: 9px;
                letter-spacing: 1px;
                color: {DarkPalette.DIM};
                text-transform: uppercase;
            }}
        """)
        body_layout.addWidget(range_label)
        
        range_group = QButtonGroup(body)
        range_layout = QHBoxLayout()
        range_layout.setSpacing(10)
        
        self.radio_inout = QRadioButton("Mark In / Out")
        self.radio_inout.setChecked(True)
        self.radio_inout.setStyleSheet(self.get_radio_style())
        range_layout.addWidget(self.radio_inout, 1)
        range_group.addButton(self.radio_inout)
        
        self.radio_full = QRadioButton("Full Timeline")
        self.radio_full.setStyleSheet(self.get_radio_style())
        range_layout.addWidget(self.radio_full, 1)
        range_group.addButton(self.radio_full)
        
        body_layout.addLayout(range_layout)
        
        # 動画情報表示
        info_label = QLabel(f"動画: {os.path.basename(self.video_path) if self.video_path else '(未選択)'}")
        info_label.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                color: {DarkPalette.DIM};
                padding: 10px;
                background: {DarkPalette.SURF};
                border: 1.5px solid {DarkPalette.B2};
                border-radius: 8px;
            }}
        """)
        body_layout.addWidget(info_label)
        
        fps_label = QLabel(f"FPS: {self.fps:.2f}")
        fps_label.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                color: {DarkPalette.DIM};
                padding: 10px;
                background: {DarkPalette.SURF};
                border: 1.5px solid {DarkPalette.B2};
                border-radius: 8px;
            }}
        """)
        body_layout.addWidget(fps_label)
        
        # Prompt (任意)
        prompt_label = QLabel("Prompt（任意）")
        prompt_label.setStyleSheet(f"""
            QLabel {{
                font-family: 'Monospace';
                font-size: 9px;
                letter-spacing: 1px;
                color: {DarkPalette.DIM};
            }}
        """)
        body_layout.addWidget(prompt_label)
        
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("例：専門用語を含む技術的な内容。固有名詞に注意してください。")
        self.prompt_edit.setMaximumHeight(80)
        self.prompt_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {DarkPalette.SURF};
                border: 1.5px solid {DarkPalette.B2};
                border-radius: 8px;
                padding: 10px 13px;
                color: {DarkPalette.TXT};
                font-size: 12px;
            }}
            QTextEdit:focus {{
                border-color: {DarkPalette.ACCENT};
            }}
        """)
        body_layout.addWidget(self.prompt_edit)
        
        body_layout.addStretch()
        
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        
        return page
    
    def create_confirm_page(self) -> QWidget:
        """Step 3: 配置確認ページ"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ヘッダー
        header = QFrame()
        header.setStyleSheet(f"background: transparent; border-bottom: 1px solid rgba(255, 255, 255, 0.05);")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 20, 24, 16)
        header_layout.setSpacing(5)
        
        step_ind = QLabel("STEP 03 / 03")
        step_ind.setStyleSheet(f"""
            QLabel {{
                font-family: 'Monospace';
                font-size: 9px;
                color: {DarkPalette.ACCENT};
                letter-spacing: 2px;
            }}
        """)
        header_layout.addWidget(step_ind)
        
        title = QLabel("配置の確認")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: 18px;
                font-weight: 500;
                color: {DarkPalette.TXT};
            }}
        """)
        header_layout.addWidget(title)
        
        subtitle = QLabel("内容を確認して「配置を実行」を押してください")
        subtitle.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                color: {DarkPalette.DIM};
                font-weight: 300;
            }}
        """)
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header)
        
        # ボディ
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 20, 24, 20)
        body_layout.setSpacing(16)
        
        # 成功メッセージ (初期は非表示)
        self.success_widget = QFrame()
        self.success_widget.setStyleSheet(f"""
            QFrame {{
                background: rgba(78, 201, 168, 0.06);
                border: 1.5px solid rgba(78, 201, 168, 0.2);
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        success_layout = QVBoxLayout(self.success_widget)
        success_layout.setAlignment(Qt.AlignCenter)
        
        check_label = QLabel("✅")
        check_label.setStyleSheet("font-size: 26px;")
        check_label.setAlignment(Qt.AlignCenter)
        success_layout.addWidget(check_label)
        
        success_title = QLabel("字幕生成完了")
        success_title.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: 500;
                color: {DarkPalette.GREEN};
            }}
        """)
        success_title.setAlignment(Qt.AlignCenter)
        success_layout.addWidget(success_title)
        
        self.success_detail = QLabel("SRT ファイルが生成されました")
        self.success_detail.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                color: {DarkPalette.DIM};
            }}
        """)
        self.success_detail.setAlignment(Qt.AlignCenter)
        success_layout.addWidget(self.success_detail)
        
        body_layout.addWidget(self.success_widget)
        self.success_widget.hide()
        
        body_layout.addStretch()
        
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        
        return page
    
    def create_footer(self) -> QWidget:
        """フッター作成"""
        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background: rgba(0, 0, 0, 0.15);
                border-top: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 0 0 20px 20px;
            }}
        """)
        
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 10, 20, 14)
        
        self.status_label = QLabel("Step 1 / 3 — 解析範囲を選択してください")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                font-family: 'Monospace';
                font-size: 10px;
                color: {DarkPalette.FAINT};
            }}
        """)
        layout.addWidget(self.status_label, 1)
        
        # ボタン
        self.btn_back = QPushButton("‹ 戻る")
        self.btn_back.setStyleSheet(self.get_button_style("ghost"))
        self.btn_back.clicked.connect(self.go_back)
        self.btn_back.hide()
        layout.addWidget(self.btn_back)
        
        self.btn_next = QPushButton("次へ ›")
        self.btn_next.setStyleSheet(self.get_button_style("primary"))
        self.btn_next.clicked.connect(self.go_next)
        layout.addWidget(self.btn_next)
        
        return footer
    
    def get_radio_style(self) -> str:
        """ラジオボタンのスタイル"""
        return f"""
            QRadioButton {{
                background: {DarkPalette.SURF};
                border: 1.5px solid {DarkPalette.B2};
                border-radius: 12px;
                padding: 14px 16px;
                font-size: 13px;
                font-weight: 500;
                color: {DarkPalette.DIM};
            }}
            QRadioButton:hover {{
                border-color: {DarkPalette.B1};
                background: {DarkPalette.SURF2};
            }}
            QRadioButton:checked {{
                background: rgba(91, 156, 246, 0.07);
                border-color: {DarkPalette.ACCENT};
                color: {DarkPalette.ACCENT};
            }}
            QRadioButton::indicator {{
                width: 0px;
                height: 0px;
            }}
        """
    
    def get_button_style(self, variant: str = "primary") -> str:
        """ボタンのスタイル"""
        if variant == "primary":
            return f"""
                QPushButton {{
                    padding: 10px 22px;
                    border-radius: 12px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {DarkPalette.ACCENT}, stop:1 {DarkPalette.ACD});
                    color: white;
                    border: 1.5px solid {DarkPalette.ACD};
                    font-size: 13px;
                    font-weight: 500;
                    min-width: 100px;
                }}
                QPushButton:hover {{
                    background: {DarkPalette.ACCENT};
                }}
                QPushButton:disabled {{
                    background: {DarkPalette.SURF};
                    color: {DarkPalette.FAINT};
                    border-color: {DarkPalette.B1};
                }}
            """
        elif variant == "ghost":
            return f"""
                QPushButton {{
                    padding: 10px 22px;
                    border-radius: 12px;
                    background: {DarkPalette.SURF};
                    color: {DarkPalette.DIM};
                    border: 1.5px solid {DarkPalette.B1};
                    font-size: 13px;
                    font-weight: 500;
                    min-width: 100px;
                }}
                QPushButton:hover {{
                    background: {DarkPalette.SURF2};
                    color: {DarkPalette.TXT};
                    border-color: {DarkPalette.B1};
                }}
            """
        else:  # action (緑)
            return f"""
                QPushButton {{
                    padding: 10px 22px;
                    border-radius: 12px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {DarkPalette.GREEN}, stop:1 #2fa882);
                    color: white;
                    border: 1.5px solid #2a9472;
                    font-size: 13px;
                    font-weight: 500;
                    min-width: 100px;
                }}
                QPushButton:hover {{
                    background: {DarkPalette.GREEN};
                }}
            """
    
    def apply_dark_theme(self):
        """ダークテーマ適用"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {DarkPalette.BG};
            }}
            QWidget {{
                color: {DarkPalette.TXT};
                font-family: 'Noto Sans JP', sans-serif;
                font-size: 13px;
            }}
            QScrollBar:vertical {{
                width: 4px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {DarkPalette.B1};
                border-radius: 2px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
    
    def jump_to_step(self, step_idx: int):
        """ステップジャンプ"""
        if step_idx == self.current_step:
            return
        
        # 現在の状態で許可されているか確認
        if not self.step_indicators[step_idx].clickable:
            return
        
        self.current_step = step_idx
        self.show_step(step_idx)
    
    def go_next(self):
        """次へボタン"""
        if self.current_step == 0:
            # Step 1 → Loading → Step 2 (ここでは簡略化してすぐStep 2へ)
            self.start_workflow()
        elif self.current_step == 1:
            # Step 2 完了後 → Step 3
            self.current_step = 2
            self.show_step(2)
    
    def go_back(self):
        """戻るボタン"""
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step(self.current_step)
    
    def show_step(self, step_idx: int):
        """ステップ表示切り替え"""
        # サイドバー更新
        for i, indicator in enumerate(self.step_indicators):
            indicator.set_active(i == step_idx)
            indicator.set_done(i < step_idx and self.analyzed)
            indicator.set_clickable(i < step_idx and self.analyzed)
        
        # コンテンツ切り替え (Step 1 = index 0, Step 3 = index 1)
        if step_idx == 0:
            self.content_stack.setCurrentIndex(0)
        elif step_idx == 2:
            self.content_stack.setCurrentIndex(1)
        
        # フッター更新
        if step_idx == 0:
            self.status_label.setText("Step 1 / 3 — 解析範囲を選択してください")
            self.btn_back.hide()
            self.btn_next.show()
            self.btn_next.setText("次へ ›")
            self.btn_next.setStyleSheet(self.get_button_style("primary"))
        elif step_idx == 2:
            self.status_label.setText("Step 3 / 3 — 配置内容を確認してください")
            self.btn_back.show()
            self.btn_next.show()
            self.btn_next.setText("閉じる")
            self.btn_next.setStyleSheet(self.get_button_style("ghost"))
    
    def start_workflow(self):
        """ワークフロー開始"""
        if not self.video_path:
            self.status_label.setText("エラー: 動画ファイルが指定されていません")
            return
        
        # Loading overlay 表示
        self.loading_overlay.show()
        self.loading_overlay.raise_()
        
        # Worker 起動
        from utils.path_manager import get_project_root
        project_root = get_project_root()
        
        self.worker = SubtitleWorker(
            video_path=self.video_path,
            resolve=self.resolve,
            settings=self.settings_mgr.all_settings,
            project_root=project_root,
            fps=self.fps,
            offset_frame=0
        )
        
        self.worker.progress.connect(self.on_progress)
        self.worker.status_changed.connect(self.on_status_changed)
        self.worker.log_message.connect(self.on_log_message)
        self.worker.finished.connect(self.on_workflow_finished)
        self.worker.error.connect(self.on_workflow_error)
        
        self.worker.start()
    
    def on_progress(self, progress: int):
        """進捗更新"""
        # フェーズ推定 (簡易版)
        if progress < 30:
            self.loading_overlay.set_phase(0, "active", progress, "音声抽出中...")
        elif progress < 70:
            self.loading_overlay.set_phase(0, "done", 100, "✓ 音声抽出完了")
            self.loading_overlay.set_phase(1, "active", (progress - 30) * 2, "文字起こし中...")
        else:
            self.loading_overlay.set_phase(0, "done", 100, "✓ 音声抽出完了")
            self.loading_overlay.set_phase(1, "done", 100, "✓ 文字起こし完了")
            self.loading_overlay.set_phase(2, "active", (progress - 70) * 3, "AI修正中...")
    
    def on_status_changed(self, status: str):
        """ステータス変更"""
        self.status_label.setText(status)
    
    def on_log_message(self, message: str):
        """ログメッセージ"""
        print(f"[GUI Log] {message}")
    
    def on_workflow_finished(self, srt_path: str):
        """ワークフロー完了"""
        self.loading_overlay.set_phase(2, "done", 100, "✓ AI修正完了")
        self.loading_overlay.hide()
        
        self.analyzed = True
        self.current_step = 2
        self.show_step(2)
        
        # 成功メッセージ表示
        self.success_widget.show()
        self.success_detail.setText(f"SRT: {os.path.basename(srt_path)}")
        
        self.status_label.setText(f"完了: {srt_path}")
    
    def on_workflow_error(self, error: str):
        """ワークフローエラー"""
        self.loading_overlay.hide()
        self.status_label.setText(f"エラー: {error}")
        print(f"[GUI Error] {error}")
    
    def cancel_workflow(self):
        """ワークフロー中止"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.loading_overlay.cancel_button.setEnabled(False)
            self.loading_overlay.cancel_button.setText("中止リクエスト送信済み...")
    
    def resizeEvent(self, event):
        """リサイズ時に overlay のサイズも更新"""
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.setGeometry(0, 0, self.width(), self.height())
    
    def closeEvent(self, event):
        """ウィンドウクローズ時の処理"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)
        event.accept()
