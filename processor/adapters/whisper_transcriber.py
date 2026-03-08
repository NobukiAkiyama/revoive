"""
processor/adapters/whisper_transcriber.py
faster-whisper を使用した音声文字起こし実装 (鉄壁フォールバック版)
"""

import os
import threading
from typing import Dict, Any, List, Optional
import sys

from processor.base_transcriber import TranscriptSegment, BaseTranscriber

class WhisperTranscriber(BaseTranscriber):
    def __init__(self, settings: Dict[str, Any]) -> None:
        try:
            from faster_whisper import WhisperModel as FasterWhisperModel
            self.FasterWhisperModel = FasterWhisperModel
        except ImportError:
            raise RuntimeError("FATAL: faster-whisper がインストールされていません。")

        self.settings = settings
        whisper_cfg = settings.get("whisper", {})
        self.model_name = whisper_cfg.get("model", "base")
        self.device = whisper_cfg.get("device", "auto")
        self.model: Any = None

        self.language = whisper_cfg.get("language", "ja")
        self.vad_filter = whisper_cfg.get("vad_filter", True)
        self.min_duration_ms = whisper_cfg.get("min_speech_duration_ms", 250)

    def _initialize_model(self, device: str, progress_callback: Optional[Any] = None) -> None:
        """モデルの初期化。"""
        try:
            msg = f"[Whisper] Loading model '{self.model_name}' on '{device}'..."
            print(msg)
            if progress_callback:
                progress_callback(msg, 0)
                
            self.model = self.FasterWhisperModel(self.model_name, device=device)
            self.device = device
            
            if progress_callback:
                progress_callback(f"[Whisper] Model loaded on '{device}'.", 0)
        except Exception as e:
            if device != "cpu":
                msg = f"[Warning] GPU initialization failed: {e}. Switching to CPU..."
                print(msg)
                if progress_callback:
                    progress_callback(msg, 0)
                self._initialize_model("cpu", progress_callback)
            else:
                raise RuntimeError(f"Whisper failed even on CPU: {e}")

    def transcribe(self, audio_path: str, stop_event: Optional[threading.Event] = None, progress_callback: Optional[Any] = None) -> Optional[List[TranscriptSegment]]:
        """文字起こし実行 (DLLエラー時も自動復旧)"""
        if not os.path.exists(audio_path):
            raise RuntimeError(f"File not found: {audio_path}")

        # モデルの遅延ロード
        if self.model is None:
            self._initialize_model(self.device, progress_callback)

        try:
            return self._run_transcription(audio_path, stop_event)
        except Exception as e:
            error_msg = str(e)
            # DLL 不足エラー (cublas, cudnn 等) を検知
            if "cublas" in error_msg.lower() or "cudnn" in error_msg.lower() or "library not found" in error_msg.lower():
                print("\n" + "!"*60)
                print("[Critical] CUDA Library (DLL) is missing for GPU execution.")
                print("[Action] Falling back to CPU mode mid-process...")
                print("[Fix Suggestion] Run: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12")
                print("!"*60 + "\n")
                
                # その場で CPU モードに作り直して再実行
                self._initialize_model("cpu")
                return self._run_transcription(audio_path, stop_event)
            else:
                raise e

    def _run_transcription(self, audio_path: str, stop_event: Optional[threading.Event] = None) -> Optional[List[TranscriptSegment]]:
        """実際の文字起こしロジック"""
        assert self.model is not None
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
        
        result = []
        for i, seg in enumerate(segments):
            event = stop_event
            if event and event.is_set():
                print("[Whisper] Transcription interrupted by user.")
                return None
            
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
