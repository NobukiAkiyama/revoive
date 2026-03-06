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
    """
    バックエンドの全工程を実行するドライバ。
    
    1. Resolve 接続 & FPS 取得
    2. ffmpeg による音声抽出
    3. Whisper による文字起こし -> CSV -> SRT
    4. Resolve へのインポート
    """
    resolve = get_resolve(resolve_obj)
    if not resolve:
        print("[Error] DaVinci Resolve 接続失敗")
        return

    # Timeline から FPS を取得 (p=963 準拠)
    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    if not timeline:
        print("[Error] タイムラインが見つかりません。")
        return
        
    fps = float(timeline.GetSetting("timelineFrameRate"))
    print(f"[Info] Timeline FPS: {fps}")

    # 内部使用パスはプロジェクトルートからの相対で構築
    data_dir = os.path.join(PROJECT_ROOT, "data", "output")
    os.makedirs(data_dir, exist_ok=True)
    temp_audio = os.path.join(data_dir, "temp_transcript_audio.wav")
    output_base = os.path.join(data_dir, "generated_subtitle")

    # 設定 (外部ファイルからの読み込みを想定するが、現在はデフォルト)
    settings = {
        "whisper": {"model": "base"}
    }
    pipeline = SubtitlePipeline(settings)

    # 1. 音声抽出 (ffmpeg)
    print(">>> Phase 1: ffmpeg 音声抽出")
    if not pipeline.extract_audio_ffmpeg(video_path, temp_audio):
        print("[Error] 音声抽出失敗")
        return

    # 2. 字幕生成 (Whisper -> CSV -> SRT)
    print(">>> Phase 2: AI 字幕生成パイプライン")
    srt_path = pipeline.run_full_pipeline(temp_audio, output_base, fps)

    # 3. インポート
    print(">>> Phase 3: Resolve インポート")
    import_srt_to_resolve(resolve, srt_path)

def main():
    """
    単体テスト実行用：引数にビデオパスを渡して実行可能
    例: python app_entry.py C:/path/to/video.mp4
    """
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        run_subtitle_workflow(video_path)
    else:
        print("Usage: python app_entry.py <video_path>")
        print("Note: Resolve UI 連携時はこのモジュールの関数を外部から呼び出してください。")

if __name__ == "__main__":
    main()
