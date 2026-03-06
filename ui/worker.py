"""
ui/worker.py
============
UI スレッドをブロックせずに重い処理を実行するための Worker クラス。
シグナル/スロットを用いて進捗やログを UI へ橋渡しする。
"""

from PySide6.QtCore import QThread, Signal
from typing import Any, Dict, Optional
import os

class SubtitleWorker(QThread):
    """
    字幕生成パイプラインを別スレッドで実行する Worker。
    """
    # UI 側で受け取るためのシグナル定義
    progress = Signal(int)    # 進捗率 (0-100)
    log_message = Signal(str) # ログメッセージ
    finished = Signal(str)    # 成功時の SRT パス
    error = Signal(str)       # エラーメッセージ

    def __init__(self, 
                 video_path: str, 
                 resolve: Any, 
                 settings: Dict[str, Any],
                 project_root: str):
        super().__init__()
        self.video_path = video_path
        self.resolve = resolve
        self.settings = settings
        self.project_root = project_root
        self._is_cancelled = False

    def run(self):
        """
        別スレッドで実行されるメイン処理。
        """
        try:
            from processor.subtitle_pipeline import SubtitlePipeline
            
            self.log_message.emit(">>> [Worker] パイプライン初期化中...")
            pipeline = SubtitlePipeline(self.settings)

            # 1. Timeline から FPS 取得
            project_manager = self.resolve.GetProjectManager()
            project = project_manager.GetCurrentProject()
            timeline = project.GetCurrentTimeline()
            if not timeline:
                self.error.emit("タイムラインが見つかりません。")
                return
            
            fps = float(timeline.GetSetting("timelineFrameRate"))
            self.log_message.emit(f"[Info] Timeline FPS: {fps}")

            # 2. 出力パス準備
            data_dir = os.path.join(self.project_root, "data", "output")
            os.makedirs(data_dir, exist_ok=True)
            temp_audio = os.path.join(data_dir, "temp_transcript_audio.wav")
            output_base = os.path.join(data_dir, "generated_subtitle")

            # 3. 音声抽出 (ffmpeg)
            self.log_message.emit(">>> [Step 1] 音声抽出開始...")
            if not pipeline.extract_audio_ffmpeg(self.video_path, temp_audio):
                self.error.emit("音声抽出に失敗しました。")
                return
            self.progress.emit(30)

            # 4. パイプライン実行 (Whisper & AI Edit)
            self.log_message.emit(">>> [Step 2] 字幕生成/AI処理開始...")
            
            # log_callback を Worker のシグナルに紐付け
            def worker_log(msg):
                self.log_message.emit(msg)

            srt_path = pipeline.run_full_pipeline(temp_audio, output_base, fps, log_callback=worker_log)
            
            if srt_path and os.path.exists(srt_path):
                self.progress.emit(100)
                self.finished.emit(srt_path)
            else:
                self.error.emit("字幕生成パイプラインが異常終了しました。")

        except Exception as e:
            import traceback
            err_details = traceback.format_exc()
            self.log_message.emit(f"[Fatal Error] {err_details}")
            self.error.emit(str(e))

    def cancel(self):
        """
        処理を中断するフラグを立てる (pipeline 側での対応が必要)。
        """
        self._is_cancelled = True
        self.log_message.emit("[Worker] 中断リクエストを受け取りました。")
