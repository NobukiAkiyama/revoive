"""
processor/adapters/whisper_transcriber.py
faster-whisper を使用した音声文字起こし実装
"""

import os
from typing import Dict, Any, List

from processor.base_transcriber import BaseTranscriber, TranscriptSegment


class WhisperTranscriber(BaseTranscriber):
    """
    faster-whisper を使用した音声文字起こし実装
    仕様書: SPECIFICATION_v2_00_merged.md セクション10 'WhisperTranscriber'
    """

    def __init__(self, settings: Dict[str, Any]) -> None:
        # 遅延インポート: faster-whisper が未インストールでも他エンジンが動作できるようにする
        try:
            from faster_whisper import WhisperModel as FasterWhisperModel
        except ImportError:
            raise RuntimeError(
                "FATAL ERROR: faster-whisper がインストールされていません\n"
                "インストール: pip install faster-whisper"
            )

        self.settings = settings
        whisper_cfg = settings.get("whisper", {})
        model_name = whisper_cfg.get("model", "base")
        device = whisper_cfg.get("device", "auto")

        try:
            self.model = FasterWhisperModel(model_name, device=device)
        except Exception as e:
            raise RuntimeError(f"Whisper モデル読み込み失敗: {e}")

        self.language = whisper_cfg.get("language", "ja")
        self.vad_filter = whisper_cfg.get("vad_filter", True)
        self.min_duration_ms = whisper_cfg.get("min_speech_duration_ms", 250)

    def transcribe(self, audio_path: str) -> List[TranscriptSegment]:
        """faster-whisper で音声を文字起こし"""
        if not os.path.exists(audio_path):
            raise RuntimeError(f"音声ファイルが見つかりません: {audio_path}")

        try:
            segments, _ = self.model.transcribe(
                audio_path,
                language=self.language,
                word_timestamps=True,
                vad_filter=self.vad_filter,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    min_speech_duration_ms=self.min_duration_ms,
                ),
            )
        except Exception as e:
            raise RuntimeError(f"Whisper による文字起こし失敗: {e}")

        result = []
        for i, seg in enumerate(segments):
            duration_ms = (seg.end - seg.start) * 1000
            result.append(
                TranscriptSegment(
                    id=f"seg_{i + 1:03d}",
                    text=seg.text.strip(),
                    start=seg.start,
                    end=seg.end,
                    needs_review=(duration_ms < self.min_duration_ms * 2),
                )
            )

        return result
