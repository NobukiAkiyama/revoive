"""
processor/workflow_engine.py
===========================
GUI非依存の字幕生成ワークフローエンジン。
PySide6 などの GUI ライブラリへの依存を排除し、CLI/GUI 両方から利用可能。
"""

import os
import sys
import threading
from typing import Any, Dict, Optional, Callable, Generator, Tuple
from processor.subtitle_pipeline import SubtitlePipeline

def run_standard_workflow(
    video_path: str,
    settings: Dict[str, Any],
    fps: float,
    project_root: str,
    log_callback: Optional[Callable[[str], None]] = None,
    stop_event: Optional[threading.Event] = None
) -> Generator[Tuple[str, int], None, Optional[str]]:
    """
    FFmpegによる音声抽出からSRT生成までの一連の処理をジェネレーターとして実行する。
    
    Yields:
        (status_message, progress_percent)
        
    Returns:
        生成された SRT ファイルの絶対パス。失敗・中断した場合は None。
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    def check_stop():
        return stop_event and stop_event.is_set()

    try:
        log(">>> [Engine] ワークフロー開始...")
        yield ("Initializing...", 5)
        
        if check_stop():
            log("[Engine] 中断されました。")
            return None

        # 1. パイプライン初期化
        pipeline = SubtitlePipeline(settings)
        pipeline.set_stop_event(stop_event) # パイプラインに停止イベントを渡す
        
        # 2. 出力ディレクトリ準備
        data_dir = os.path.normpath(os.path.join(project_root, "data", "output"))
        os.makedirs(data_dir, exist_ok=True)
        
        temp_audio = os.path.normpath(os.path.join(data_dir, "temp_transcript_audio.wav"))
        output_base = os.path.normpath(os.path.join(data_dir, "generated_subtitle"))

        if check_stop(): return None

        # 3. 音声抽出 (FFmpeg)
        log(">>> [Phase 1] 音声の正規化 (FFmpeg) 開始...")
        yield ("Extracting Audio...", 10)
        
        if not pipeline.extract_audio_ffmpeg(video_path, temp_audio):
            if check_stop():
                log("[Engine] FFmpeg 実行中に中断されました。")
            else:
                log("[Error] 音声の抽出または正規化に失敗しました。")
            return None
        
        if check_stop(): return None
        yield ("Audio Extracted", 30)

        # 4. 文字起こし & SRT生成 (Whisper + AI)
        log(">>> [Phase 2] 文字起こしパイプライン開始...")
        yield ("Transcribing...", 40)
        
        # run_full_pipeline の内部でも stop_event をチェックするように変更が必要
        srt_path = pipeline.run_full_pipeline(
            audio_path=temp_audio,
            output_base_name=output_base,
            fps=fps,
            log_callback=log,
            progress_callback=lambda p: next(iter([None])) # ダミー、後で調整
        )

        #進捗の詳細は pipeline 内部で yield させたいが、一旦簡易実装
        if check_stop():
            log("[Engine] 文字起こし中に中断されました。")
            return None

        if srt_path and os.path.exists(srt_path):
            log(f">>> [Success] 処理完了: {srt_path}")
            yield ("Completed", 100)
            return srt_path
        else:
            log("[Error] 文字起こし処理が異常終了しました。")
            return None

    except Exception as e:
        import traceback
        log(f"[Fatal Error] {str(e)}")
        log(traceback.format_exc())
        return None

