"""
ui/worker.py
============
UI スレッドをブロックせずに重い処理を実行するための Worker クラス。
シグナル/スロットを用いて進捗やログを UI へ橋渡しする。
"""

import threading
from PySide6.QtCore import QThread, Signal
from typing import Any, Dict, Optional
import os

class SubtitleWorker(QThread):
    """
    字幕生成パイプラインを別スレッドで実行する Worker。
    """
    # UI 側で受け取るためのシグナル定義
    progress = Signal(int)    # 進捗率 (0-100)
    status_changed = Signal(str) # ステータス文字列
    log_message = Signal(str) # ログメッセージ
    finished = Signal(str)    # 成功時の SRT パス
    error = Signal(str)       # エラーメッセージ

    def __init__(self, 
                 video_path: str, 
                 resolve: Any, 
                 settings: Dict[str, Any],
                 project_root: str) -> None:
        super().__init__()
        self.video_path = video_path
        self.resolve = resolve
        self.settings = settings
        self.project_root = project_root
        self._stop_event = threading.Event()

    def run(self) -> None:
        """
        別スレッドで実行されるメイン処理。
        """
        try:
            from processor.workflow_engine import run_standard_workflow
            
            self.log_message.emit(">>> [Worker] ワークフロー開始...")

            # 1. Timeline から FPS 取得
            project_manager = self.resolve.GetProjectManager()
            project = project_manager.GetCurrentProject()
            timeline = project.GetCurrentTimeline()
            if not timeline:
                self.error.emit("タイムラインが見つかりません。")
                return
            
            fps = float(timeline.GetSetting("timelineFrameRate"))
            self.log_message.emit(f"[Info] Timeline FPS: {fps}")

            # 2. ジェネレーターの取得と反復
            engine_gen = run_standard_workflow(
                video_path=self.video_path,
                settings=self.settings,
                fps=fps,
                project_root=self.project_root,
                log_callback=lambda msg: self.log_message.emit(msg),
                stop_event=self._stop_event
            )
            
            srt_path = None
            try:
                for status, prog in engine_gen:
                    self.status_changed.emit(status)
                    self.progress.emit(prog)
            except StopIteration as e:
                srt_path = e.value
            
            # 中断チェック
            if self._stop_event.is_set():
                self.log_message.emit("[Worker] 処理が中断されました。")
                return

            if srt_path and os.path.exists(srt_path):
                self.progress.emit(100)
                self.finished.emit(srt_path)
            else:
                self.error.emit("ワークフローが終了しましたが、SRTが見つかりません。")

        except Exception as e:
            import traceback
            err_details = traceback.format_exc()
            self.log_message.emit(f"[Fatal Error] {err_details}")
            self.error.emit(str(e))

    def cancel(self) -> None:
        """
        処理を中断する。
        """
        self._stop_event.set()
        self.log_message.emit("[Worker] 中断リクエストをエンジンへ送信中...")

