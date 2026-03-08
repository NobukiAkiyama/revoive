import os
import sys
import subprocess
from unittest.mock import MagicMock, patch

# プロジェクトルートの動的解決
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from processor.subtitle_pipeline import SubtitlePipeline

def test_ffmpeg_robustness() -> None:
    print(">>> Testing FFmpeg robustness logic (ffmpeg-python version)...")
    settings = {
        "ffmpeg_path": "ffmpeg",
        "ai": {"api_key": "dummy_key"}
    }
    pipeline = SubtitlePipeline(settings)
    
    # テスト用のダミー入力ファイル
    dummy_video = os.path.join(PROJECT_ROOT, "test_dummy.mp4")
    dummy_output = os.path.join(PROJECT_ROOT, "test_output.wav")
    
    # 1. ffmpeg.run_async のモック
    with patch("ffmpeg.run_async") as mock_run_async, \
         patch("os.path.exists", side_effect=lambda p: True if p == dummy_output else os.path.exists(p)), \
         patch("os.path.getsize", return_value=2048), \
         patch("os.makedirs"):
        
        # 疑似プロセスオブジェクト
        mock_process = MagicMock()
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_run_async.return_value = mock_process
        
        success = pipeline.extract_audio_ffmpeg(dummy_video, dummy_output)
        
        # 検証: ffmpeg-python の output 呼び出しが正しいか (内部的に構築されたストリームを検証するのは難しいため、実行されたことのみ確認)
        assert mock_run_async.called
        assert success == True
        print("✓ extract_audio_ffmpeg (ffmpeg-python) success check passed.")

    # 2. エラー時の挙動チェック
    with patch("ffmpeg.run_async") as mock_run_async:
        mock_process = MagicMock()
        mock_process.poll.return_value = 1
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"Error message")
        mock_run_async.return_value = mock_process
        
        with patch("os.makedirs"):
            success = pipeline.extract_audio_ffmpeg(dummy_video, dummy_output)
            assert success == False
            print("✓ Error handling check passed.")

if __name__ == "__main__":
    test_ffmpeg_robustness()
