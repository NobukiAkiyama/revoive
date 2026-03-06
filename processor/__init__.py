# processor/__init__.py
# Subtitle focused version

from .base_transcriber import TranscriptSegment, BaseTranscriber
from .subtitle_pipeline import SubtitlePipeline
from .ai_editor import AIEditor

__all__ = [
    "TranscriptSegment",
    "BaseTranscriber",
    "SubtitlePipeline",
    "AIEditor",
]
