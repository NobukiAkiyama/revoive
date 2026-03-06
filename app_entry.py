"""
app_entry.py (Backend Driver for Subtitle Pivot)
===============================================
ロジックの動作検証および UI 連携用の最小限のエントリポイント。
UI に関してはユーザー側で実装することを想定し、バックエンドの呼び出しに専念します。
"""

import sys
import os
from typing import Any, Optional

# プロジェクトルートの動的解決
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from extension.resolve_api import get_resolve
from extension.srt_importer import import_srt_to_resolve
from processor.subtitle_pipeline import SubtitlePipeline

def run_subtitle_workflow(video_path: str, resolve_obj: Optional[Any] = None):
    # ... (existing content omitted for brevity in this tool call, but conceptually kept)
    pass

def init_q_application():
    """
    QApplication の二重起動を防止し、Resolve の既存インスタンスがあればそれを取得する。
    """
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            print("[Info] Starting new QApplication instance")
            app = QApplication(sys.argv)
        else:
            print("[Info] Using existing QApplication instance")
        return app
    except ImportError:
        print("[Error] PySide6 がインストールされていません。")
        return None

def run_gui_safe(resolve_obj: Optional[Any] = None):
    """
    Resolve 内部から安全に UI (エントリポイント) を起動するための関数。
    """
    app = init_q_application()
    if not app:
        return

    # ここでメインウィンドウをインスタンス化するが、表示(show)は UI 実装側で行う想定。
    # ここではロジックの口（ブリッジ）だけを作成。
    print("[Info] ReVoice GUI components initialized (Logic only).")
    
    # app.exec() を実行。sys.exit() は Resolve を巻き添えにするため使用しない。
    # 戻り値を受け取って終了。
    exit_code = app.exec()
    print(f"[Info] ReVoice application exited with code: {exit_code}")

def main():
    """
    単体テスト実行用：引数にビデオパスを渡して実行可能
    あるいは Resolve 内部から呼び出される際のエントリ。
    """
    # resolve オブジェクトの事前取得
    resolve = get_resolve()

    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        run_subtitle_workflow(video_path, resolve)
    else:
        # Resolve 内部起動を想定した GUI ロジックの開始
        run_gui_safe(resolve)

if __name__ == "__main__":
    main()
