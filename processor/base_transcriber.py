"""
processor/base_transcriber.py
音声文字起こし抽象インターフェース + 共通データ構造
"""

from dataclasses import dataclass, field
from typing import List, Optional
from abc import ABC, abstractmethod


@dataclass
class TranscriptSegment:
    """
    パイプライン全ステージで使用する統一データ構造
    仕様書: SPECIFICATION_v2_00_merged.md セクション9 'TranscriptSegment'
    """
    id: str
    text: str
    start: float                      # 秒単位（元タイムライン基準）
    end: float                        # 秒単位（元タイムライン基準）
    speaker: Optional[str] = None
    base_speed: float = 1.0
    rate_modifier: float = 1.0
    needs_review: bool = False        # 短い・判定不能セグメント（黄色表示）
    exclude: bool = False             # 生成・配置対象から除外
    user_note: str = ""               # ユーザーメモ
    generated_wav_path: str = ""      # TTS生成後に設定


import threading

class BaseTranscriber(ABC):
    """音声文字起こしの抽象インターフェース"""

    @abstractmethod
    def transcribe(self, audio_path: str, stop_event: Optional[threading.Event] = None) -> Optional[List[TranscriptSegment]]:
        """音声ファイルを文字起こしし、タイムスタンプ付きセグメントを返す"""
        pass
